import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

/**
 * عميل المتصفح. لا يستخدم إلا المفتاح العام (anon/publishable).
 * مفتاح service_role ممنوع من الظهور في أي ملف يصل إلى المتصفح — لا يوجد
 * في هذا المشروع أي متغيّر يبدأ بـ NEXT_PUBLIC_ يحمل صلاحية إدارية.
 *
 * RLS في قاعدة البيانات هو خط الدفاع الحقيقي، لا هذا الملف. هذا الملف
 * يحدّد من نتصل به فقط.
 */

let cached: SupabaseClient | null = null;

export function supabaseBrowser(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) return null;
  if (!cached) cached = createBrowserClient(url, key);
  return cached;
}

/** هل توجد جلسة مالك نشطة؟ */
export async function hasSession(): Promise<boolean> {
  const sb = supabaseBrowser();
  if (!sb) return false;
  const { data } = await sb.auth.getSession();
  return Boolean(data.session);
}

/** رمز الوصول للجلسة الحالية — يُرسل لمسارات API الخلفية. */
export async function getAccessToken(): Promise<string | null> {
  const sb = supabaseBrowser();
  if (!sb) return null;
  const { data } = await sb.auth.getSession();
  return data.session?.access_token ?? null;
}

/**
 * دخول المالك. كلمة المرور لا تُخزَّن هنا ولا تُسجَّل.
 * تُرجَع رسالة عربية عند الفشل بدل نص المزوّد الإنجليزي.
 */
export async function signInOwner(
  email: string,
  password: string,
): Promise<{ ok: true } | { ok: false; reason: string }> {
  const sb = supabaseBrowser();
  if (!sb) return { ok: false, reason: "متغيّرات البيئة غير مضبوطة" };

  const { error } = await sb.auth.signInWithPassword({ email, password });
  if (error) {
    return {
      ok: false,
      reason:
        error.message === "Invalid login credentials"
          ? "بيانات الدخول غير صحيحة"
          : error.message,
    };
  }
  return { ok: true };
}

export async function signOutOwner(): Promise<void> {
  const sb = supabaseBrowser();
  await sb?.auth.signOut();
}

/** إسناد الواجهة (النطاق الشخصي السيادي). */
export const ATTRIBUTION =
  "تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدير الحاسب";

/** إسناد نطاق التدريب — يُذيَّل به كل مراسَل تدريبي صادر. */
export const TRAINING_ATTRIBUTION =
  "تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدرب الحاسب";
