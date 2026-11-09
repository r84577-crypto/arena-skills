/**
 * لوحة الموصّلات — تُقرأ من الواقع لا من التمني.
 *
 * آخر مراجعة: 2026-11-09. كل سطر هنا مقيس بأداة حقيقية.
 */

const CONNECTORS = [
  { name: "Supabase", state: "ok", text: "27 جدولاً · 3 مخططات · الفحص clean" },
  { name: "Google Calendar", state: "ok", text: "تقويم صحي معزول + رئيسي · بلا مشاركة عامة" },
  { name: "Gmail", state: "ok", text: "القراءة تعمل · الإرسال عبر البوابة الجديدة" },
  { name: "Notion", state: "ok", text: "قواعد التدريب · مشاركة عامة مغلقة" },
  { name: "Linear", state: "ok", text: "فريقان: SAM و CTR" },
  { name: "Google Drive", state: "ok", text: "قالب إسناد + لوحة حالة" },
  { name: "GitHub", state: "ok", text: "فرع نشط · فحص CI تلقائي" },
  { name: "Vercel", state: "warn", text: "مصادَق · الحساب محدود (limited)" },
  { name: "WhatsApp", state: "warn", text: "البوابة مبنية · بانتظار توكن Meta" },
] as const;

const LABEL: Record<string, string> = {
  ok: "متصل",
  bad: "محجوب",
  warn: "غير مهيّأ",
};

export default function Connectors() {
  return (
    <section className="grid" aria-label="حالة الموصّلات">
      {CONNECTORS.map((c, i) => (
        <article className={`card enter d${(i % 6) + 1}`} key={c.name}>
          <h2>{c.name}</h2>
          <span className={`pill ${c.state}`}>{LABEL[c.state]}</span>
          <div className="note">{c.text}</div>
        </article>
      ))}
    </section>
  );
}
