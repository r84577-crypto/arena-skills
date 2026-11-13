/**
 * بوابة الأصل (CSRF) ومحدِّد الحدّ — منطق صرف بلا اعتمادية.
 *
 * منفصل عن `security.ts` لأنه يجب أن يُختبر بـ node مباشرة. `security.ts`
 * يستورد `next/server` (لأنه يبني ردوداً)، وأي ملف يستورده يصبح غير قابل
 * للاختبار بلا خادم. الهجوم الذي نتّقي منه لا ينتظر خادماً.
 *
 * شرح كل قرار أمني موجود عند الدالة نفسها، لا في مستند منفصل يُنسى.
 */

/* ------------------------------------------------------------------------- */
/* الأصل — بوابة CSRF                                                        */
/* ------------------------------------------------------------------------- */

/**
 * أصول الموقع المسموحة، صريحة من البيئة (`ALLOWED_ORIGINS` مفصولة بفواصل).
 *
 * القائمة الفارغة ليست ثغرة: `checkOrigin` يقبل أيضاً مطابقة المضيف مع
 * مضيف الطلب نفسه، فتعمل على أي نطاق نشر بلا إعداد. تُضاف localhost في
 * التطوير لأن منفذ المعاينة قد يختلف عن مضيف الطلب عند الوكس.
 */
export function allowedOriginsFromEnv(env: { ALLOWED_ORIGINS?: string; NODE_ENV?: string }): string[] {
  const configured = (env.ALLOWED_ORIGINS ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  if (configured.length > 0) return configured;
  return env.NODE_ENV !== "production" ? ["http://localhost:3000"] : [];
}

/**
 * بوابة CSRF لكل طلب يغيّر بيانات (POST/PUT/PATCH/DELETE).
 *
 * الكوكيز هنا SameSite=Lax، وهي وحدها لا تكفي: Lax يمنع القراءة لكن
 * طلبات النموذج البسيطة قد تمرّ. لذلك نتحقق من `Origin` صراحةً — وهو
 * الفحص المعتمد في OWASP لطلبات JSON.
 *
 * الطلبات الخلفية بلا `Origin` (سكربتات، cron) تُقبل فقط إن حملت
 * `Authorization` — أي أنها ليست طلباً سياقياً من متصفح.
 */
export function checkOrigin(
  req: Request,
  allowedOrigins: readonly string[],
): { ok: true } | { ok: false; reason: string } {
  const origin = req.headers.get("origin");
  if (!origin) {
    if (!req.headers.get("authorization")) {
      return { ok: false, reason: "الطلب بلا Origin ولا رمز جلسة" };
    }
    return { ok: true };
  }

  // `Origin: null` يأتي من iframe معزول أو ملف محلي — ليس موقعنا.
  if (origin === "null") return { ok: false, reason: "أصل الطلب غير مسموح" };

  let originUrl: URL;
  try {
    originUrl = new URL(origin);
  } catch {
    return { ok: false, reason: "أصل الطلب غير صالح" };
  }

  // (أ) قائمة صريحة — مقارنة تامة، لا `startsWith`:
  //     `https://site.com.evil.tld` يبدأ بنطاقنا فيمرّ من فحص ساذج.
  const wanted = origin.replace(/\/$/, "").toLowerCase();
  if (allowedOrigins.some((o) => o.replace(/\/$/, "").toLowerCase() === wanted)) {
    return { ok: true };
  }

  // (ب) مطابقة المضيف مع مضيف الطلب نفسه.
  //
  //     لماذا المضيف لا المخطط؟ المخطط في `Origin` يأتي من المتصفح، بينما
  //     «مخطط الطلب» مستنتج من `x-forwarded-*` وقد يختلف في معاينة أو وكيل،
  //     فيُرفض طلب شرعي بلا سبب. المخطط أصلاً مفروض بـ HSTS والتحويل 308،
  //     فالمقارنة على المضيف (مع المنفذ) هي الفحص الصحيح: المضيف الشبيه مختلف.
  const requestHost = (req.headers.get("x-forwarded-host") ?? req.headers.get("host") ?? "")
    .split(",")[0]
    .trim()
    .toLowerCase();
  if (requestHost && originUrl.host.toLowerCase() === requestHost) {
    return { ok: true };
  }

  return { ok: false, reason: "أصل الطلب غير مسموح" };
}

/* ------------------------------------------------------------------------- */
/* حدّ الطلبات                                                                */
/* ------------------------------------------------------------------------- */

export type RateDecision = {
  ok: boolean;
  remaining: number;
  retryAfterSec: number;
};

export type RateLimitRule = {
  /** اسم القاعدة، يظهر في الترويسات والسجلات. */
  name: string;
  /** أقصى عدد طلبات داخل النافذة. */
  limit: number;
  /** طول النافذة بالثواني. */
  windowSec: number;
};

/**
 * محدِّد نافذة زمنية متحركة (sliding window) في الذاكرة.
 *
 * لماذا في الذاكرة؟ لأن المشروع لا يملك Redis، وإضافة اعتمادية لمجرد عدّاد
 * غير مبرَّرة. حدود هذا الاختيار مذكورة صراحةً ولا تُخفى:
 *
 *   - العدّاد لكل نسخة (instance) على حدة. على Netlify عدة نسخ = الحدّ
 *     الفعلي = الحدّ × عدد النسخ. الحدّ الأدنى مضمون لكل نسخة.
 *   - يُصفَّر عند إعادة النشر أو إعادة التشغيل.
 *
 * أي حدّ أدنى حقيقي أفضل من لا شيء، والطبقة القوية تبقى RLS والجلسة
 * والحصة اليومية في الدفتر (50 رسالة/24 ساعة) — وهي ليست في الذاكرة.
 */
export class MemoryLimiter {
  private hits = new Map<string, number[]>();
  private readonly maxKeys = 10_000;

  check(key: string, rule: RateLimitRule, now = Date.now()): RateDecision {
    const windowMs = rule.windowSec * 1000;
    const cutoff = now - windowMs;
    const bucketKey = `${rule.name}:${key}`;
    const recent = (this.hits.get(bucketKey) ?? []).filter((t) => t > cutoff);

    if (recent.length >= rule.limit) {
      const oldest = recent[0] ?? now;
      const retryAfterSec = Math.max(1, Math.ceil((oldest + windowMs - now) / 1000));
      this.hits.set(bucketKey, recent);
      return { ok: false, remaining: 0, retryAfterSec };
    }

    recent.push(now);
    this.hits.set(bucketKey, recent);
    this.sweep(now, windowMs);
    return { ok: true, remaining: rule.limit - recent.length, retryAfterSec: 0 };
  }

  /** تنظيف دوري: لا خريطة تنمو بلا سقف مهما هاجم أحدهم عناوين عشوائية. */
  private sweep(now: number, windowMs: number): void {
    if (this.hits.size <= this.maxKeys) return;
    const cutoff = now - windowMs;
    for (const [k, v] of this.hits) {
      if (!v.some((t) => t > cutoff)) this.hits.delete(k);
    }
    for (const k of this.hits.keys()) {
      if (this.hits.size <= this.maxKeys) break;
      this.hits.delete(k);
    }
  }

  /** للاختبارات فقط. */
  reset(): void {
    this.hits.clear();
  }
}

/**
 * الصالح من `x-forwarded-for` وحده: الترويسة يزوّرها العميل، لكن منصات
 * النشر تضبط ترويستها الخاصة. نفضّل ترويسة المنصة، ونأخذ أول عنوان في
 * XFF كآخر خيار. الحدّ طبقة تخفيف لا مصادقة، فلا يُبنى عليه قرار هوية.
 */
export function clientIpFrom(headers: Headers): string {
  const platform =
    headers.get("x-nf-client-connection-ip") ??
    headers.get("cf-connecting-ip") ??
    headers.get("x-real-ip");
  if (platform) return platform.trim().slice(0, 64);
  const xff = headers.get("x-forwarded-for");
  if (xff) {
    const first = xff.split(",")[0]?.trim();
    if (first) return first.slice(0, 64);
  }
  return "unknown";
}
