import SceneShell from "@/components/SceneShell";
import StatusBoard from "@/components/StatusBoard";
import Connectors from "@/components/Connectors";
import CommsPanel from "@/components/CommsPanel";
import { ATTRIBUTION } from "@/lib/supabase";

/**
 * لوحة السيادة — الصفحة الرئيسية (مكوّن خادم).
 *
 * المؤشرات تُجلب من المتصفح (StatusBoard) لأن بيئة البناء بلا شبكة صادرة.
 * الحالة «غير متصل» ليست عيباً مخفياً — تُعرض بصدق مع زر إعادة المحاولة.
 */

const SCOPES = [
  {
    key: "personal",
    title: "المجال الشخصي السيادي",
    body: "الصحة والمال والذاكرة — للمالك وحده، بلا قارئ ثانٍ. كل جدول بعزل صفوف، والموجّه يسجّل كل قرار دخول.",
    foot: "اللقب: مدير الحاسب",
  },
  {
    key: "training",
    title: "وحدة تدريب الحاسب",
    body: "الدورات والمتدربون والامتحانات والزيارات — للمصرّحين في قائمة المدرّبين فقط، بمخطط منفصل تماماً.",
    foot: "اللقب: مدرب الحاسب",
  },
  {
    key: "aon",
    title: "تطبيقات عون المستقلة",
    body: "آلة لآلة فقط — الوصول البشري ممنوع بالتصميم، ولا مفتاح إلا عبر service_role.",
    foot: "بلا إسناد بشري",
  },
] as const;

export default function Page() {
  return (
    <main>
      <header className="hero enter">
        <h1>
          النظام <span className="glow">السيادي</span>
        </h1>
        <p>
          التوأم الرقمي لعادل عبدالله الحربي — ذاكرة دائمة، روتين صحي، ووحدة
          تدريب حاسب، تحت ثلاثة نطاقات معزولة لا يعبر بينها شيء.
        </p>
        <div className="badges">
          <span className="badge">
            <span className="dot" aria-hidden="true" />
            حيّ — بريدة، القصيم
          </span>
          <span className="badge">شخصي · مالك فقط</span>
          <span className="badge gold">تدريب · مصرّحون فقط</span>
          <span className="badge">عون · آلات فقط</span>
        </div>
      </header>

      <SceneShell />

      <div className="section-head enter d1">
        <h2>المؤشرات الحيّة</h2>
        <p>تُقرأ بجلسة المالك من دالة واحدة — بلا جلسة لا أرقام.</p>
      </div>
      <StatusBoard />

      <div className="section-head enter d2">
        <h2>النطاقات الثلاثة</h2>
        <p>عزل مفروض بالسياسات، لا موثّق بالكلام.</p>
      </div>
      <section className="grid" aria-label="النطاقات">
        {SCOPES.map((s, i) => (
          <article className={`card scope-${s.key} enter d${i + 1}`} key={s.key}>
            <h2>{s.title}</h2>
            <div className="note" style={{ fontSize: 13.5 }}>
              {s.body}
            </div>
            <div className="note" style={{ marginTop: 10 }}>
              {s.foot}
            </div>
          </article>
        ))}
      </section>

      <div className="section-head enter d3">
        <h2>شبكة الموصّلات</h2>
        <p>كل سطر مقيس — القراءة ليست كتابة، والمقروء يُقال مقروء.</p>
      </div>
      <Connectors />

      <div className="section-head enter d4">
        <h2>المراسلة الصادرة</h2>
        <p>كل رسالة تُسجَّل قبل إرسالها — والواتساب لرقم واحد لا غير.</p>
      </div>
      <CommsPanel />

      <footer className="credit">{ATTRIBUTION}</footer>
    </main>
  );
}
