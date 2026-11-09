"use client";

/**
 * لوحة المؤشرات — للمالك المسجّل وحده.
 *
 * زر دخول واحد. لا مفتاح إداري هنا — المفتاح العام وجلسة المالك فقط.
 * الجلب من المتصفح لا الخادم: التصيير على الخادم يحدث حيث لا شبكة
 * صادرة، فتعرض الصفحة «غير متصل» دائماً.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchStatus, type Status } from "@/lib/status";
import { hasSession, signInOwner, signOutOwner } from "@/lib/supabase";

type State =
  | { k: "loading" }
  | { k: "anon" }
  | { k: "ok"; data: Status }
  | { k: "error"; reason: string };

function arDate(iso: string): string {
  try {
    return new Intl.DateTimeFormat("ar-SA", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "Asia/Riyadh",
      numberingSystem: "latn",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

/** عدّاد يتصاعد من الصفر — يقفز للنهاية عند تقليل الحركة. */
function Counter({ value }: { value: number }) {
  const [shown, setShown] = useState(0);
  const raf = useRef(0);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(value);
      return;
    }
    const start = performance.now();
    const dur = 900;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      setShown(Math.round(value * eased));
      if (p < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [value]);

  return <>{shown.toLocaleString("en-US")}</>;
}

function LoginForm({ onDone }: { onDone: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    const r = await signInOwner(email.trim(), password);
    setBusy(false);
    if (r.ok) {
      setPassword("");
      onDone();
    } else {
      setErr(r.reason);
    }
  }

  return (
    <div className="glass login-wrap enter" role="form" aria-label="تسجيل الدخول">
      <h2>لوحة القيادة مقفلة</h2>
      <p className="sub">
        المؤشرات تُقرأ بجلسة المالك. المفتاح العام وحده لا يكفي — وهذا هو المقصود.
      </p>
      <form onSubmit={submit}>
        <label className="field">
          البريد
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="username"
            dir="ltr"
          />
        </label>
        <label className="field">
          كلمة المرور
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            dir="ltr"
          />
        </label>
        {err && (
          <div className="form-error" role="alert">
            {err}
          </div>
        )}
        <button type="submit" disabled={busy} className="btn" style={{ width: "100%" }}>
          {busy ? "جارٍ التحقق…" : "دخول"}
        </button>
      </form>
    </div>
  );
}

export default function StatusBoard() {
  const [state, setState] = useState<State>({ k: "loading" });

  const load = useCallback(async () => {
    setState({ k: "loading" });
    if (!(await hasSession())) {
      setState({ k: "anon" });
      return;
    }
    const r = await fetchStatus();
    setState(r.ok ? { k: "ok", data: r.data } : { k: "error", reason: r.reason });
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (state.k === "loading") {
    return (
      <section className="grid" aria-label="جارٍ التحميل" aria-busy="true">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <article className="card" key={i}>
            <div className="skeleton" style={{ height: 13, width: "55%" }} />
            <div className="skeleton" style={{ height: 34, width: "40%", marginTop: 10 }} />
          </article>
        ))}
      </section>
    );
  }

  if (state.k === "anon") {
    return <LoginForm onDone={() => void load()} />;
  }

  if (state.k === "error") {
    return (
      <section className="grid" aria-label="تعذّر الاتصال">
        <article className="card enter" style={{ gridColumn: "1 / -1" }}>
          <h2>تعذّرت قراءة الحالة</h2>
          <div className="note">{state.reason}</div>
          <button onClick={() => void load()} className="btn btn-ghost">
            إعادة المحاولة
          </button>
        </article>
      </section>
    );
  }

  const d = state.data;
  const verdict =
    d.security_verdict === "clean" ? (
      <span className="value ok">سليم</span>
    ) : d.security_verdict === "drift" ? (
      <span className="value bad">انحراف</span>
    ) : (
      <span className="value">—</span>
    );

  const stats: { label: string; body: React.ReactNode; note: string; delay: number }[] = [
    { label: "حقائق الملف", body: <Counter value={d.facts} />, note: "مسوّاة بمستويات حساسية", delay: 1 },
    { label: "وثائق الذاكرة", body: <Counter value={d.memory} />, note: `${d.memory_embedded} مضمّنة · ${d.memory - d.memory_embedded} معلّق`, delay: 1 },
    { label: "طبقة المعرفة", body: <Counter value={d.entities} />, note: `${d.edges} علاقة موثّقة`, delay: 2 },
    { label: "سجلات الصحة", body: <Counter value={d.health_logs} />, note: "دواء، CPAP، تمرين", delay: 2 },
    { label: "الروتينات النشطة", body: <Counter value={d.routines} />, note: "متزامنة مع التقويم", delay: 3 },
    { label: "محطات الحياة", body: <Counter value={d.milestones} />, note: "موثّقة بالأدلة", delay: 3 },
    {
      label: "دورات التزامن",
      body: <Counter value={d.sync_ok} />,
      note: d.sync_failed > 0 ? `${d.sync_failed} فاشلة — معروفة ومقصودة` : "بلا فشل",
      delay: 4,
    },
    { label: "النطاق التدريبي", body: <Counter value={d.training_courses} />, note: `${d.training_visits} زيارة ميدانية · مخطط منفصل`, delay: 4 },
    { label: "قرارات الموجّه", body: <Counter value={d.router_decisions} />, note: "كل طلب مسجَّل بفاعله وسببه", delay: 5 },
    { label: "قياسات التضمين", body: <Counter value={d.probes} />, note: "تجزئة رموز — ليست عصبية", delay: 5 },
    {
      label: "المراسلة الصادرة",
      body: <Counter value={d.comms_sent} />,
      note: `${d.comms_queued} بانتظار التهيئة — تُسجَّل قبل إرسالها`,
      delay: 6,
    },
    {
      label: "الفحص الأمني",
      body: verdict,
      note: d.security_verdict === "drift" ? "راجع security_audit" : "يُفحص ليلياً آلياً",
      delay: 6,
    },
  ];

  return (
    <>
      <div className="live-row">
        <p>حيّ · {arDate(d.generated_at)}</p>
        <button
          onClick={async () => {
            await signOutOwner();
            setState({ k: "anon" });
          }}
          className="btn btn-ghost"
        >
          خروج
        </button>
      </div>
      <section className="grid" aria-label="المؤشرات الحيّة">
        {stats.map((s) => (
          <article className={`card enter d${s.delay}`} key={s.label}>
            <h2>{s.label}</h2>
            <div className="value">{s.body}</div>
            <div className="note">{s.note}</div>
          </article>
        ))}
      </section>
    </>
  );
}
