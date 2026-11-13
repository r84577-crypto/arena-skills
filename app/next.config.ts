import type { NextConfig } from "next";

/**
 * ترويسات الأمان الثابتة (لا تعتمد على الطلب).
 *
 * لماذا ليست كلها هنا؟ الـ CSP تحتاج nonce جديداً لكل طلب، والملف يُقيَّم
 * مرة واحدة عند البناء — فتوليد الـ nonce هنا يعطي قيمة واحدة للجميع.
 * لذلك CSP تُبنى في `src/proxy.ts` (المصدر الوحيد للسياسة)، وهنا تبقى
 * الترويسات التي لا تتغير. أي ترويسة مكرّرة بين الملفين محذوفة عمداً،
 * فسياستان في ترويستين تعني تقاطعاً لا يفهمه أحد لاحقاً.
 *
 * المفردات:
 *   HSTS                      منع http بعد أول زيارة (سنتان + preload)
 *   X-Frame-Options           منع التأطير (طبقة أقدم من frame-ancestors)
 *   X-Content-Type-Options    منع تخمين النوع (نصّ يُنفَّذ كسكربت)
 *   Referrer-Policy           لا تسريب مسارات داخلية لمواقع أخرى
 *   Permissions-Policy        تعطيل الكاميرا/الموقع/الفوترة عن الواجهة
 *   COOP/CORP                 عزل نافذة/مورد عن أصل آخر
 */
const staticSecurityHeaders = [
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()",
  },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Cross-Origin-Resource-Policy", value: "same-origin" },
  { key: "X-Permitted-Cross-Domain-Policies", value: "none" },
];

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // لا `X-Powered-By: Next.js` — بصمة الإصدار تُسهّل استهداف ثغرة معروفة.
  poweredByHeader: false,

  async headers() {
    return [
      {
        source: "/(.*)",
        headers: staticSecurityHeaders,
      },
      // لا كاش على أي مسار API — ردود المراسلة خاصة ولا تُشارَك بين طلبات.
      {
        source: "/api/(.*)",
        headers: [{ key: "Cache-Control", value: "no-store, max-age=0" }],
      },
    ];
  },
};

export default nextConfig;
