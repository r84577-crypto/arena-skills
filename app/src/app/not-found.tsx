import Link from "next/link";

/**
 * صفحة 404 مؤسسية — عربية، بهوية النظام، وتعيد الزائر للوحة.
 */
export default function NotFound() {
  return (
    <main>
      <div className="glass login-wrap enter" style={{ maxWidth: 560, textAlign: "center" }}>
        <p className="badge gold" style={{ display: "inline-block" }}>404</p>
        <h2>الصفحة غير موجودة</h2>
        <p className="sub">الرابط الذي اتبعته لا يشير إلى شيء في النظام السيادي.</p>
        <div style={{ marginTop: 16 }}>
          <Link href="/" className="btn">
            عودة إلى اللوحة
          </Link>
        </div>
      </div>
    </main>
  );
}
