import { NextResponse } from "next/server";

/**
 * GET /api/health — نبض المؤسسية للمراقبة الخارجية (UptimeRobot ونحوه).
 *
 * عام بلا جلسة عمداً — ويعيد قيماً منطقية فقط (مهيّأ/غير مهيّأ)،
 * لا أسرار ولا عدّادات ولا أي بيانات مالك.
 */
export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  const mail =
    Boolean(process.env.RESEND_API_KEY) ||
    Boolean(process.env.GMAIL_USER && process.env.GMAIL_APP_PASSWORD);
  const whatsapp = Boolean(
    process.env.WHATSAPP_TOKEN && process.env.WHATSAPP_PHONE_NUMBER_ID,
  );
  const supabase = Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  );

  return NextResponse.json({
    status: "ok",
    time: new Date().toISOString(),
    commit:
      process.env.COMMIT_REF ||
      process.env.VERCEL_GIT_COMMIT_SHA ||
      "dev",
    configured: { supabase, mail, whatsapp },
  });
}
