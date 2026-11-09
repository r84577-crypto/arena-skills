"use client";

/**
 * المراسلة الصادرة — إيميل وواتساب من اللوحة.
 *
 * التدفق مقصود بعناية:
 *   1. تُسجَّل الرسالة في public.comms_log أولاً (RLS: المالك فقط،
 *      وقيد CHECK يرفض أي رقم واتساب غير رقم المالك).
 *   2. يُستدعى مسار التسليم الخلفي، فيتحقق من الجلسة والنطاق ثم يرسل.
 *   3. يُحدَّث الصف بالنتيجة (sent / failed / blocked / not_configured).
 *
 * بلا جلسة: قفل. بلا مفاتيح مزوّد: not_configured بصدق، لا تظاهر.
 */

import { useCallback, useEffect, useState } from "react";
import { supabaseBrowser, hasSession, getAccessToken } from "@/lib/supabase";

type Channel = "email" | "whatsapp";
type Scope = "PERSONAL" | "TRAINING";

type LogRow = {
  id: number;
  created_at: string;
  channel: Channel;
  scope: string;
  to_addr: string;
  status: string;
};

type Result =
  | { k: "idle" }
  | { k: "busy"; step: string }
  | { k: "done"; tone: "ok" | "warn" | "bad"; text: string };

const WHATSAPP_DISPLAY = "0508247153";

const STATUS_AR: Record<string, string> = {
  queued: "بالانتظار",
  sent: "أُرسلت",
  blocked: "مرفوضة",
  failed: "فشلت",
  not_configured: "بانتظار التهيئة",
};

function scopeLabel(s: string): string {
  return s === "TRAINING" ? "تدريب" : "شخصي";
}

export default function CommsPanel() {
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [channel, setChannel] = useState<Channel>("email");
  const [to, setTo] = useState("");
  const [subject, setSubject] = useState("");
  const [scope, setScope] = useState<Scope>("TRAINING");
  const [body, setBody] = useState("");
  const [result, setResult] = useState<Result>({ k: "idle" });
  const [log, setLog] = useState<LogRow[]>([]);

  const refreshLog = useCallback(async () => {
    const sb = supabaseBrowser();
    if (!sb) return;
    const { data } = await sb
      .from("comms_log")
      .select("id,created_at,channel,scope,to_addr,status")
      .order("id", { ascending: false })
      .limit(5);
    if (data) setLog(data as LogRow[]);
  }, []);

  useEffect(() => {
    void hasSession().then((ok) => {
      setAuthed(ok);
      if (ok) void refreshLog();
    });
  }, [refreshLog]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const sb = supabaseBrowser();
    if (!sb) return;

    setResult({ k: "busy", step: "يُسجَّل في الدفتر…" });
    const toAddr = channel === "whatsapp" ? "966508247153" : to.trim();

    // 1) التسجيل أولاً — RLS والقيد يرفضان أي تجاوز هنا.
    const { data: row, error: insertError } = await sb
      .from("comms_log")
      .insert({
        actor: (await sb.auth.getUser()).data.user?.id,
        channel,
        scope,
        to_addr: toAddr,
        subject: channel === "email" ? subject.trim() || null : null,
        body: body.trim(),
      })
      .select("id")
      .single();

    if (insertError || !row) {
      setResult({
        k: "done",
        tone: "bad",
        text: `رُفض التسجيل: ${insertError?.message ?? "خطأ غير معروف"}`,
      });
      return;
    }

    // 2) التسليم عبر المسار الخلفي.
    setResult({ k: "busy", step: "يُرسَل عبر المزوّد…" });
    const token = await getAccessToken();
    let outcome: { status: string; reason?: string; provider_ref?: string };
    try {
      const res = await fetch(`/api/send-${channel}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          id: row.id,
          to: toAddr,
          subject: subject.trim(),
          body: body.trim(),
          scope,
        }),
      });
      outcome = (await res.json()) as typeof outcome;
    } catch (err) {
      outcome = { status: "failed", reason: err instanceof Error ? err.message : "تعذّر الوصول للمسار" };
    }

    // 3) تحديث الصف بالنتيجة.
    await sb
      .from("comms_log")
      .update({
        status: outcome.status,
        reason: outcome.reason ?? null,
        provider_ref: outcome.provider_ref ?? null,
        sent_at: outcome.status === "sent" ? new Date().toISOString() : null,
      })
      .eq("id", row.id);

    const tone = outcome.status === "sent" ? "ok" : outcome.status === "not_configured" ? "warn" : "bad";
    const text =
      outcome.status === "sent"
        ? `أُرسلت وسُجّلت (#${row.id}).`
        : outcome.status === "not_configured"
          ? `سُجّلت (#${row.id}) بانتظار تهيئة المزوّد — لم يُرسَل شيء.`
          : `سُجّلت (#${row.id}) وفشل التسليم: ${outcome.reason ?? outcome.status}`;
    setResult({ k: "done", tone, text });
    setBody("");
    if (channel === "email") {
      setTo("");
      setSubject("");
    }
    void refreshLog();
  }

  if (authed === null) {
    return (
      <div className="glass login-wrap enter" style={{ maxWidth: 560 }} aria-busy="true">
        <div className="skeleton" style={{ height: 20, width: "40%" }} />
        <div className="skeleton" style={{ height: 44, marginTop: 14 }} />
      </div>
    );
  }

  if (!authed) {
    return (
      <div className="glass login-wrap enter" style={{ maxWidth: 560 }}>
        <h2>المراسلة مقفلة</h2>
        <p className="sub">سجّل الدخول أولاً — الإرسال للمالك وحده، والتسجيل يثبت الفاعل.</p>
      </div>
    );
  }

  return (
    <div className="glass login-wrap enter" style={{ maxWidth: 560 }}>
      <h2>رسالة جديدة</h2>
      <p className="sub">تُسجَّل قبل إرسالها، وتُذيَّل بإسناد نطاقها تلقائياً.</p>

      <div className="tabs" role="tablist" aria-label="القناة">
        <button
          role="tab"
          aria-selected={channel === "email"}
          className="tab"
          onClick={() => setChannel("email")}
          type="button"
        >
          بريد إلكتروني
        </button>
        <button
          role="tab"
          aria-selected={channel === "whatsapp"}
          className="tab"
          onClick={() => setChannel("whatsapp")}
          type="button"
        >
          واتساب
        </button>
      </div>

      <form onSubmit={submit}>
        {channel === "email" ? (
          <>
            <label className="field">
              إلى
              <input
                type="email"
                required
                dir="ltr"
                value={to}
                onChange={(e) => setTo(e.target.value)}
                placeholder="name@example.com"
              />
            </label>
            <label className="field">
              الموضوع
              <input
                type="text"
                required
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                maxLength={200}
              />
            </label>
          </>
        ) : (
          <label className="field">
            إلى (مقفلة على رقم المالك — يرفض القيد أي رقم آخر)
            <input type="text" readOnly dir="ltr" value={WHATSAPP_DISPLAY} />
          </label>
        )}

        <label className="field">
          النطاق
          <select value={scope} onChange={(e) => setScope(e.target.value as Scope)}>
            <option value="TRAINING">تدريب — إسناد «مدرب الحاسب»</option>
            <option value="PERSONAL">شخصي — إسناد «مدير الحاسب»</option>
          </select>
        </label>

        <label className="field">
          النص
          <textarea
            required
            value={body}
            onChange={(e) => setBody(e.target.value)}
            maxLength={4000}
            placeholder={channel === "whatsapp" ? "نص رسالة الواتساب…" : "نص الرسالة…"}
          />
        </label>

        <button type="submit" className="btn" style={{ width: "100%" }} disabled={result.k === "busy"}>
          {result.k === "busy" ? result.step : channel === "email" ? "سجّل وأرسل" : "سجّل وأرسل واتساب"}
        </button>
      </form>

      {result.k === "done" && (
        <div className={`result-banner ${result.tone}`} role="status">
          {result.text}
        </div>
      )}

      {log.length > 0 && (
        <>
          <h2 style={{ marginTop: 22, fontSize: 15 }}>أحدث الرسائل</h2>
          <ul className="log-list">
            {log.map((r) => (
              <li key={r.id}>
                <span className={`pill ${r.status === "sent" ? "ok" : r.status === "not_configured" || r.status === "queued" ? "warn" : "bad"}`}>
                  {STATUS_AR[r.status] ?? r.status}
                </span>
                <span>{r.channel === "email" ? "بريد" : "واتساب"}</span>
                <span style={{ color: "var(--ink-dim)" }}>
                  {scopeLabel(r.scope)} · {r.channel === "email" ? r.to_addr : WHATSAPP_DISPLAY}
                </span>
                <time>
                  {new Intl.DateTimeFormat("ar-SA", {
                    day: "numeric",
                    month: "short",
                    hour: "2-digit",
                    minute: "2-digit",
                    timeZone: "Asia/Riyadh",
                    numberingSystem: "latn",
                  }).format(new Date(r.created_at))}
                </time>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
