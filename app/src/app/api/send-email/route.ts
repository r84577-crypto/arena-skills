import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

/**
 * POST /api/send-email — التسليم الخلفي للبريد.
 *
 * الترتيب مقصود: التهيئة → التحقق من الحقول → الجلسة → المالك → الإرسال.
 * بلا RESEND_API_KEY يجيب not_configured (503) بصدق — لا تظاهر بإرسال.
 * الإسناد يُذيَّل حسب النطاق: تدريب → «مدرب الحاسب»، شخصي → «مدير الحاسب».
 */

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const MAX_BODY = 4000;

const FOOTERS: Record<string, string> = {
  TRAINING: "تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدرب الحاسب",
  PERSONAL: "تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدير الحاسب",
};

export async function POST(req: Request) {
  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) {
    return NextResponse.json(
      { status: "not_configured", reason: "RESEND_API_KEY غير مهيّأ على الخادم" },
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

  const text = `${body}\n\n—\n${FOOTERS[scope]}`;

  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: process.env.RESEND_FROM || "onboarding@resend.dev",
        to: [to],
        subject: `‎[${scope === "TRAINING" ? "تدريب" : "شخصي"}] ${subject}`,
        text,
      }),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      return NextResponse.json(
        { status: "failed", reason: `المزوّد رفض (${res.status}): ${detail.slice(0, 200)}` },
        { status: 502 },
      );
    }
    const sent = (await res.json()) as { id?: string };
    return NextResponse.json({ status: "sent", provider_ref: sent.id ?? null });
  } catch (e) {
    return NextResponse.json(
      { status: "failed", reason: e instanceof Error ? e.message : "خطأ شبكة" },
      { status: 502 },
    );
  }
}
