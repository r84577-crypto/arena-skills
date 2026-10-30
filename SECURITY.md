# Security policy

This repository ships Markdown, small stdlib-only Python checkers, and one bash
installer. It runs no service, holds no data, and has no runtime dependencies.
That is a short attack surface, but it is not an empty one: skills are instructions
that an agent may follow, and instructions are executable in the only sense that
matters.

## Reporting a vulnerability

**Do not open a public issue for a security report.**

Use GitHub's private reporting channel:
[Security → Report a vulnerability](https://github.com/r84577-crypto/arena-skills/security/advisories/new)

If that is unavailable to you, open a public issue that says only *"I have a
security report, please enable private reporting"* — with no details — and a
private channel will be opened.

### What to include

- The file and line, or the exact command, that triggers the problem.
- What an attacker gains. "A secret is exposed" is a finding; "this looks wrong"
  is a hunch, and it will be treated as one.
- The version or commit you tested.

**Never paste a real credential into a report.** Quote the first four characters
and the length (`ghp_… 40 chars`). If a live secret has leaked, revoke it first
and then report it — revocation is not something this project can do for you.

## In scope

| Class | Example |
| --- | --- |
| Secret leakage | A checker that prints a token value, or a pattern that lets a credential-bearing file pass |
| Instruction-level risk | A skill whose instructions would lead an agent to exfiltrate data, run untrusted code, or write outside its stated boundaries |
| Checker bypass | A file layout that makes `validate-skills.py` or `scan_secrets.py` exit 0 when it should not |
| Installer behaviour | `install-skills.sh` writing outside its documented destination, or overwriting without `--force` |
| CI integrity | A workflow that runs untrusted input with write scope, or an action that is not pinned |

## Out of scope

- **The third-party repositories described in `docs/`.** They are referenced, never
  vendored, and their security is their own. Report issues to their maintainers.
  See [NOTICE.md](NOTICE.md) for the distinction.
- **The `docx`, `pdf`, `pptx`, and `xlsx` skills in `anthropics/skills`.** They are
  proprietary and are documented here only as a warning. This repository does not
  ship them.
- **`allowed-tools` being advisory.** Hosts may ignore it; this is a documented
  property of the format, not a vulnerability. [README.md](README.md) says so plainly.
- Missing hardening on your own machine (sandboxing, agent permissions). That is
  configuration, not a defect here.

## What this project does and does not promise

The checkers are heuristics. `scan_secrets.py` matches known credential shapes and
will miss re-encoded, split, or novel formats; `validate-skills.py` checks structure,
not intent. A clean run means *these specific checks found nothing*, and nothing more.

Nothing here has been executed against a hostile repository as part of a test suite.
No skill is reviewed by a security professional before merge. Skills are read by
humans, checked mechanically, and merged — treat third-party skills you install as
code you have not read, because that is what they are.

## Response

Best effort, no SLA: this is a single-maintainer project with no funding. Expect an
acknowledgement within a week and an assessment within two. Credit is given in the
advisory unless you ask otherwise.

## Supported versions

Only the tip of `main`. There are no release branches, and fixes are not backported.
