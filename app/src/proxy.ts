import { NextResponse, type NextRequest } from "next/server";

/**
 * بوابة الطلب الأولى (Next.js 16 يسمّيها `proxy` بدل `middleware`).
 * تعمل على حافة الشبكة قبل الوصول إلى أي صفحة أو مسار API.
 *
 * مسؤولياتها ثلاث فقط:
 *
 *  1. HTTPS إجباري: أي طلب `http:` يُحوَّل 308 إلى `https:` قبل أي شيء.
 *     (HSTS في `next.config.ts` يمنع المتصفح من إرسال http أصلاً بعد أول
 *     زيارة؛ هذا يحمي أول زيارة وطلبات curl.)
 *
 *  2. CSP بـ nonce لكل طلب: `script-src` لم يبقَ فيه `unsafe-inline`.
 *     الترويسة الثابتة في `next.config.ts` لا تعرف الـ nonce لأنها تُحسب
 *     مرة واحدة عند البناء، لذلك الـ nonce يُنتج هنا ويُحقن في تفسير
 *     السكربتات، ثم يستبدل الترويسة.
 *
 *     لا `unsafe-eval`: لا شيء في الكود يستخدم eval/new Function، وإزالة
 *     `unsafe-eval` تغلق حقن السكربت عبر أي مسار يعتمد عليه.
 *
 *  3. ذاكرة المخبأ (x-nextjs-cache / CDN): لا شيء هنا يُخزَّن، فصفحة
 *     المالك لا يجوز أن تصل من كاش مشترك.
 *
 * ملاحظة صريحة: الصفحات تُصيَّر بـ nonce جديد لكل طلب، فتُصبح غير قابلة
 * للتخزين المؤقت — وهذا مقصود. صفحة لوحة المالك ليست محتوى عاماً.
 */

/** مسارات لا تحتاج CSP سكربت: أصول ثابتة تُخدم كما هي. */
function isStaticAsset(pathname: string): boolean {
  return (
    pathname.startsWith("/_next/static/") ||
    pathname.startsWith("/_next/image") ||
    pathname === "/favicon.ico" ||
    /\.(?:svg|png|jpg|jpeg|gif|webp|ico|txt|xml|json|webmanifest|woff2?)$/i.test(pathname)
  );
}

/** أصل الموقع: من البيئة إن ضُبط، وإلا من ترويسة المنصة، وإلا مضيف الطلب. */
function requestOrigin(req: NextRequest): string {
  const configured = process.env.SITE_ORIGIN?.trim();
  if (configured) return configured.replace(/\/$/, "");

  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
  const proto = req.headers.get("x-forwarded-proto") ?? req.nextUrl.protocol.replace(":", "");
  if (host) return `${proto}://${host}`.replace(/\/$/, "");
  return req.nextUrl.origin;
}

function buildCsp(nonce: string): string {
  const supabase = process.env.NEXT_PUBLIC_SUPABASE_URL?.replace(/\/$/, "") ?? "";
  // اتصال المتصفح بـ Supabase (مصادقة + PostgREST عبر wss) يحتاج المضيف
  // في connect-src. لا نضيف أي مضيف لم يُضبط في البيئة.
  const connect = ["'self'", supabase, supabase.replace(/^https:/, "wss:")].filter(Boolean);

  return [
    "default-src 'self'",
    // nonce + strict-dynamic: السكربت الموثّق وحده يعمل ويُحمّل ما يثق به.
    // لا unsafe-inline، لا unsafe-eval. سكربت المطوّر يجيب تقرير انتهاك.
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    // Next يضيف أنماطاً مضمّنة عند التصيير؛ style-src يبقى بالـ inline لأن
    // إزالته تكسر التصيير بلا مكسب أمني حقيقي (CSS ليس تنفيذاً).
    "style-src 'self' 'unsafe-inline'",
    "font-src 'self' data:",
    "img-src 'self' data: blob:",
    `connect-src ${connect.join(" ")}`,
    "worker-src 'self' blob:",
    "frame-ancestors 'none'",
    "frame-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
    "manifest-src 'self'",
    "upgrade-insecure-requests",
  ].join("; ");
}

export function proxy(req: NextRequest): NextResponse {
  const { pathname, search } = req.nextUrl;

  // (1) HTTPS إجباري — قبل أي عمل آخر، وبلا استثناء في الإنتاج.
  const proto = req.headers.get("x-forwarded-proto");
  const isHttps = req.nextUrl.protocol === "https:" || proto === "https";
  if (!isHttps && process.env.NODE_ENV === "production") {
    const url = new URL(req.url);
    url.protocol = "https:";
    url.host = req.headers.get("x-forwarded-host") ?? req.headers.get("host") ?? url.host;
    return NextResponse.redirect(url, 308);
  }

  const nonce = crypto.randomUUID().replace(/-/g, "");
  const csp = buildCsp(nonce);

  // (2) الـ nonce يُمرَّر للسكربتات عبر ترويسة الطلب؛ Next يقرأها ويزرعها.
  const requestHeaders = new Headers(req.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("content-security-policy", csp);

  const res = NextResponse.next({ request: { headers: requestHeaders } });

  res.headers.set("Content-Security-Policy", csp);
  res.headers.set("x-security-nonce", nonce);

  // أصول ثابتة: تخزين طويل آمن لأن أسماءها تحتوي بصمة.
  if (isStaticAsset(pathname)) {
    res.headers.set("cache-control", "public, max-age=31536000, immutable");
  } else {
    res.headers.set("cache-control", "no-store, must-revalidate");
  }

  // الطلبات المتقاطعة لا تأخذ بيانات اعتماد من نطاق آخر.
  res.headers.set("Cross-Origin-Resource-Policy", "same-origin");

  // حماية إضافية للمسارات الخلفية: لا Referer إلى أي مصدر خارجي.
  if (pathname.startsWith("/api/")) {
    res.headers.set("Referrer-Policy", "no-referrer");
    res.headers.set("X-Robots-Tag", "noindex, nofollow");
  }

  // احتياطي: لو عُدِّل الأصل عبر rewrite، يبقى الأصل الحقيقي متاحاً للأصل.
  res.headers.set("X-Origin-For", requestOrigin(req));

  void search;
  return res;
}

/**
 * نطاق التطبيق: كل شيء عدا الأصول الثابتة. `_next/static` تُخدم بلا
 * حافة لأنها لا تحتاج nonce ولا سياسة سكربت.
 */
export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
