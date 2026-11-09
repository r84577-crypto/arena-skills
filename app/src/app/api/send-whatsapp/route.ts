import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

/**
 * POST /api/send-whatsapp — التسليم الخلفي للواتساب.
 *
 * البوابة مزدوجة: قيد CHECK في القاعدة يرفض أي رقم غير رقم المالك عند
 * التسجيل، وهذا المسار يُطبّع الرقم ويرفض أي غيره قبل الجلسة والمزوّد.
 * الترتيب: التهيئة → البوابة والتحقق → الجلسة → المالك → الإرسال.
 * الرقم الوحيد المقبول: 966508247153 (0508247153).
 *
 * ملاحظة Meta: الرسائل النصية الحرة تحتاج نافذة محادثة نشطة (24 ساعة)؛
 * خارجها يرفض المزوّد — ونحن نعرض رفضه بصدق بدل ادعاء الإرسال.
 */

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const OWNER_NUMBER = "966508247153";
const MAX_BODY = 4000;

const FOOTERS: Record<string, string> = {
  TRAINING: "تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدرب الحاسب",
  PERSONAL: "تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدير الحاسب",
};

/** تطبيع كل الصيغ (0508247153، ‎+966…‎، 966…) إلى صيغة واحدة. */
function normalize(input: string): string | null {
  const digits = input.replace(/\D/g, "");
  if (/^9665\d{8}$/.test(digits)) return digits;
  if (/^05\d{8}$/.test(digits)) return `966${digits.slice(1)}`;
  if (/^5\d{8}$/.test(digits)) return `966${digits}`;
  return null;
}

export async function POST(req: Request) {
  const token = process.env.WHATSAPP_TOKEN;
  const phoneId = process.env.WHATSAPP_PHONE_NUMBER_ID;
  if (!token || !phoneId) {
    return NextResponse.json(
      { status: "not_configured", reason: "WHATSAPP_TOKEN أو WHATSAPP_PHONE_NUMBER_ID غير مهيّأ" },
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

  let payload: { to?: string; body?: string; scope?: string };
  try {
    payload = (await req.json()) as typeof payload;
  } catch {
    return NextResponse.json({ status: "blocked", reason: "جسم غير صالح" }, { status: 400 });
  }

  const normalized = normalize(payload.to ?? "");
  const body = (payload.body ?? "").trim();
  const scope = payload.scope === "PERSONAL" ? "PERSONAL" : payload.scope === "TRAINING" ? "TRAINING" : null;

  // البوابة: أي رقم غير رقم المالك يُرفض هنا — قبل المزوّد وقبل الجلسة،
  // فالرقم المقبول معلن أصلاً ولا سر يُكشف برفض غيره.
  if (normalized !== OWNER_NUMBER) {
    return NextResponse.json(
      { status: "blocked", reason: "الواتساب مقفل على رقم المالك وحده" },
      { status: 403 },
    );
  }
  if (!body || body.length > MAX_BODY || !scope) {
    return NextResponse.json({ status: "blocked", reason: "حقول ناقصة أو خارج الحد" }, { status: 400 });
  }

  const bearer = req.headers.get("authorization")?.replace(/^Bearer\s+/i, "");
  if (!bearer) {
    return NextResponse.json({ status: "blocked", reason: "بلا رمز جلسة" }, { status: 401 });
  }

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
    const res = await fetch(`https://graph.facebook.com/v21.0/${phoneId}/messages`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messaging_product: "whatsapp",
        to: normalized,
        type: "text",
        text: { body: text },
      }),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      return NextResponse.json(
        { status: "failed", reason: `المزوّد رفض (${res.status}): ${detail.slice(0, 200)}` },
        { status: 502 },
      );
    }
    const sent = (await res.json()) as { messages?: { id?: string }[] };
    return NextResponse.json({ status: "sent", provider_ref: sent.messages?.[0]?.id ?? null });
  } catch (e) {
    return NextResponse.json(
      { status: "failed", reason: e instanceof Error ? e.message : "خطأ شبكة" },
      { status: 502 },
    );
  }
}
