---
name: repo-audit
description: >
  Audits a repository for the hygiene and trust gaps that block collaboration:
  missing or misdetected license and attribution, absent CI, dead internal
  links, stale metadata, credential-bearing files, and undocumented setup.
  Use when asked to review a repository, decide whether a project is safe to
  adopt or contribute to, prepare a repository for publication, or explain why
  a repository reads as abandoned. Use when a README promises more than the
  tree contains. Do not use for reviewing application code for bugs or
  vulnerabilities - use a code review or security audit skill for that.
license: MIT
version: 1.0.0
allowed-tools: Read, Bash
---

# Repository audit

Assess a repository the way a careful maintainer or a prospective adopter would: by
reading the tree, not the README. Every finding must cite a file path and, where
possible, a measured number.

## When to use this

- A repository is being proposed as a dependency, a contribution target, or a reference.
- A repository looks unmaintained and you need to say why, specifically.
- A project is about to be published and needs its gaps closed first.

Not for: reviewing code correctness, security testing, or performance work.

## What to measure

| Area | Check | Failure looks like |
| --- | --- | --- |
| License | `LICENSE` exists **and** provider detection agrees | File present but API reports `NOASSERTION` — usually appended text inside the license |
| Attribution | Vendored code or prose names its source and license | Copied docs with no source link |
| Structure | Claimed capabilities exist in the tree | README promises "skills", tree has one file |
| Links | Internal links and anchors resolve | 73 links resolving to 404 inside the repo |
| CI guards | Lint, link check, secret scan run on PRs | No `.github/workflows/` |
| Credentials | No credential files or token-shaped strings | `.npmrc`, `nuget.config`, `ghp_…` in history |
| Metadata | Description, topics, license, default branch are real | `"description": "test "` |
| Maintenance | Recent commits and releases, or an explicit archive | Last push years ago, no notice |

## Procedure

1. Read the tree before the prose. List the top two levels and compare against what the
   README claims. Capability claims that are not backed by files are the most common defect.
2. Check the license file itself, not just its presence. Confirm the hosting provider detects
   a license, and read per-directory license files where a repository vendors other work.
3. Measure internal links and anchors. Count them; do not eyeball.
4. Check for CI, and check what it actually enforces rather than that it exists.
5. Scan for credential-bearing files and token-shaped strings.
6. Check activity: last push, commits in the last 90 days, latest release.
7. Report ordered by severity, with paths and numbers.

## Output

A short report with this shape:

```text
Summary: <one sentence verdict>

Blocking
- <finding> — <path> — <why it matters> — <fix>

Should fix
- ...

Notes
- <anything measured that is fine, so the reader knows it was checked>
```

Rules for the report:

- Every finding names a path.
- Every quantitative claim is measured in this run.
- If something could not be checked, say so explicitly instead of implying it passed.
- Do not recommend a repository as safe. State what you verified and what you did not.

## Boundaries

- Read-only. Do not modify the audited repository unless asked separately.
- Do not clone or execute anything from the audited repository to "see if it works" without
  explicit permission; that is a supply-chain decision, not an audit step.
- Never paste secrets found in a repository into the report. Name the file and the kind of
  secret, not the value.

## Validation

Before delivering, confirm each claim in the report can be reproduced with a command you ran.
If a claim came from a README rather than the tree, label it as unverified.
