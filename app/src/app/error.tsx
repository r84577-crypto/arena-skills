"use client";

/**
 * حدّ الخطأ العام — أي عطل في أي مسار ينتهي هنا لا في شاشة بيضاء.
 * زر إعادة المحاولة يعيد التصيير، وزر التحديث يعيد التحميل الكامل.
 */
export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main>
      <div className="glass login-wrap enter" style={{ maxWidth: 560, textAlign: "center" }}>
        <h2>تعثّر التحميل</h2>
        <p className="sub">
          حدث خطأ غير متوقع — بياناتك محفوظة، والمشكلة في العرض فقط.
          {error.digest ? ` (مرجع: ${error.digest})` : ""}
        </p>
        <div style={{ display: "flex", gap: 10, justifyContent: "center", marginTop: 16 }}>
          <button type="button" className="btn" onClick={() => reset()}>
            إعادة المحاولة
          </button>
          <button
            type="button"
            className="btn"
            onClick={() => window.location.reload()}
          >
            تحديث الصفحة
          </button>
        </div>
      </div>
    </main>
  );
}
