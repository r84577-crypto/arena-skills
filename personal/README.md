# `personal/` — the sovereign personal OS

This directory contains reusable schema and application logic for a single-owner personal system. It is separate from institute software, it does not read the institute's operational tables, and nothing in
`db/` depends on it.

## Why it is a separate deployment

Phase 1 was built inside the existing Supabase project `faw-marketing`, because that project
already held his account and his operational context, and extending it was the low-risk
choice at the time. The clarification that changed the requirement is simple:

> the twin is exclusively personal and operates independently of any institution.

A personal database that lives inside the institute's project is, by definition, not
independent. It inherits the institute's owner account, its staff, its backups, and its
billing — and the principal's health and financial rows sit one `role` change away from an
institute administrator.

So the personal system moves to its own project:

| | `faw-marketing` (institute) | personal project |
| --- | --- | --- |
| Audience | staff, roles, reports, visits | one person |
| Contains | institute operations | health, money, life milestones |
| Access | role-based, supervisors see broadly | owner-only, no second reader |
| Deletion | governed by institute retention | his decision alone |

## What happens to phase 1

It stays where it is, working, and is re-labelled honestly: a **pilot** that proved the
schema, the RLS model, the intake flow, the webhook door, and the morning digest. The facts
are then exported and imported into the personal project. No data is lost, and
`faw-marketing` keeps no personal health or financial rows once the export is verified.

`migrations/0001` here is the personal schema. It is intentionally **stricter** than the
pilot: no staff roles, no institute foreign keys, and no table that any account other than
the principal can read.

## Running it

```shell
cd personal
supabase link --project-ref <personal-project-ref>
supabase db push          # applies migrations/ in order
```

The project reference is deliberately not committed: creating the project is the
principal's action, on his own account and his own billing.

## What this deployment deliberately does not include

| Claim in the briefs | Reality | What exists instead |
| --- | --- | --- |
| Trained dialect model (Najdi/Qassimi/Harb) | Training a model needs audio corpora and a training pipeline; neither exists here | `personal.style_rules` — five registers of instruction text, editable in one table |
| Voice interaction | Needs speech-to-text plus an audio pipeline; the CLI and an API key are both absent | the data model and recall functions are ready for a transcript to land in `personal.memory` |
| "Zero memory loss" | This agent has no cross-conversation memory; that is a host property, not a database one | `personal.snapshot()` and `search_memory()` produce context that can be re-injected each session |
| AES-256 everywhere | At-rest encryption is the platform's; column encryption is opt-in and expensive | `personal.put_secret()` / `reveal_secret()` — pgcrypto AES-256 with the key in Supabase Vault |

## Status

**Written and parse-checked, not applied.** `supabase` CLI is not installed in the build
sandbox, and the project does not exist yet: creating it is the principal's action, on his
own account and billing. Parsing was verified with `pglast` — 44 + 17 + 15 statements, plus
plpgsql body checks — which proves syntax, not behaviour. Behaviour is proven by the pilot
in `db/`, where every function was executed against a real database.
