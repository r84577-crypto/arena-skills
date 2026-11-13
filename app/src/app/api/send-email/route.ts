import { NextResponse } from "next/server";
import {
  selectProvider,
  scopeFooter,
  scopeTag,
  sendViaResend,
  sendViaGmail,
} from "@/lib/mailer";
import {
  DAILY_QUOTA,
  fetchQueuedRow,
  sentInLast24h,
  updateLogRow,
} from "@/lib/comms-server";
import { requireOwner } from "@/lib/delivery-guard";
import {
  MAX_BODY_CHARS,
  MAX_SUBJECT_CHARS,
  email,
  int,
  jsonError,
  logSecurityEvent,
  oneOf,
  readJsonBody,
  sanitizeText,
  str,
} from "@/lib/security";

/**
 * POST /api/send-email — التسليم الخلفي للبريد.
 *
 * الترتيب مقصود: الحرّاس (Origin → حدّ IP → جلسة → مالك → حدّ مستخدم) →
 * المزوّد → الحقول → صف الدفتر → الحصة → الإرسال → التوثيق (خادماً).
 * الحرّاس قبل أي كشف لحالة التهيئة أو أي اتصال بقاعدة.
 *
 * 2026-11-13: الحماية صارت في `requireOwner` (Origin ثم حدّ IP ثم
 * الجلسة ثم المالك ثم حدّ المستخدم)، والجسم يُقرأ بسقف 16KB صريحاً
 * بدل `req.json()` الذي يقرأ أي حجم في الذاكرة.
 *
 * القاعدة المؤسسية: العميل يُسجِّل المسودة (queued) فقط ويمرّر id —
 * والخادم يتحقق من الصف (موجود + queued + مطابق) ويرفض إعادة التشغيل،
 * ثم يكتب النتيجة النهائية بنفسه. لا يوثَّق «أُرسلت» إلا من هنا.
 * الحصة: DAILY_QUOTA إرسال ناجح / 24 ساعة (كل القنوات) — تجاوزها 429.
 */

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(req: Request) {
  // الطبقة الأمنية أولاً — قبل أي شيء آخر.
  //
  // 2026-11-13: كان فحص تهيئة المزوّد يسبق التحقق من الجلسة، فأي زائر
  // يعرف من رد 503 هل البريد مهيّأ أم لا، ويتخطى الحرّاس كلهم. الآن لا
  // يرى حالة التهيئة إلا مالك مُثبَت.
  const guard = await requireOwner(req);
  if (!guard.ok) return guard.response;
  const { sb, userId } = guard;

  const provider = selectProvider({
    RESEND_API_KEY: process.env.RESEND_API_KEY,
    GMAIL_USER: process.env.GMAIL_USER,
    GMAIL_APP_PASSWORD: process.env.GMAIL_APP_PASSWORD,
  });
  if (!provider) {
    return jsonError(
      "لا مزوّد بريد مهيّأ — RESEND_API_KEY أو (GMAIL_USER + GMAIL_APP_PASSWORD)",
      503,
    );
  }

  const body = await readJsonBody(req);
  if (!body.ok) {
    logSecurityEvent("bad_request_body", { route: "/api/send-email", user: userId, status: body.status });
    return jsonError(body.reason, body.status);
  }
  const payload = body.value;

  const id = int(payload.id, { min: 1, max: Number.MAX_SAFE_INTEGER });
  const to = email(payload.to);
  const subject = str(payload.subject, { max: MAX_SUBJECT_CHARS, min: 1 });
  const rawText = str(payload.body, { max: MAX_BODY_CHARS, min: 1 });
  const scope = oneOf(payload.scope, ["PERSONAL", "TRAINING"] as const);
  // الحقول النصية تُنقّى من محارف التحكم وقلب الاتجاه قبل الإرسال.
  const text = rawText === null ? null : sanitizeText(rawText) || null;

  if (id === null) return jsonError("معرّف الدفتر مطلوب", 400);
  if (to === null) return jsonError("بريد المستلم غير صالح", 400);
  if (subject === null || text === null) return jsonError("حقول ناقصة أو خارج الحد", 400);
  if (scope === null) return jsonError("النطاق غير معروف", 400);

  // صف الدفتر: موجود + queued + مطابق — وإلا رفض بلا إرسال.
  const check = await fetchQueuedRow(sb, id, { channel: "email", to, scope });
  if (!check.ok) {
    logSecurityEvent("ledger_rejected", { route: "/api/send-email", user: userId, id });
    return jsonError(check.reason, 400);
  }

  // الحصة اليومية — تُوثَّق في الصف نفسه لتبقى الحقيقة واحدة.
  const sent = await sentInLast24h(sb);
  if (sent !== null && sent >= DAILY_QUOTA) {
    const reason = `تجاوزت الحصة اليومية (${DAILY_QUOTA} رسالة / 24 ساعة)`;
    const logged = await updateLogRow(sb, id, { status: "blocked", reason });
    return NextResponse.json(
      { status: "blocked", reason, ledger: logged ? "updated" : "update_failed" },
      { status: 429, headers: { "cache-control": "no-store" } },
    );
  }

  const fullText = `${text}\n\n—\n${scopeFooter(scope)}`;
  const taggedSubject = `‎[${scopeTag(scope)}] ${str(subject, { max: MAX_SUBJECT_CHARS }) ?? ""}`;

  const result =
    provider === "resend"
      ? await sendViaResend({
          apiKey: process.env.RESEND_API_KEY as string,
          from: process.env.RESEND_FROM || "onboarding@resend.dev",
          to,
          subject: taggedSubject,
          text: fullText,
        })
      : await sendViaGmail({
          user: process.env.GMAIL_USER as string,
          appPassword: process.env.GMAIL_APP_PASSWORD as string,
          to,
          subject: taggedSubject,
          text: fullText,
        });

  if (!result.ok) {
    // سبب المزوّد يُسجَّل خادماً، ويُعاد للمستخدم مختصراً بلا تفاصيل داخلية.
    logSecurityEvent("provider_failed", {
      route: "/api/send-email",
      user: userId,
      provider,
    });
    const logged = await updateLogRow(sb, id, { status: "failed", reason: result.reason });
    return NextResponse.json(
      { status: "failed", provider, reason: result.reason, ledger: logged ? "updated" : "update_failed" },
      { status: 502, headers: { "cache-control": "no-store" } },
    );
  }

  logSecurityEvent("message_sent", { route: "/api/send-email", user: userId, provider });
  const logged = await updateLogRow(sb, id, {
    status: "sent",
    providerRef: result.providerRef,
  });
  return NextResponse.json(
    {
      status: "sent",
      provider,
      provider_ref: result.providerRef,
      ledger: logged ? "updated" : "update_failed",
    },
    { headers: { "cache-control": "no-store" } },
  );
}
