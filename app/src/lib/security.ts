/**
 * الطبقة الأمنية المشتركة — تُستورَد من `proxy.ts` ومن كل مسار API.
 *
 * التقسيم مقصود:
 *
 *   request-guards.ts   الأصل (CSRF) + حدّ الطلبات — منطق صرف يُختبر بـ node
 *   validation.ts       قراءة الجسم والتحقق من الحقول — منطق صرف يُختبر بـ node
 *   security.ts         (هذا الملف) الترويسات والردود والتسجيل، ويستورد
 *                       `next/server` لأنه يبني `NextResponse`
 *
 * السبب: أي ملف يستورد `next/server` لا يمكن اختباره بلا خادم. المنطق
 * الذي يجب أن يُختبر أكثر من غيره (التحقق، الأصل، الحدّ) أُخرج منه، وبقي
 * هنا ما هو غلاف رقيق حول الإطار.
 */

import { NextResponse } from "next/server";
import {
  MemoryLimiter,
  allowedOriginsFromEnv,
  clientIpFrom,
  type RateDecision,
  type RateLimitRule,
} from "@/lib/request-guards";

// يُعاد التصدير هنا لأن المسارات تستورد من ملف واحد.
export {
  MAX_API_BODY_BYTES,
  MAX_BODY_CHARS,
  MAX_EMAIL_CHARS,
  MAX_SUBJECT_CHARS,
  email,
  int,
  oneOf,
  readJsonBody,
  sanitizeText,
  str,
  type BodyResult,
} from "@/lib/validation";

export {
  MemoryLimiter,
  checkOrigin,
  type RateDecision,
  type RateLimitRule,
} from "@/lib/request-guards";

/* ------------------------------------------------------------------------- */
/* الردود                                                                     */
/* ------------------------------------------------------------------------- */

/**
 * خطأ عام للمستخدم. لا رسالة مزوّد، ولا مسار ملف، ولا اسم جدول — التفاصيل
 * تُسجَّل خادماً فقط (`logSecurityEvent`). و`no-store` حتى لا يُخزَّن رفض
 * مؤقت فيُخفي نجاحاً لاحقاً.
 */
export function jsonError(
  message: string,
  status: number,
  extraHeaders?: Record<string, string>,
): NextResponse {
  return NextResponse.json(
    { status: "blocked", reason: message },
    { status, headers: { "cache-control": "no-store", ...extraHeaders } },
  );
}

/* ------------------------------------------------------------------------- */
/* الأصل والحدّ                                                               */
/* ------------------------------------------------------------------------- */

/** IP العميل كما تراه المنصة (التفصيل في `request-guards.ts`). */
export function clientIp(req: Request): string {
  return clientIpFrom(req.headers);
}

/**
 * أصول الموقع المسموحة من `ALLOWED_ORIGINS`.
 *
 * القائمة الفارغة ليست ثغرة: `checkOrigin` يقبل أيضاً مطابقة المضيف مع
 * مضيف الطلب نفسه، فتعمل على أي نطاق نشر بلا إعداد.
 */
export function allowedOrigins(_req: Request): string[] {
  return allowedOriginsFromEnv({
    ALLOWED_ORIGINS: process.env.ALLOWED_ORIGINS,
    NODE_ENV: process.env.NODE_ENV,
  });
}

/**
 * الحدود المطبَّقة على مسارات التسليم. المسار المكلف (مزوّد بريد/واتساب
 * يكلّف مالاً وسمعة نطاق) يحدّه ثلاثة أقفال:
 *
 *   1. حدّ IP     — يمنع الغمر من مصدر واحد.
 *   2. حدّ مستخدم — يمنع مستخدماً مصرَّحاً من استنزاف الحصة.
 *   3. حصة الدفتر اليومية — الحقيقة النهائية، في قاعدة البيانات.
 */
export const SEND_RULES = {
  ip: { name: "send-ip", limit: 10, windowSec: 60 },
  user: { name: "send-user", limit: 5, windowSec: 60 },
} as const satisfies Record<string, RateLimitRule>;

export const sendLimiter = new MemoryLimiter();

/** ترويسات 429 القياسية، فيعرف العميل متى يعود. */
export function rateLimitHeaders(d: RateDecision, rule: RateLimitRule): Record<string, string> {
  return {
    "retry-after": String(d.retryAfterSec),
    "x-ratelimit-limit": String(rule.limit),
    "x-ratelimit-remaining": String(d.remaining),
    "cache-control": "no-store",
  };
}

/* ------------------------------------------------------------------------- */
/* تسجيل الأحداث الأمنية                                                      */
/* ------------------------------------------------------------------------- */

/**
 * سجل أمني في مسار واحد (`console` → سجلّات المنصة). القاعدة:
 * لا كلمة مرور، لا رمز جلسة، لا نص رسالة، لا بريد كامل. البصمة فقط.
 *
 * ما لا يُسجَّل لا يُحقَّق فيه. لذلك كل رفض مصادقة/أصل/حدّ يترك سطراً،
 * وسطراً واحداً لكل حدث — لا سجلّ كامل للطلبات يغرق الحقيقي.
 */
export function logSecurityEvent(
  event: string,
  fields: Record<string, string | number | boolean | null>,
): void {
  try {
    const line = JSON.stringify({
      evt: "security",
      event,
      at: new Date().toISOString(),
      ...fields,
    });
    // 4xx الأمنية ليست أعطالاً، لكنها تحتاج أثراً.
    console.warn(line);
  } catch {
    // التسجيل لا يُسقط الطلب أبداً.
  }
}

/**
 * تنبيه تكرار الفشل: العتبة `limit` داخل `windowSec` تُنتج سطر
 * `security_alert` **واحداً** لكل نافذة، لا سطراً لكل طلب بعدها.
 *
 * الفرق مهم: خادم يكتب تنبيهاً مع كل طلب مهاجَم يغرق سجلّه، والتنبيه
 * الذي يغرق لا يُقرأ. سطر واحد لكل نافذة = إشارة، لا ضجيج.
 *
 * الربط ببريد/Slack اختياري — أي مراقب يقرأ سطر `security_alert` يكفي.
 */
export const alertLimiter = new MemoryLimiter();
const alerted = new Set<string>();

export function maybeAlert(
  key: string,
  event: string,
  fields: Record<string, string | number | boolean | null>,
): void {
  const windowSec = 300;
  const rule: RateLimitRule = { name: `alert:${event}`, limit: 5, windowSec };
  const d = alertLimiter.check(key, rule);
  const slot = `${event}:${key}`;
  if (d.ok || alerted.has(slot)) return;

  alerted.add(slot);
  // نسقط الذاكرة بعد نافذتين حتى لا تنمو بلا سقف.
  setTimeout(() => alerted.delete(slot), windowSec * 2000).unref?.();
  logSecurityEvent("security_alert", { alert_for: event, window: windowSec, ...fields });
}
