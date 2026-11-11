import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import {
  DAILY_QUOTA,
  fetchQueuedRow,
  sentInLast24h,
  updateLogRow,
} from "@/lib/comms-server";

/**
 * POST /api/send-whatsapp — التسليم الخلفي للواتساب.
 *
 * البوابة مزدوجة: قيد CHECK في القاعدة يرفض أي رقم غير رقم المالك عند
 * التسجيل، وهذا المسار يُطبّع الرقم ويرفض أي غيره قبل الجلسة والمزوّد.
 * الترتيب: التهيئة → البوابة والتحقق → الجلسة والمالك → صف الدفتر →
 * الحصة → الإرسال → توثيق النتيجة في الدفتر (خادماً).
 * الرقم الوحيد المقبول: 966508247153 (0508247153).
 *
 * القاعدة المؤسسية: العميل يُسجِّل المسودة (queued) فقط ويمرّر id —
 * والخادم يتحقق من الصف (موجود + queued + مطابق) ويرفض إعادة التشغيل،
 * ثم يكتب النتيجة النهائية بنفسه. لا يوثَّق «أُرسلت» إلا من هنا.
 * الحصة: DAILY_QUOTA إرسال ناجح / 24 ساعة (كل القنوات) — تجاوزها 429.
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

  let payload: { id?: number; to?: string; body?: string; scope?: string };
  try {
    payload = (await req.json()) as typeof payload;
  } catch {
    return NextResponse.json({ status: "blocked", reason: "جسم غير صالح" }, { status: 400 });
  }

  const id = typeof payload.id === "number" ? payload.id : NaN;
  const normalized = normalize(payload.to ?? "");
  const body = (payload.body ?? "").trim();
  const scope = payload.scope === "PERSONAL" ? "PERSONAL" : payload.scope === "TRAINING" ? "TRAINING" : null;

  if (!Number.isInteger(id)) {
    return NextResponse.json({ status: "blocked", reason: "معرّف الدفتر مطلوب" }, { status: 400 });
  }
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
  // to_addr المخزّن بصيغة 966… وهو نفسه normalized هنا.
  const check = await fetchQueuedRow(sb, id, { channel: "whatsapp", to: normalized, scope });
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
      const reason = `المزوّد رفض (${res.status}): ${detail.slice(0, 200)}`;
      const logged = await updateLogRow(sb, id, { status: "failed", reason });
      return NextResponse.json(
        { status: "failed", reason, ledger: logged ? "updated" : "update_failed" },
        { status: 502 },
      );
    }
    const sentRes = (await res.json()) as { messages?: { id?: string }[] };
    const providerRef = sentRes.messages?.[0]?.id ?? null;
    const logged = await updateLogRow(sb, id, { status: "sent", providerRef });
    return NextResponse.json({
      status: "sent",
      provider_ref: providerRef,
      ledger: logged ? "updated" : "update_failed",
    });
  } catch (e) {
    const reason = e instanceof Error ? e.message : "خطأ شبكة";
    const logged = await updateLogRow(sb, id, { status: "failed", reason });
    return NextResponse.json(
      { status: "failed", reason, ledger: logged ? "updated" : "update_failed" },
      { status: 502 },
    );
  }
}
