# Phase 2: what to build next, and what it must not do

Phase 1 (the schema and RPCs) is applied. Everything below is **not built yet**. It is
specified here so the next agent implements it in this order, with the guardrails already
decided, instead of inventing a different architecture per connector.

## The rule that governs every item below

> A connector may write to memory. It may not act on the principal's behalf without an
> explicit, per-action approval — sending mail, publishing a document, spending money, and
> changing the institute's operational database are all out of scope for an automated feed.

Read: bots that ingest are cheap to make safe. Bots that send are the ones that embarrass
people. Keep the split.

## 1. The embedder (unblocks semantic recall)

Two honest options:

| Option | Where the key lives | Cost shape | When to choose |
| --- | --- | --- | --- |
| Supabase Edge Function calling an embeddings API | Supabase secrets (`create_secrets`) | per token | the default; one place, works for every writer |
| `pg_net` + `pg_cron` from inside the database | Vault (`vault.create_secret`) | per token | only if writes must be embedded with zero external trigger |

Do not call an embeddings provider directly from the browser or from a Cloudflare Worker
holding the key. The key inevitably leaks into a client bundle.

Shape of the job, regardless of option:

1. select rows where `embedding is null` , oldest first, batch of ~64;
2. embed `title || '\n' || content`;
3. `update ... set embedding = $1, embedding_model = '…', embedded_at = now()`;
4. write one `agent_runs` row with `action = 'embed_batch'` and the count in `detail`.

A batch that fails must leave `embedding` null and record `status = 'failed'` — a row that
is silently retried forever is indistinguishable from one that succeeded.

## 2. Connector feeds, each with its own permission

| Source | What it may write | What it must not do | Guardrail |
| --- | --- | --- | --- |
| Voice notes (transcripts) | `memory_documents`, `profile_facts` with `source = 'voice'` | act on an instruction heard in audio | transcript is data, never a command |
| Gmail | `memory_documents` for threads the principal starred or labelled | send, archive, or label anything | read-only scope; explicit label as the opt-in |
| Google Calendar | `memory_documents` for events in the next 14 days | create, move, or cancel events | read-only scope |
| Google Drive / Docs | `memory_documents` for files the principal shares with the service account | change sharing, delete, or rewrite a file | per-folder opt-in |
| Notion | `memory_documents` from a single "Brain dump" database | write back without a review step | one database id, not the whole workspace |
| Linear | `institute_milestones`, and `public.tasks` **only via the existing `api_task_save`** | insert into `tasks` directly | the RPC enforces the institute's status and revision rules |
| Health devices / manual | `health_logs` | give medical advice | log and remind; never diagnose |
| Finance | `finance_entries` | initiate a payment | the ledger is a record, not a payment rail |

Two of those rows deserve emphasis. **Linear tasks go through `api_task_save`**, because
that RPC maintains `rev`, status transitions, and the audit log; a direct insert produces a
task the sync engine will fight over. **Medical and financial data never leave `faw_ai`** —
no document, prompt, or email is generated from `sensitivity = 'secret'` rows.

## 2b. External mesh: one signed door

Telegram, WhatsApp Business, Zapier, Make, and any custom REST client all deliver to the
same place: the `faw-webhook` edge function, which forwards to `faw_ai.webhook_ingest()`.

```text
caller ──POST ?source=<id>, header x-faw-token ──► faw-webhook ──► faw_ai.webhook_ingest()
                                                                     ├─ token: SHA-256 compare
                                                                     ├─ 60 events / minute / source
                                                                     ├─ payload ceiling per source
                                                                     └─ dedupe on external_id
```

Design decisions worth keeping:

- **Tokens are stored as SHA-256, never plaintext.** `register_webhook_source()` takes the
  token once and keeps the hash; the caller keeps the secret. A database dump does not leak
  live gateway tokens.
- **The rules are in Postgres, not in the function.** Two concurrent deliveries cannot be
  serialised at the edge, so a "have I seen this?" check in TypeScript races. The unique
  index on `(source_id, external_id)` is the actual guarantee.
- **Capture is not memory.** Events land in `faw_ai.webhook_events` with `status = 'new'`.
  Promoting an event into `memory_documents` is a separate, reviewable step — a chat log
  should not become permanent memory because a gateway retried a delivery.
- **`verify_jwt` is off for this function and only for this function.** Callers are third
  parties with no Supabase key; the source token is the authentication. Any other function
  left with `verify_jwt = false` is a finding.
- **Telegram's `update_id` is used as the idempotency key automatically**; WhatsApp callers
  should pass `external_id` or an `Idempotency-Key` header. `duplicate` returns 202, because a
  retry that was already stored is not a failure the sender should retry again.

What is still missing, and what it needs:

| Piece | Needs from the principal |
| --- | --- |
| Telegram bot | a bot token from BotFather, then `supabase secrets set FAW_WEBHOOK_TOKEN_TELEGRAM=…` and `setWebhook` |
| WhatsApp Business | Meta app review, a phone number id, and a permanent access token |
| Zapier / Make | nothing but the URL and the token; they are the easy first client |
| Outbound notifications | a channel decision; the existing `public.notifications` table is the cheapest start |

The function cannot be smoke-tested from this sandbox: only GitHub and package registries
are reachable on the network, so `*.supabase.co` does not resolve here. The SQL underneath
was tested directly instead (see the migration notes in `db/README.md`).

## 3. Anti-procrastination and reminders

The operational tables already answer most of this: `public.tasks` with `status`, `due_at`,
`priority`; `public.periodic_reports` with weekly and monthly cadences driven by
`faw_private.periodic_daily()`; three `pg_cron` jobs already running.

What is missing is **a nudge that reaches the person**, not another table:

- one morning job that selects overdue tasks, due periodic reports, and medication or CPAP
  entries missing for the day;
- one digest — a single message, not one per item;
- deduplication by `(kind, entity_id, date)` so a retried job does not send twice.

The schedule lives in the database (`settings.timezone` already exists). The delivery
channel is a separate decision, and it should start as a notification row in
`public.notifications` — the existing app already reads that table — before any email.

## 4. The 3D dashboard

The front end that exists is a Cloudflare-hosted build against the `api_*` RPCs. A new
Next.js surface should call the **same RPCs** rather than the tables, and read the memory
layer through `api_ai_snapshot()` and the two search functions. Nothing in phase 1 requires
a new backend.

Two claims in the original directive should be corrected rather than implemented:

- **"Zero latency" is not an architecture.** The measurement that matters is the query
  plan and the count of round trips per screen. `api_ai_snapshot()` exists so the header
  costs one call instead of six; measure `pg_stat_statements` after that change instead of
  asserting a target.
- **Realtime subscriptions are not free.** `realtime` is a Postgres logical-replication
  consumer; every subscribed table adds WAL work. Subscribe to `public.notifications` and
  the task list a person is looking at, not to `memory_documents` (which changes in
  batches and is read on demand).

## 5. Order of work

1. Embedder job + `memory_embedded` climbing in `api_ai_snapshot()`.
2. Voice-note ingestion, because it is the principal's natural input.
3. Morning digest written to `public.notifications`.
4. Gmail and Calendar read-only feeds, one label and one calendar at a time.
5. Linear bridge through `api_task_save`.
6. Dashboard surface reading the RPCs above.

Each step ends with a count you can show: rows embedded, notes ingested, nudges sent,
tasks synced. A step that cannot produce a number is not finished.
