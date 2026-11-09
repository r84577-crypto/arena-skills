import nodemailer from "nodemailer";

/**
 * إرسال البريد — طبقة المزوّدين (خادم فقط، لا تُستورَد في المتصفح أبداً).
 *
 * مزوّدان مجانيان، بالترتيب:
 *   1. Resend — إن وُجد RESEND_API_KEY (3000 رسالة/شهر مجاناً).
 *   2. Gmail SMTP — إن وُجد GMAIL_USER + GMAIL_APP_PASSWORD (كلمة مرور
 *      التطبيقات من حساب Google، مجانية، بحدود Gmail اليومية المعتادة).
 * بلا أي منهما: not_configured بصدق.
 *
 * ملاحظة الاختبار: `selectProvider` دالة صرفة تُختبَر مباشرة بـ node دون
 * شبكة. دالتا الإرسال تُرجعان SendResult ولا ترميان أبداً — أي عطل شبكة
 * أو رفض مزوّد يتحول إلى سبب عربي يُسجَّل في الدفتر.
 */

export type EmailProvider = "resend" | "gmail" | null;

export type SendResult =
  | { ok: true; providerRef: string | null }
  | { ok: false; reason: string };

export function selectProvider(env: {
  RESEND_API_KEY?: string;
  GMAIL_USER?: string;
  GMAIL_APP_PASSWORD?: string;
}): EmailProvider {
  if (env.RESEND_API_KEY) return "resend";
  if (env.GMAIL_USER && env.GMAIL_APP_PASSWORD) return "gmail";
  return null;
}

export function scopeFooter(scope: "TRAINING" | "PERSONAL"): string {
  return scope === "TRAINING"
    ? "تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدرب الحاسب"
    : "تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدير الحاسب";
}

export function scopeTag(scope: "TRAINING" | "PERSONAL"): string {
  return scope === "TRAINING" ? "تدريب" : "شخصي";
}

export async function sendViaResend(args: {
  apiKey: string;
  from: string;
  to: string;
  subject: string;
  text: string;
}): Promise<SendResult> {
  try {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${args.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: args.from,
        to: [args.to],
        subject: args.subject,
        text: args.text,
      }),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      return { ok: false, reason: `المزوّد رفض (${res.status}): ${detail.slice(0, 200)}` };
    }
    const sent = (await res.json()) as { id?: string };
    return { ok: true, providerRef: sent.id ?? null };
  } catch (e) {
    return { ok: false, reason: e instanceof Error ? e.message : "خطأ شبكة" };
  }
}

export async function sendViaGmail(args: {
  user: string;
  appPassword: string;
  to: string;
  subject: string;
  text: string;
}): Promise<SendResult> {
  try {
    const transporter = nodemailer.createTransport({
      host: "smtp.gmail.com",
      port: 465,
      secure: true,
      auth: { user: args.user, pass: args.appPassword },
      connectionTimeout: 10000,
      greetingTimeout: 8000,
      socketTimeout: 20000,
    });
    const info = await transporter.sendMail({
      from: args.user,
      to: args.to,
      subject: args.subject,
      text: args.text,
    });
    return { ok: true, providerRef: info.messageId ?? null };
  } catch (e) {
    return { ok: false, reason: e instanceof Error ? e.message : "خطأ شبكة" };
  }
}
