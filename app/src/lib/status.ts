import { supabaseBrowser } from "./supabase";

/**
 * قراءة حالة النظام — من المتصفح، بجلسة المالك.
 *
 * لماذا بجلسة المالك؟ لأن الدالة `public.sovereign_status` سُحبت من `anon`:
 * كانت تُعيد عدّادات الصحة والذاكرة لأي زائر يحمل المفتاح العام. الآن
 * الدالة للمسجّل وحده، فلا بد من الجلسة قبل قراءتها.
 *
 * إصلاح 2026-11-09 (عيب الزرّين): كانت هذه الدالة تفتح عميلاً جديداً بلا
 * جلسة (`persistSession: false`)، فينجح الدخول ثم تفشل القراءة فوراً —
 * فيرى المالك شاشة خطأ وزر «إعادة محاولة» لا يعمل أبداً مهما ضُغط.
 * الآن تُستخدم الجلسة نفسها، فالدخول الواحد يكفي.
 */

export type Status = {
  facts: number;
  memory: number;
  memory_embedded: number;
  entities: number;
  edges: number;
  health_logs: number;
  routines: number;
  milestones: number;
  sync_ok: number;
  sync_failed: number;
  training_courses: number;
  training_visits: number;
  probes: number;
  router_decisions: number;
  comms_queued: number;
  comms_sent: number;
  security_verdict: "clean" | "drift" | null;
  last_sync: string;
  generated_at: string;
};

export type StatusResult =
  | { ok: true; data: Status }
  | { ok: false; reason: string };

export async function fetchStatus(): Promise<StatusResult> {
  const sb = supabaseBrowser();
  if (!sb) {
    return { ok: false, reason: "متغيّرات البيئة غير مضبوطة" };
  }

  try {
    const { data: sessionData } = await sb.auth.getSession();
    if (!sessionData.session) {
      return { ok: false, reason: "لا توجد جلسة — سجّل الدخول أولاً" };
    }

    const { data, error } = await sb.rpc("sovereign_status");

    if (error) return { ok: false, reason: error.message };
    if (!data) return { ok: false, reason: "استجابة فارغة" };

    return { ok: true, data: data as Status };
  } catch (e) {
    return { ok: false, reason: e instanceof Error ? e.message : "خطأ غير معروف" };
  }
}
