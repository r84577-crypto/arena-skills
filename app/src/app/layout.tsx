import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "عادل الحربي — النظام السيادي",
  description: "توأم رقمي شخصي: ذاكرة دائمة، روتين صحي، ولوحة سيادة.",
  // الموقع خاص: لا فهرسة، ولا أرشفة، ولا معاينة في محركات البحث.
  robots: {
    index: false,
    follow: false,
    nocache: true,
    googleBot: { index: false, follow: false, noimageindex: true },
  },
  authors: [{ name: "عادل عبدالله الحربي" }],
};

export const viewport: Viewport = {
  themeColor: "#0a0d14",
  width: "device-width",
  initialScale: 1,
};

/**
 * `force-dynamic` هنا ليس ترفاً.
 *
 * الـ nonce يتغيّر كل طلب، والصفحة المُصيَّرة مسبقاً عند البناء تحمل
 * nonce واحداً أو لا تحمل شيئاً — فتفسد السياسة. تصيير كل طلب هو الثمن
 * الوحيد لـ CSP حقيقية بلا `unsafe-inline`، والموقع صفحة واحدة لمستخدم
 * واحد، فالثمن مقبول ومقصود.
 */
export const dynamic = "force-dynamic";

/**
 * الطبقة الجذرية.
 *
 * ملاحظة على الـ CSP: لا يوجد سكربت مضمّن يكتبه هذا المشروع، وسكربتات
 * Next نفسها تُوسَم بالـ nonce تلقائياً لأن `src/proxy.ts` يضع ترويسة
 * `content-security-policy` على *طلب* التصيير — وهذا هو العقد الذي
 * يقرأه Next. لذلك لا يُمرَّر الـ nonce يدوياً هنا، وأي سكربت مضمّن
 * يُضاف مستقبلاً يجب أن يأخذ `nonce` من `headers().get("x-nonce")`.
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
