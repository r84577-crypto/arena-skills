# Projects

One entry per project. Keep the status line current — it is the first thing read in a new
session.

## Template

```markdown
## <project name>

- Status: planned | active | blocked | shipped | archived
- Objective: one sentence, the outcome not the activity
- Stack: languages, frameworks, services
- Source of truth: repository URL or path
- Live environment: URL, or "none"
- Constraints: licence, budget, deadline, compatibility
- Open decisions: link to the entry in DECISIONS.md
- Last touched: YYYY-MM-DD
```

## Example

## website-refresh

- Status: active
- Objective: replace the marketing site with a static build that deploys on merge
- Stack: Astro, Tailwind, Vercel
- Source of truth: `github.com/example/website-refresh`
- Live environment: staging only
- Constraints: no new runtime dependencies; copy approved by marketing
- Open decisions: hosting platform — see DECISIONS.md, 2026-10-12
- Last touched: 2026-10-31
