# Decisions

Append-only. A decision is superseded by a newer entry, never rewritten. This file exists so
that settled questions stay settled and an agent can see *why* something is the way it is.

## Format

```markdown
## YYYY-MM-DD — <short title>

- Decision: what was decided, in one sentence.
- Reason: the constraint or evidence behind it.
- Alternatives considered: and why they lost.
- Approved by: name or role.
- Affects: files, projects, or systems.
- Status: active | superseded by YYYY-MM-DD — <title>
```

## Entries

## 2026-10-31 — Website hosting stays on Vercel

- Decision: deploy the marketing site to Vercel, not to a container platform.
- Reason: preview deployments per pull request; the team already pays for the plan.
- Alternatives considered: Fly.io (cheaper at low traffic, no preview-per-PR flow);
  self-hosted nginx (operational load with no benefit here).
- Approved by: engineering lead.
- Affects: `website-refresh`, deploy workflow, DNS.
- Status: active
