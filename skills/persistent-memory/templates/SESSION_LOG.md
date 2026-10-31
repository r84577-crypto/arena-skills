# Session log

Newest entry first. One entry per session, short. The value is the handoff, not the diary: a
new session should be able to read the top entry and start working.

## Format

```markdown
## YYYY-MM-DD — <project> — <one-line goal>

- Completed: artifact paths, not activities.
- Verified: the command or check that ran, and its actual result.
- Not verified: what remains untested, and why.
- Decisions: link to the entry in DECISIONS.md, if any.
- Blockers: what is stuck, and on whom.
- Next: the exact next step.
```

## Entries

## 2026-10-31 — website-refresh — replace the hero and fix the deploy

- Completed: `src/components/Hero.astro`, `astro.config.mjs`.
- Verified: `npm run build` passed; preview deployment returned HTTP 200 on `/`.
- Not verified: the mobile breakpoint at 375px — no device available in this session.
- Decisions: none.
- Blockers: the production domain still resolves to the old host; DNS change is with ops.
- Next: check the 375px breakpoint, then merge the open pull request.
