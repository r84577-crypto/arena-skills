/**
 * التحقق من المدخلات — دوال صرفة بلا أي اعتمادية.
 *
 * لماذا منفصلة عن `security.ts`؟ لأن `security.ts` يستورد `next/server`
 * (لأنه يبني ردوداً)، وأي استيراد لـ Next يمنع اختبار الدوال بـ node
 * مباشرة. التحقق هو الجزء الذي يجب أن يُختبر أكثر من غيره، فلا يُلوَّث
 * باعتمادية إطار العمل.
 *
 * كل دالة هنا تُعيد `null` عند الرفض ولا ترمي — فالمنادي يقرّر رمز
 * الحالة، ولا يوجد مسار يمرّ من هنا بمدخل غير متحقق.
 */

/**
 * سقف جسم الطلب. `req.json()` التابع لـ Next لا يعرف حجم الجسم، فجسم
 * 50 ميجابايت يُقرأ كاملاً في الذاكرة قبل أن يصل إلى أي تحقق. لذلك
 * نقرأ النص بسقف صريح ثم نحوّله بأنفسنا.
 */
export const MAX_API_BODY_BYTES = 16 * 1024;

/** حدود المحتوى — تطابق قيود `comms_log` في القاعدة حرفياً. */
export const MAX_SUBJECT_CHARS = 200;
export const MAX_BODY_CHARS = 4000;
export const MAX_EMAIL_CHARS = 320;

export type BodyResult<T> =
  | { ok: true; value: T }
  | { ok: false; reason: string; status: number };

/** يقرأ جسم الطلب كنص بسقف صريح ثم يحوّله JSON كائناً. */
export async function readJsonBody(req: Request): Promise<BodyResult<Record<string, unknown>>> {
  const declared = Number(req.headers.get("content-length") ?? "0");
  if (Number.isFinite(declared) && declared > MAX_API_BODY_BYTES) {
    return { ok: false, reason: "حجم الطلب أكبر من الحد المسموح", status: 413 };
  }

  let raw: string;
  try {
    raw = await req.text();
  } catch {
    return { ok: false, reason: "تعذّرت قراءة الطلب", status: 400 };
  }

  // القياس على البايتات الفعلية (UTF-8) لا على عدد الحروف:
  // حرف عربي واحد = بايتان، فحدّ "حروف" يتضاعف بصمت.
  if (new TextEncoder().encode(raw).length > MAX_API_BODY_BYTES) {
    return { ok: false, reason: "حجم الطلب أكبر من الحد المسموح", status: 413 };
  }
  if (!raw.trim()) {
    return { ok: false, reason: "جسم الطلب فارغ", status: 400 };
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return { ok: false, reason: "جسم الطلب ليس JSON صالحاً", status: 400 };
  }
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    return { ok: false, reason: "جسم الطلب يجب أن يكون كائناً", status: 400 };
  }
  return { ok: true, value: parsed as Record<string, unknown> };
}

/** حقل نصّي بحدّ أعلى/أدنى، مع رفض أي نوع آخر (رقم/كائن/مصفوفة/null). */
export function str(v: unknown, { max, min = 0 }: { max: number; min?: number }): string | null {
  if (typeof v !== "string") return null;
  const trimmed = v.trim();
  if (trimmed.length < min || trimmed.length > max) return null;
  return trimmed;
}

/** عدد صحيح داخل حدود — يرفض NaN والكسور والسالب والنصوص الرقمية. */
export function int(v: unknown, { min, max }: { min: number; max: number }): number | null {
  if (typeof v !== "number" || !Number.isInteger(v)) return null;
  if (v < min || v > max) return null;
  return v;
}

/** بريد إلكتروني — فحص شكلي صارم بما يكفي، لا RFC كاملاً. */
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export function email(v: unknown, maxLen = MAX_EMAIL_CHARS): string | null {
  const s = str(v, { max: maxLen, min: 3 });
  if (s === null || !EMAIL_RE.test(s)) return null;
  return s.toLowerCase();
}

/** نطاق معروف — القائمة المغلقة تمنع أي قيمة تُخترع من العميل. */
export function oneOf<T extends string>(v: unknown, allowed: readonly T[]): T | null {
  return typeof v === "string" && (allowed as readonly string[]).includes(v) ? (v as T) : null;
}

/**
 * تنقية نص يذهب إلى بريد/واتساب: إزالة أحرف التحكم (عدا سطر جديد) و
 * محارف الاتجاه الخفية التي تُستخدم لقلب ترتيب النص المعروض.
 * لا تُعالَج HTML هنا — التسليم نصّي، والتصيير في الواجهة يهرّب تلقائياً.
 */
export function sanitizeText(v: string): string {
  return v
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "")
    .replace(/[\u200E\u200F\u202A-\u202E\u2066-\u2069]/g, "")
    .trim();
}
