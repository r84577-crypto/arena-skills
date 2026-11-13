import { NextResponse } from "next/server";

/**
 * GET /api/health — نبض للمراقبة الخارجية (UptimeRobot ونحوه).
 *
 * 2026-11-13: كان يعيد `configured: {supabase, mail, whatsapp}` لأي زائر.
 * هذا كشف مجاني لمهاجم: «الواتساب غير مهيّأ» تعني أن غمر ذلك المسار لا
 * يكلّف المالك شيئاً، و«البريد مهيّأ» تعني أن استنزاف الحصة ممكن. لا
 * بيانات مالك كانت مكشوفة، لكن حالة التهيئة الداخلية ليست معلومة عامة.
 *
 * الآن: كلمة واحدة. `ok` تعني أن الخادم يرد. لا إصدار، لا commit، لا
 * حالة تهيئة. من يحتاج تفاصيل التهيئة يقرأ سجلّات المنصة بصلاحية.
 */
export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  return NextResponse.json(
    { status: "ok" },
    {
      headers: {
        "cache-control": "no-store, max-age=0",
        "X-Robots-Tag": "noindex, nofollow",
      },
    },
  );
}
