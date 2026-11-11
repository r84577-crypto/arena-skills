import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
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

/**
 * POST /api/send-email — التسليم الخلفي للبريد.
 *
 * الترتيب مقصود: المزوّد → الحقول → الجلسة والمالك → صف الدفتر →
 * الحصة → الإرسال → توثيق النتيجة في الدفتر (خادماً).
 * المزوّدان مجانيان: Resend أولاً، ثم Gmail SMTP (كلمة مرور التطبيقات).
 * بلا أي منهما يجيب not_configured (503) بصدق — لا تظاهر بإرسال.
 * الإسناد يُذيَّل حسب النطاق: تدريب → «مدرب الحاسب»، شخصي → «مدير الحاسب».
 *
 * القاعدة المؤسسية: العميل يُسجِّل المسودة (queued) فقط ويمرّر id —
 * والخادم يتحقق من الصف (موجود + queued + مطابق) ويرفض إعادة التشغيل،
 * ثم يكتب النتيجة النهائية بنفسه. لا يوثَّق «أُرسلت» إلا من هنا.
 * الحصة: DAILY_QUOTA إرسال ناجح / 24 ساعة (كل القنوات) — تجاوزها 429.
 */

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const MAX_BODY = 4000;

export async function POST(req: Request) {
  // كائن صريح لا process.env مباشرة — فهرس البيئة لا يُرضي فاحص الأنواع الضعيفة.
  const provider = selectProvider({
    RESEND_API_KEY: process.env.RESEND_API_KEY,
    GMAIL_USER: process.env.GMAIL_USER,
    GMAIL_APP_PASSWORD: process.env.GMAIL_APP_PASSWORD,
  });
  if (!provider) {
    return NextResponse.json(
      {
        status: "not_configured",
        reason: "لا مزوّد بريد مهيّأ — RESEND_API_KEY أو (GMAIL_USER + GMAIL_APP_PASSWORD)",
      },
      { status: 503 },
    );
  }

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anon) {
    return NextResponse.json(
      { status: "failed", reason: "إعدادات Supabase ناقصة على الخادم" },
      { status: 500 },
    );
  }

  let payload: { id?: number; to?: string; subject?: string; body?: string; scope?: string };
  try {
    payload = (await req.json()) as typeof payload;
  } catch {
    return NextResponse.json({ status: "blocked", reason: "جسم غير صالح" }, { status: 400 });
  }

  const id = typeof payload.id === "number" ? payload.id : NaN;
  const to = (payload.to ?? "").trim();
  const subject = (payload.subject ?? "").trim();
  const body = (payload.body ?? "").trim();
  const scope = payload.scope === "PERSONAL" ? "PERSONAL" : payload.scope === "TRAINING" ? "TRAINING" : null;

  if (!Number.isInteger(id)) {
    return NextResponse.json({ status: "blocked", reason: "معرّف الدفتر مطلوب" }, { status: 400 });
  }
  if (!EMAIL_RE.test(to)) {
    return NextResponse.json({ status: "blocked", reason: "بريد المستلم غير صالح" }, { status: 400 });
  }
  if (!subject || !body || body.length > MAX_BODY || !scope) {
    return NextResponse.json({ status: "blocked", reason: "حقول ناقصة أو خارج الحد" }, { status: 400 });
  }

  const bearer = req.headers.get("authorization")?.replace(/^Bearer\s+/i, "");
  if (!bearer) {
    return NextResponse.json({ status: "blocked", reason: "بلا رمز جلسة" }, { status: 401 });
  }

  // التحقق من الجلسة والمالكية عبر القاعدة نفسها — لا ثقة عمياء بالعميل.
  // public.is_owner غلاف مالكية للمسارات الخلفية.
  const sb = createClient(url, anon, {
    auth: { persistSession: false },
    global: { headers: { Authorization: `Bearer ${bearer}` } },
  });
  try {
    const { data: userData, error: userError } = await sb.auth.getUser(bearer);
    if (userError || !userData.user) {
      return NextResponse.json({ status: "blocked", reason: "جلسة غير صالحة" }, { status: 401 });
    }
    const { data: isOwner, error: ownerError } = await sb.rpc("is_owner");
    if (ownerError || !isOwner) {
      return NextResponse.json({ status: "blocked", reason: "ليس المالك" }, { status: 403 });
    }
  } catch {
    return NextResponse.json(
      { status: "failed", reason: "تعذّر الوصول لخدمة التحقق" },
      { status: 503 },
    );
  }

  // صف الدفتر: موجود + queued + مطابق — وإلا رفض بلا إرسال.
  const check = await fetchQueuedRow(sb, id, { channel: "email", to, scope });
  if (!check.ok) {
    return NextResponse.json({ status: "blocked", reason: check.reason }, { status: 400 });
  }

  // الحصة اليومية — تُوثَّق في الصف نفسه لتبقى الحقيقة واحدة.
  const sent = await sentInLast24h(sb);
  if (sent !== null && sent >= DAILY_QUOTA) {
    const reason = `تجاوزت الحصة اليومية (${DAILY_QUOTA} رسالة / 24 ساعة)`;
    const logged = await updateLogRow(sb, id, { status: "blocked", reason });
    return NextResponse.json(
      { status: "blocked", reason, ledger: logged ? "updated" : "update_failed" },
      { status: 429 },
    );
  }

  const text = `${body}\n\n—\n${scopeFooter(scope)}`;
  const taggedSubject = `‎[${scopeTag(scope)}] ${subject}`;

  const result =
    provider === "resend"
      ? await sendViaResend({
          apiKey: process.env.RESEND_API_KEY as string,
          from: process.env.RESEND_FROM || "onboarding@resend.dev",
          to,
          subject: taggedSubject,
          text,
        })
      : await sendViaGmail({
          user: process.env.GMAIL_USER as string,
          appPassword: process.env.GMAIL_APP_PASSWORD as string,
          to,
          subject: taggedSubject,
          text,
        });

  if (!result.ok) {
    const logged = await updateLogRow(sb, id, { status: "failed", reason: result.reason });
    return NextResponse.json(
      { status: "failed", provider, reason: result.reason, ledger: logged ? "updated" : "update_failed" },
      { status: 502 },
    );
  }
  const logged = await updateLogRow(sb, id, {
    status: "sent",
    providerRef: result.providerRef,
  });
  return NextResponse.json({
    status: "sent",
    provider,
    provider_ref: result.providerRef,
    ledger: logged ? "updated" : "update_failed",
  });
}
