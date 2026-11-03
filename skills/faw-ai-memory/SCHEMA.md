# The `faw_ai` schema

Applied to Supabase project `faw-marketing` (ref `tbvtzuspjcxsidpqknid`, Postgres 17) on
2026-11-03. The re-runnable migration lives at
`db/migrations/20261103090000_faw_ai_memory_phase1.sql` in this repository. It is referred
to by path rather than linked on purpose: skills are loaded as standalone directories, so a
link that points outside the skill would break as soon as the skill is copied somewhere
useful.

## Where it sits

```text
faw-marketing
  public/        existing institute system — api_* RPCs, visits, organizations, tasks, reports
  faw_private/   existing snapshots and cron helpers
  faw_ai/        NEW — the principal's personal memory (this skill)
  auth, storage, cron, vault, realtime   unchanged
```

`faw_ai` is not linked to the operational tables except by one optional foreign key:
`institute_milestones.org_id → public.organizations(id)`. That direction is deliberate —
the operational system must never depend on the memory layer, so the memory layer can be
dropped without a migration on the institute's side.

## Tables

| Table | Holds | Dedupe key |
| --- | --- | --- |
| `profile_facts` | One keyed fact with `source`, `confidence`, `sensitivity` | `(owner_id, category, key)` |
| `memory_documents` | Text chunks + `vector(1536)` embedding + trigram index | `(owner_id, content_hash)` |
| `health_logs` | Vitals, medication, CPAP, workouts, sleep, labs | none — an event log |
| `finance_entries` | Personal ledger, SAR by default | none — an event log |
| `institute_milestones` | Dated achievements, optionally tied to an org | none |
| `agent_runs` | What an agent did, when, and whether it worked | none |
| `profile_intake` | A staged profile awaiting the subject's approval | one `pending` per subject |

Every table has `owner_id` and RLS enabled, with exactly one policy:

```sql
for all to authenticated
using (owner_id = auth.uid()) with check (owner_id = auth.uid())
```

That means **one staff account cannot read another's twin data, and a supervisor cannot
read downward either** — unlike the operational tables, where `can_view_all()` deliberately
grants supervisors institute-wide visibility. If a future requirement needs sharing, add a
narrow policy for a specific role; never widen this one.

`profile_intake` is the exception to the table-per-owner pattern: its policy is
`subject_user_id = auth.uid()`, and `subject_user_id` is whose twin the payload describes.
The system owner — `role = 'owner'` in `public.profiles` — is an administrator of the
institute's data and has **no** read access to this table. See
[DATA-GOVERNANCE.md](DATA-GOVERNANCE.md) for why that was corrected after first shipping.

`anon` has no `USAGE` on the schema. `authenticated` gets DML on tables and `EXECUTE` on
the four RPCs below. `service_role` keeps full access and bypasses RLS — which is why a
server-side writer is the most dangerous caller: it can set any `owner_id`.

### `profile_facts` columns that carry meaning

- `source` — `manual`, `voice`, `gmail`, `calendar`, `drive`, `linear`, `notion`, `import`,
  `system`. An automated pass should only overwrite rows whose `source` is its own, or
  whose `confidence` is lower than the new value's.
- `confidence` — `0.00`–`1.00`. Hand-entered facts default to `1.00`.
- `sensitivity` — `public` / `personal` / `sensitive` / `secret`. `secret` rows must never
  be copied into a prompt, a document, or another connector.
- `verified_at` / `expires_at` — a fact with no evidence and no expiry is a rumour.

### `memory_documents` and the embedding

- `embedding` is `extensions.vector(1536)`, for `text-embedding-3-small`. The dimension is
  part of the column type, so changing models needs a new column and a re-embed, planned as
  a migration — not an `alter type`.
- `embedding` starts `NULL`. Keyword search works immediately; semantic search returns
  nothing until something embeds the rows. That is honest, and `api_ai_snapshot()` reports
  `memory_embedded` so the gap is visible.
- `content_hash` is `md5(content)`. `api_memory_add()` computes it; a direct insert must
  supply it. Re-ingesting identical text updates metadata instead of duplicating the row.
- HNSW index with `m = 16, ef_construction = 64` on cosine distance. Fine to a few hundred
  thousand rows; below ~1,000 rows the planner may prefer a sequential scan, which is
  correct, not broken.

## RPCs

| Function | Returns | Notes |
| --- | --- | --- |
| `api_memory_add(kind, content, title?, metadata?, table?, id?)` | `uuid` | owner from `auth.uid()`, hash computed server-side |
| `api_memory_search(query, limit?)` | rows + `score` | trigram similarity, works with no embeddings |
| `api_memory_match(embedding_json, limit?, min_sim?)` | rows + `score` | raises a readable error if the vector is not 1536-D |
| `api_ai_snapshot()` | `jsonb` | counts for the owner + attribution footer |
| `api_profile_seed(subject?)` | `jsonb` | subject-only; materialises an approved intake, reports `facts_written` and `secret_tier` |
| `api_profile_brief()` | `jsonb` | staff-safe: no phone, no birth date, no health, no money |
| `api_attribution_footer()` | `text` | the one credit-line source of truth |

All are `security invoker`, so RLS applies to the caller. All are revoked from `public` and
`anon` and granted to `authenticated` and `service_role` only.

## Rules for extending it

1. **Additive only.** `create ... if not exists` and `create or replace`. No `drop table`,
   no `alter column ... type`, no rename of anything already granted.
2. **Every new table carries `owner_id` and an owner policy.** A table in `faw_ai` without
   RLS is a leak, and nothing in the repository catches it for you — add the policy in the
   same migration that creates the table.
3. **New functions start closed.** `revoke all ... from public, anon` then grant explicitly.
   The schema already sets default privileges to revoke `EXECUTE`, but do not rely on it
   for functions created in `public`.
4. **Timestamps that users read are `timestamptz`.** The operational tables store ISO text
   (`((now() at time zone 'utc'))::text`); do not copy that pattern into new tables — it
   is the single biggest obstacle to date arithmetic in the existing system.
5. **Keep the memory layer out of `public`.** Only the `api_*` wrappers live there, because
   PostgREST exposes that schema.

## The operational system, for orientation

Not owned by this skill, but an agent will see it and should not touch it:

- 20 tables in `public`, all with RLS enabled; roles `owner`, `admin`, `viewer`, `employee`
  resolved by `public.my_role()` from `profiles`, gated on `status = 'active'` and
  `must_change_pw = false`.
- ~45 `api_*` RPCs, one per screen or action (`api_visits`, `api_plan_save`, …).
- `pg_cron` installed, three jobs, with `faw_private.periodic_daily()` and
  `faw_private.snapshot_operational()` in support.
- `marketing_datasets` and `sync_operations` have RLS enabled and **no policy**, so they
  are service-role-only today. That is a finding, not a bug to fix silently: changing it
  changes who can see imported marketing data.
