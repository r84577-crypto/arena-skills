import { NextResponse } from "next/server";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import {
  SEND_RULES,
  allowedOrigins,
  checkOrigin,
  clientIp,
  jsonError,
  logSecurityEvent,
  maybeAlert,
  rateLimitHeaders,
  sendLimiter,
} from "@/lib/security";

/**
 * بوابة التسليم المشتركة بين `/api/send-email` و`/api/send-whatsapp`.
 *
 * كانت القواعد مكرّرة في الملفين، وكل تكرار هو فرصة لتباعد النسختين.
 * الآن الترتيب واحد في مكان واحد:
 *
 *   1. CSRF (Origin)         — الطلب ليس من موقع آخر باسم المستخدم.
 *   2. حدّ IP (429)          — لا غمر من مصدر واحد.
 *   3. ترويسة الجلسة         — الطلب ليس مجهولاً.
 *   4. حدّ المستخدم (429)    — لا استنزاف لمستخدم مصرَّح.
 *   5. تحقّق الجلسة + المالك — عبر القاعدة، لا ثقة بالعميل.
 *
 * الأرخص أولاً: من يفشل في (1) لا يكلّفنا استدعاء Supabase.
 */

export type Guarded =
  | { ok: true; sb: SupabaseClient; userId: string }
  | { ok: false; response: NextResponse };

export async function requireOwner(req: Request): Promise<Guarded> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anon) {
    return { ok: false, response: jsonError("إعدادات الخادم غير مكتملة", 500) };
  }

  // (1) CSRF — كل طلب تسليم هو تغيير حالة (يرسل رسالة حقيقية).
  const origin = checkOrigin(req, allowedOrigins(req));
  if (!origin.ok) {
    logSecurityEvent("csrf_rejected", { route: new URL(req.url).pathname, ip: clientIp(req) });
    return { ok: false, response: jsonError("طلب من أصل غير مسموح", 403) };
  }

  // (2) حدّ IP.
  const ip = clientIp(req);
  const ipDecision = sendLimiter.check(ip, SEND_RULES.ip);
  if (!ipDecision.ok) {
    logSecurityEvent("rate_limited", { scope: "ip", route: new URL(req.url).pathname, ip });
    maybeAlert(ip, "rate_limited", { scope: "ip", ip });
    return {
      ok: false,
      response: jsonError("طلبات كثيرة — أعد المحاولة بعد قليل", 429, rateLimitHeaders(ipDecision, SEND_RULES.ip)),
    };
  }

  // (3) رمز الجلسة.
  const bearer = req.headers.get("authorization")?.replace(/^Bearer\s+/i, "").trim();
  if (!bearer) {
    logSecurityEvent("auth_missing_token", { ip, route: new URL(req.url).pathname });
    return { ok: false, response: jsonError("بلا رمز جلسة", 401) };
  }

  // التحقق من الجلسة قبل حدّ المستخدم: المفتاح هو هوية موثّقة، لاuid مُدَّعى.
  const sb = createClient(url, anon, {
    auth: { persistSession: false, autoRefreshToken: false },
    global: { headers: { Authorization: `Bearer ${bearer}` } },
  });

  let userId: string;
  try {
    const { data, error } = await sb.auth.getUser(bearer);
    if (error || !data.user) {
      logSecurityEvent("auth_invalid_session", { ip });
      maybeAlert(ip, "auth_invalid_session", { ip });
      return { ok: false, response: jsonError("جلسة غير صالحة", 401) };
    }
    userId = data.user.id;

    const { data: isOwner, error: ownerError } = await sb.rpc("is_owner");
    if (ownerError || !isOwner) {
      logSecurityEvent("authz_denied", { ip, user: userId });
      return { ok: false, response: jsonError("ليس المالك", 403) };
    }
  } catch {
    // لا رسالة مزوّد للمستخدم — التفاصيل في السجل.
    logSecurityEvent("auth_backend_unavailable", { ip });
    return { ok: false, response: jsonError("تعذّر التحقق من الجلسة", 503) };
  }

  // (4) حدّ المستخدم بعد إثبات الهوية (لا يمكن تحايله بتغيير الـ IP وحده).
  const userDecision = sendLimiter.check(userId, SEND_RULES.user);
  if (!userDecision.ok) {
    logSecurityEvent("rate_limited", { scope: "user", user: userId });
    return {
      ok: false,
      response: jsonError("تجاوزت الحد — أعد المحاولة بعد قليل", 429, rateLimitHeaders(userDecision, SEND_RULES.user)),
    };
  }

  return { ok: true, sb, userId };
}
