import { NextResponse } from "next/server";
import {
  DAILY_QUOTA,
  fetchQueuedRow,
  sentInLast24h,
  updateLogRow,
} from "@/lib/comms-server";
import { OWNER_NUMBER, normalize } from "@/lib/phone";
import { requireOwner } from "@/lib/delivery-guard";
import {
  MAX_BODY_CHARS,
  int,
  jsonError,
  logSecurityEvent,
  oneOf,
  readJsonBody,
  sanitizeText,
  str,
} from "@/lib/security";

/**
 * POST /api/send-whatsapp — التسليم الخلفي للواتساب.
 *
 * البوابة مزدوجة: قيد CHECK في القاعدة يرفض أي رقم غير رقم المالك عند
 * التسجيل، وهذا المسار يُطبّع الرقم ويرفض أي غيره قبل المزوّد.
 * الترتيب: requireOwner (Origin → حدّ IP → جلسة → مالك → حدّ مستخدم) →
 * بوابة الرقم والتحقق من الحقول → التهيئة → صف الدفتر → الحصة → الإرسال
 * → التوثيق. الحرّاس قبل أي كشف لحالة التهيئة.
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

const FOOTERS: Record<string, string> = {
  TRAINING: "تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدرب الحاسب",
  PERSONAL: "تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدير الحاسب",
};

export async function POST(req: Request) {
  // الحرّاس أولاً: لا يُكشف شيء عن التهيئة قبل إثبات الهوية.
  const guard = await requireOwner(req);
  if (!guard.ok) return guard.response;
  const { sb, userId } = guard;

  const token = process.env.WHATSAPP_TOKEN;
  const phoneId = process.env.WHATSAPP_PHONE_NUMBER_ID;
  if (!token || !phoneId) {
    return jsonError("WHATSAPP_TOKEN أو WHATSAPP_PHONE_NUMBER_ID غير مهيّأ", 503);
  }

  const body = await readJsonBody(req);
  if (!body.ok) {
    logSecurityEvent("bad_request_body", { route: "/api/send-whatsapp", user: userId, status: body.status });
    return jsonError(body.reason, body.status);
  }
  const payload = body.value;

  const id = int(payload.id, { min: 1, max: Number.MAX_SAFE_INTEGER });
  const normalized = normalize(str(payload.to, { max: 32, min: 3 }) ?? "");
  const rawText = str(payload.body, { max: MAX_BODY_CHARS, min: 1 });
  const text = rawText === null ? null : sanitizeText(rawText) || null;
  const scope = oneOf(payload.scope, ["PERSONAL", "TRAINING"] as const);

  if (id === null) return jsonError("معرّف الدفتر مطلوب", 400);
  // البوابة: أي رقم غير رقم المالك يُرفض هنا — قبل المزوّد.
  if (normalized !== OWNER_NUMBER) {
    logSecurityEvent("whatsapp_recipient_rejected", { user: userId });
    return jsonError("الواتساب مقفل على رقم المالك وحده", 403);
  }
  if (text === null) return jsonError("النص ناقص أو خارج الحد", 400);
  if (scope === null) return jsonError("النطاق غير معروف", 400);

  // صف الدفتر: موجود + queued + مطابق — وإلا رفض بلا إرسال.
  const check = await fetchQueuedRow(sb, id, { channel: "whatsapp", to: normalized, scope });
  if (!check.ok) {
    logSecurityEvent("ledger_rejected", { route: "/api/send-whatsapp", user: userId, id });
    return jsonError(check.reason, 400);
  }

  const sent = await sentInLast24h(sb);
  if (sent !== null && sent >= DAILY_QUOTA) {
    const reason = `تجاوزت الحصة اليومية (${DAILY_QUOTA} رسالة / 24 ساعة)`;
    const logged = await updateLogRow(sb, id, { status: "blocked", reason });
    return NextResponse.json(
      { status: "blocked", reason, ledger: logged ? "updated" : "update_failed" },
      { status: 429, headers: { "cache-control": "no-store" } },
    );
  }

  const fullText = `${text}\n\n—\n${FOOTERS[scope]}`;

  try {
    const res = await fetch(`https://graph.facebook.com/v21.0/${encodeURIComponent(phoneId)}/messages`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messaging_product: "whatsapp",
        to: normalized,
        type: "text",
        text: { body: fullText },
      }),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      logSecurityEvent("provider_failed", {
        route: "/api/send-whatsapp",
        user: userId,
        status: res.status,
      });
      const reason = `المزوّد رفض (${res.status}): ${detail.slice(0, 200)}`;
      const logged = await updateLogRow(sb, id, { status: "failed", reason });
      return NextResponse.json(
        { status: "failed", reason, ledger: logged ? "updated" : "update_failed" },
        { status: 502, headers: { "cache-control": "no-store" } },
      );
    }
    const sentRes = (await res.json()) as { messages?: { id?: string }[] };
    const providerRef = sentRes.messages?.[0]?.id ?? null;
    logSecurityEvent("message_sent", { route: "/api/send-whatsapp", user: userId });
    const logged = await updateLogRow(sb, id, { status: "sent", providerRef });
    return NextResponse.json(
      { status: "sent", provider_ref: providerRef, ledger: logged ? "updated" : "update_failed" },
      { headers: { "cache-control": "no-store" } },
    );
  } catch {
    logSecurityEvent("provider_unreachable", { route: "/api/send-whatsapp", user: userId });
    const reason = "تعذّر الوصول لمزوّد الواتساب";
    const logged = await updateLogRow(sb, id, { status: "failed", reason });
    return NextResponse.json(
      { status: "failed", reason, ledger: logged ? "updated" : "update_failed" },
      { status: 502, headers: { "cache-control": "no-store" } },
    );
  }
}
