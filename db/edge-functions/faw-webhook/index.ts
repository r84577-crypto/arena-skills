// Supabase Edge Function: faw-webhook
//
// One door for every external caller: Telegram bot updates, WhatsApp Business
// callbacks, Zapier/Make, or a plain REST client. It authenticates the caller,
// then hands the payload to faw_ai.webhook_ingest(), which owns the token check,
// the per-minute ceiling, the size ceiling, and idempotency.
//
// Deploy (from db/, where the Supabase CLI config lives):
//   supabase functions deploy faw-webhook --no-verify-jwt
// The platform JWT check is off because callers are third-party services that do
// not hold a Supabase key. Authentication happens below, per source, on a token
// that is compared against a SHA-256 hash in the database.
//
// Required secrets (set with `supabase secrets set`, never committed):
//   FAW_WEBHOOK_TOKEN_<SOURCE_ID>   e.g. FAW_WEBHOOK_TOKEN_TELEGRAM
//
// The function is deliberately dumb. Every rule that can be enforced atomically
// — comparing the token, counting this minute's events, deduplicating a retry —
// lives in the database function, because two concurrent deliveries cannot be
// serialised from the edge.

import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

// Hard ceilings applied before the payload is even parsed. The database applies
// the per-source limit as well; this one exists so an enormous body is rejected
// without spending CPU on it.
const MAX_BODY_BYTES = 1_048_576;
const SOURCE_RE = /^[a-z0-9][a-z0-9_-]{1,40}$/;

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

Deno.serve(async (req: Request): Promise<Response> => {
  if (req.method !== "POST") {
    return json({ ok: false, status: "method_not_allowed" }, 405);
  }

  const url = new URL(req.url);
  const source = (url.searchParams.get("source") ?? "").toLowerCase();
  if (!SOURCE_RE.test(source)) {
    return json({ ok: false, status: "bad_source" }, 400);
  }

  const token = req.headers.get("x-faw-token") ?? "";
  if (token.length < 24) {
    return json({ ok: false, status: "missing_token" }, 401);
  }

  // A second, cheap gate: the source must be one this deployment expects. It does
  // not replace the database check — it keeps unknown sources from reaching it.
  const expected = Deno.env.get(`FAW_WEBHOOK_TOKEN_${source.toUpperCase()}`);
  if (expected && expected !== token) {
    return json({ ok: false, status: "bad_token" }, 401);
  }
  if (!expected) {
    return json({ ok: false, status: "source_not_configured" }, 403);
  }

  const raw = await req.text();
  if (new TextEncoder().encode(raw).length > MAX_BODY_BYTES) {
    return json({ ok: false, status: "too_large" }, 413);
  }

  let payload: unknown;
  try {
    payload = JSON.parse(raw);
  } catch {
    return json({ ok: false, status: "bad_json" }, 400);
  }

  // Telegram puts the update id in `update_id`; WhatsApp Cloud API uses the first
  // message id; everything else should send `external_id` or an Idempotency-Key.
  const externalId =
    (payload as Record<string, unknown>)?.external_id?.toString() ??
    (payload as Record<string, unknown>)?.update_id?.toString() ??
    req.headers.get("idempotency-key") ??
    null;

  const admin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
    auth: { persistSession: false },
  });

  const { data, error } = await admin.schema("faw_ai").rpc("webhook_ingest", {
    p_source: source,
    p_token: token,
    p_payload: payload,
    p_external_id: externalId,
  });

  if (error) {
    console.error("webhook_ingest failed", { source, error: error.message });
    return json({ ok: false, status: "ingest_error" }, 500);
  }

  // Map the database verdict onto an HTTP status so the sender knows whether to
  // retry. `duplicate` is a 200: a retry that was already stored is not an error.
  const verdict = (data as { status?: string })?.status ?? "unknown";
  const status =
    verdict === "accepted" || verdict === "duplicate" ? 202
    : verdict === "throttled" ? 429
    : verdict === "too_large" ? 413
    : verdict === "unknown_source" || verdict === "bad_token" ? 401
    : 400;

  return json(data, status);
});
