import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import {
  selectProvider,
  scopeFooter,
  scopeTag,
  sendViaResend,
  sendViaGmail,
} from "@/lib/mailer";

/**
 * POST /api/send-email — التسليم الخلفي للبريد.
 *
 * الترتيب مقصود: اختيار المزوّد → التحقق من الحقول → الجلسة → المالك → الإرسال.
 * المزوّدان مجانيان: Resend أولاً، ثم Gmail SMTP (كلمة مرور التطبيقات).
 * بلا أي منهما يجيب not_configured (503) بصدق — لا تظاهر بإرسال.
 * الإسناد يُذيَّل حسب النطاق: تدريب → «مدرب الحاسب»، شخصي → «مدير الحاسب».
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

  let payload: { to?: string; subject?: string; body?: string; scope?: string };
  try {
    payload = (await req.json()) as typeof payload;
  } catch {
    return NextResponse.json({ status: "blocked", reason: "جسم غير صالح" }, { status: 400 });
  }

  const to = (payload.to ?? "").trim();
  const subject = (payload.subject ?? "").trim();
  const body = (payload.body ?? "").trim();
  const scope = payload.scope === "PERSONAL" ? "PERSONAL" : payload.scope === "TRAINING" ? "TRAINING" : null;

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
  // public.is_owner غلاف مالكية للمسارات الخلفية (انظر 0010).
  try {
    const sb = createClient(url, anon, {
      auth: { persistSession: false },
      global: { headers: { Authorization: `Bearer ${bearer}` } },
    });
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
    return NextResponse.json(
      { status: "failed", provider, reason: result.reason },
      { status: 502 },
    );
  }
  return NextResponse.json({ status: "sent", provider, provider_ref: result.providerRef });
}
