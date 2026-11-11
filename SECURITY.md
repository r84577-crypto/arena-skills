# Security policy

This repository ships two things with two different threat models:

1. **A production web app** (`app/` — Next.js + Supabase + email/WhatsApp
   delivery). It runs as a service, holds session-gated data, and sends
   real messages. This is the part most reports will concern.
2. **Markdown skills and small checkers** (`skills/`, `scripts/`). Instructions
   an agent may follow — executable in the only sense that matters.

## Reporting a vulnerability

**Do not open a public issue for a security report.**

Use GitHub's private reporting channel:
[Security → Report a vulnerability](https://github.com/r84577-crypto/arena-skills/security/advisories/new)

If that is unavailable to you, open a public issue that says only *"I have a
security report, please enable private reporting"* — with no details — and a
private channel will be opened.

### What to include

- The file and line, or the exact request, that triggers the problem.
- What an attacker gains. "A secret is exposed" is a finding; "this looks wrong"
  is a hunch, and it will be treated as one.
- The version or commit you tested.

**Never paste a real credential into a report.** Quote the first four characters
and the length (`xox… 60 chars`). If a live secret has leaked, revoke it first
and then report it — revocation is not something this project can do for you.

## In scope — the app

| Class | Example |
| --- | --- |
| Auth bypass | Reaching `/api/send-*` or owner data without an owner session |
| Ledger forgery | A `comms_log` row marked `sent` without a provider delivery |
| Scope bleed | Personal data reachable from a training-scoped call or vice versa |
| Secret leakage | A server-only variable (`*_APP_PASSWORD`, `*_TOKEN`) reaching the browser bundle |
| Header regression | A route served without the CSP/HSTS baseline in `next.config.ts` |
| RLS gap | An app-schema table without row-level security (`security_sweep` verdict `drift`) |

## In scope — skills and checkers

| Class | Example |
| --- | --- |
| Instruction-level risk | A skill whose instructions would lead an agent to exfiltrate data, run untrusted code, or write outside its stated boundaries |
| Checker bypass | A file layout that makes `validate-skills.py` or `scan_secrets.py` exit 0 when it should not |
| Installer behaviour | `install-skills.sh` writing outside its documented destination, or overwriting without `--force` |
| CI integrity | A workflow that runs untrusted input with write scope, or an action that is not pinned |

## Out of scope

- **Supabase, Netlify, Meta, Google, and Resend infrastructure.** Their
  security is their own; report issues to their maintainers.
- **The third-party repositories described in `docs/`.** They are referenced,
  never vendored. See [NOTICE.md](NOTICE.md).
- **`allowed-tools` being advisory.** Hosts may ignore it; this is a documented
  property of the format, not a vulnerability.
- Missing hardening on your own machine (sandboxing, agent permissions).

## What this project does and does not promise

- Row-level security is enforced in the database and verified live
  (`security_sweep()->>'verdict'` must read `clean`); the app never trusts
  the client for the final send status.
- `scan_secrets.py` is heuristic (known shapes + entropy); a clean run means
  *these specific checks found nothing*, and nothing more.
- Nothing here has been reviewed by a security professional or tested against
  a hostile deployment. Treat third-party skills you install as code you have
  not read, because that is what they are.

## Response

Best effort, no SLA: this is a single-maintainer project with no funding. Expect an
acknowledgement within a week and an assessment within two. Credit is given in the
advisory unless you ask otherwise.

## Supported versions

Only the tip of `main`. There are no release branches, and fixes are not backported.
