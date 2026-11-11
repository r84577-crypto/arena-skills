import type { SupabaseClient } from "@supabase/supabase-js";

/**
 * دفتر المراسلة — الطرف الخادم (لا يُستورَد في المتصفح أبداً).
 *
 * القاعدة المؤسسية: العميل يُسجِّل المسودة (queued) فقط، والخادم وحده
 * هو من يتحقق ويُرسل ويكتب النتيجة النهائية. هذا يمنع عميلاً معدّلاً
 * من تزوير «أُرسلت»، ويمنع إعادة تشغيل صفٍّ قديم (replay).
 *
 * كل الاستعلامات هنا تمر بسياسات RLS (عميل anon + رمز الجلسة)، فلا
 * ثقة عمياء: الصف يُقرأ ويُحدَّث بصفة المالك فقط.
 */

/** الحصة القصوى للإرسال الناجح — نافذة 24 ساعة متحركة، كل القنوات معاً. */
export const DAILY_QUOTA = 50;

export type Channel = "email" | "whatsapp";

export type QueuedRow = {
  id: number;
  actor: string;
  channel: string;
  scope: string;
  to_addr: string;
  status: string;
};

export type RowCheck =
  | { ok: true; row: QueuedRow }
  | { ok: false; reason: string };

/**
 * جلب صف الدفتر والتحقق أنه مسودة صالحة لهذا الإرسال:
 * موجود + بحالة queued + يطابق القناة والمستلم والنطاق.
 * أي اختلاف = رفض بلا إرسال.
 */
export async function fetchQueuedRow(
  sb: SupabaseClient,
  id: number,
  expected: { channel: Channel; to: string; scope: string },
): Promise<RowCheck> {
  const { data, error } = await sb
    .from("comms_log")
    .select("id,actor,channel,scope,to_addr,status")
    .eq("id", id)
    .single();

  if (error || !data) {
    return { ok: false, reason: "صف الدفتر غير موجود" };
  }
  const row = data as QueuedRow;
  if (row.status !== "queued") {
    return { ok: false, reason: "الصف ليس مسودة — رُفضت إعادة التشغيل" };
  }
  if (row.channel !== expected.channel || row.to_addr !== expected.to || row.scope !== expected.scope) {
    return { ok: false, reason: "بيانات الإرسال لا تطابق صف الدفتر" };
  }
  return { ok: true, row };
}

export type LedgerUpdate = {
  status: "sent" | "failed" | "blocked";
  reason?: string | null;
  providerRef?: string | null;
};

/**
 * كتابة النتيجة النهائية في الدفتر. لا ترمي أبداً — الفشل يُبلَّغ
 * للمسار ليصرّح به بصدق (ledger:update_failed) بدل الصمت.
 */
export async function updateLogRow(
  sb: SupabaseClient,
  id: number,
  u: LedgerUpdate,
): Promise<boolean> {
  try {
    const { error } = await sb
      .from("comms_log")
      .update({
        status: u.status,
        reason: u.reason ?? null,
        provider_ref: u.providerRef ?? null,
        sent_at: u.status === "sent" ? new Date().toISOString() : null,
      })
      .eq("id", id);
    return !error;
  } catch {
    return false;
  }
}

/** عدد الرسائل المرسلة بنجاح خلال آخر 24 ساعة (للحصة). */
export async function sentInLast24h(sb: SupabaseClient): Promise<number | null> {
  try {
    const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    const { count, error } = await sb
      .from("comms_log")
      .select("id", { count: "exact", head: true })
      .eq("status", "sent")
      .gte("created_at", since);
    if (error || count === null) return null;
    return count;
  } catch {
    return null;
  }
}
