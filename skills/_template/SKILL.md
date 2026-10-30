---
name: example-skill
description: Replace this with one or two sentences describing what the skill does and the exact conditions under which an agent should load it. Name the tasks, the artifacts produced, and the requests that trigger it.
license: MIT
version: 0.1.0
# Advisory: hosts may ignore this. Keep it consistent with ## Boundaries below.
allowed-tools: Read, Write, Bash
---

# Example Skill

One paragraph of orientation: what problem this skill solves, and the outcome a successful run produces.

## When to use this

- Use when …
- Do **not** use when … (state the adjacent cases explicitly — this prevents an agent from over-applying the skill)

## Modes

State whether loading this skill authorizes any action. Default to guidance-only:

- **Guidance mode** (default): answer questions using this file. Do not create files, run commands, or modify anything.
- **Execution mode**: only when the user explicitly asks for it. Then …

If a request is ambiguous, ask one focused question before acting.

## Procedure

1. First step — what to read or check before doing anything.
2. Second step.
3. Third step — what the completed output looks like.

Keep this section short. Move reference material into sibling files and link them relatively — a `REFERENCE.md` beside this file, for example.

## Output

Describe the exact artifact: its path, format, and required fields. If the skill produces machine-readable output, define the schema in a sibling JSON Schema file and validate it.

## Boundaries

- Files this skill may write: …
- Commands it may run: …
- What it must never do without explicit confirmation: …

## Validation

If this skill ships a checker, document how to run it:

```shell
node validate-example.cjs <path>
```

## References

- [Upstream documentation](https://example.com) — record what was used and when, so the skill can be re-verified
