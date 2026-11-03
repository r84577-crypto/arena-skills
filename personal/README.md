# `personal/` — the sovereign personal OS

This directory is the **personal** half of Adel Alharbi's digital twin. It is not institute
software, it does not read the institute's operational tables, and nothing in
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
