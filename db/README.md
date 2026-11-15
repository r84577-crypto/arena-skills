# Database changes for `faw-marketing`

This directory holds the SQL that has been applied to the Supabase project behind the
institute's platform, so that the change is reviewable, re-runnable, and reproducible on a
branch or a restored backup. It is plain SQL plus the Supabase CLI configuration — there is
no application code here.

It is kept **separate from the skills**: a skill is an instruction set an agent loads, and a
migration is a change to a live database. Mixing them meant a documentation pull request
could appear to be a production database change.

## Layout

```text
db/
  README.md
  supabase/
    config.toml            # minimal config for the Supabase CLI and repo linkage
  migrations/
    20261103090000_faw_ai_memory_phase1.sql
    20261104120000_faw_ai_profile_intake.sql
    20261104130000_faw_ai_profile_subject.sql
    20261104140000_faw_ai_profile_preview.sql
    20261104150000_faw_ai_webhook_intake.sql
    20261104160000_faw_private_morning_digest.sql
  edge-functions/
    faw-webhook/index.ts          # deployed as the faw-webhook function
```

Migration filenames follow the Supabase CLI convention `<UTC timestamp>_<name>.sql`, so the
CLI applies them in the same order they were written.

## The phase 1 migration

`20261103090000_faw_ai_memory_phase1.sql` adds the personal memory layer described by the
[`faw-ai-memory` skill](../skills/faw-ai-memory/SKILL.md):

- extensions `vector` and `pg_trgm`, both in the `extensions` schema;
- schema `faw_ai` with six tables, all owner-scoped by RLS;
- five `public.api_*` functions for recall, ingestion, telemetry, and the credit line;
- two additive rows in `public.settings`.

It touches **nothing** that already existed: no `drop`, no rename, no column type change,
no policy replacement on an operational table. It is written to be re-runnable.

## The profile migrations

`20261104120000_faw_ai_profile_intake.sql` adds the staging table, the field map, the seed
RPC, and the staff-safe brief. `20261104130000_faw_ai_profile_subject.sql` corrects the
first one: the twin belongs to `subject_user_id`, not to the account with
`role = 'owner'` — in this database that is the deputy director, so the first version let
the deputy read a health declaration the subject could neither see nor approve. Both are
reflected in the applied function bodies; the older file is kept as written rather than
rewritten, because it is already applied.

Two bugs were found by the verification run and fixed rather than documented as expected
behaviour:

- counting upserted rows inside the same statement reported `facts_written = 0`;
- aggregating the breakdown over `(category, sensitivity)` collapsed rows, so the category
  counts were too low. The `secret_tier` count was a side effect of that collapse and
  under-reported health data.

Both are the reason the seed RPC returns numbers at all: a silent zero looks like success.

### Verify before applying to a branch

```shell
supabase link --project-ref <ref>
supabase db diff --schema faw_ai        # should show the new schema only
supabase db push --dry-run              # lists pending migrations, applies nothing
```

### Verify after applying

```sql
select c.relname, c.relrowsecurity,
       (select count(*) from pg_policy p where p.polrelid = c.oid) as policies
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'faw_ai' and c.relkind = 'r' order by 1;
-- expect: 6 rows, relrowsecurity = true, policies = 1
```

Row counts on the operational tables should be identical before and after. The applied run
on 2026-11-03 was checked that way: 20 tables, all counts unchanged, `public.settings`
10 → 12 (the two new keys only).

## Rollback

Deliberately possible, and deliberately not a one-liner, because dropping a schema that
holds the principal's data should require a decision:

```sql
begin;
-- confirm nothing lives here that is not reproducible
select (select count(*) from faw_ai.memory_documents)     as docs,
       (select count(*) from faw_ai.profile_facts)        as facts,
       (select count(*) from faw_ai.health_logs)          as health,
       (select count(*) from faw_ai.finance_entries)      as finance,
       (select count(*) from faw_ai.institute_milestones) as milestones;
-- then, if the counts are acceptable to lose:
-- drop schema faw_ai cascade;
-- delete from public.settings where key in ('attribution_footer','ai_memory');
-- drop function if exists public.api_memory_add(text,text,text,jsonb,text,text);
-- drop function if exists public.api_memory_match(text,integer,real);
-- drop function if exists public.api_memory_search(text,integer);
-- drop function if exists public.api_ai_snapshot();
-- drop function if exists public.api_attribution_footer();
rollback;
```

The commented block is left commented on purpose. `drop schema ... cascade` is irreversible
and takes the extension objects with it.

## Linking this repository in Supabase

Supabase's GitHub integration reads a repository and a **branch**, and applies
`supabase/migrations/*.sql` from that directory, in filename order, to the project. Two
consequences:

1. This directory is `db/`, so the repository root must be this tree — which it is — and the
   CLI must be run from `db/`: `cd db && supabase db push`.
2. The integration follows a branch that only ever receives migrations. Point it at a
   dedicated branch, not at a branch that also carries documentation and skill edits, so a
   prose commit can never queue a schema change.

Linking is a dashboard action on the Supabase side, and it applies whatever is on the
chosen branch to the live project. It should be done once, by the principal, after the
branch has been reviewed.

## Conventions for the next migration

- Never edit a migration that has already been applied. Add a new one.
- Additive by default; a destructive statement needs a written reason in the commit body.
- New tables in `faw_ai` ship with `owner_id` and an owner policy in the same file.
- New functions are revoked from `public` and `anon`, then granted explicitly.
- Use `timestamptz` for anything a person will read. The operational tables store ISO text;
  do not copy that pattern into new tables.

## The webhook migration

`20261104150000_faw_ai_webhook_intake.sql` adds `faw_ai.webhook_sources` and
`faw_ai.webhook_events`, plus `register_webhook_source()` and `webhook_ingest()`. Both
tables have RLS enabled and **no policies**: the edge function reaches them with
`service_role`, and no logged-in staff member should be able to list gateway tokens or read
another person's incoming messages.

Verified inside rolled-back transactions:

| Case | Result |
| --- | --- |
| correct token, new `external_id` | `accepted`, event id returned |
| same `external_id` again | `duplicate`, no second row |
| wrong token | `bad_token` |
| unknown source | `unknown_source` |
| two different ids | two rows |

The deployed function itself could not be reached from this sandbox — only GitHub and
package registries resolve here, so `*.supabase.co` returns no route. That is a limitation
of the build environment, not evidence about the deployment; the SQL path it calls is what
was tested.

## The morning digest

`20261104160000_faw_private_morning_digest.sql` adds `faw_private.owner_id()` and
`faw_private.morning_digest()`, and schedules the latter at `15 5 * * *` (08:15 Riyadh,
after the existing 05:00 UTC periodic job).

It writes **one** row to `public.notifications` per day — overdue periodic reports,
overdue tasks, and accounts awaiting approval, in one sentence — with the deterministic id
`auto_digest_<date>` and an advisory lock, so a retried cron run is a no-op. Verified:
first run produced a digest, an immediate re-run returned `already_sent_today`.

It deliberately excludes medication, CPAP, workouts, and money: `public.notifications` is
readable by staff, and those fields are `secret` in `faw_ai`.

## Private profile data

This public repository intentionally contains **no person-specific profile manifest or seed payload**.
Private identity, contact, health, financial, family, and other personal facts must be supplied
through a private deployment channel and stored only in a private project or secret store.
Do not add real profile exports, intake payloads, or owner-specific seed SQL to this repository.

A previously tracked intake manifest is removed by the privacy-split branch. This change does
not rewrite Git history: older commits may still contain that file. The history audit is a
separate step and must be reviewed before any history rewrite is considered.

The database remains the source of truth for any already-applied data. Removing a manifest
from Git does not delete database rows, revoke access to historical Git objects, or prove that
all copies have been removed from forks, caches, or clones.

### Private-data handling checklist

- Keep private seed files outside the repository and outside public CI artifacts.
- Use a dedicated private repository only if versioning the private deployment is necessary.
- Prefer authenticated owner-scoped intake over committing personal payloads.
- Never place service-role keys, webhook tokens, or encryption keys in Git.
- Audit Git history and any forks separately; do not force-push or rewrite history without
  a verified backup and explicit approval.
