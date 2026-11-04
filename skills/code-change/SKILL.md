---
name: code-change
description: >
  Makes a change in an existing repository the way a careful maintainer would:
  read the tree and the conventions first, keep the patch narrow, run the
  project's own tests and linters, review the diff, and report what actually ran
  and what did not. Use when asked to fix a bug, add a feature, update
  dependencies, or clean up code in a repository that already exists. Use when a
  change must be proposed as a pull request rather than applied. Do not use for
  repository hygiene or licensing review, and do not use for greenfield code
  with no existing conventions to follow.
license: MIT
version: 1.0.0
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Code change

A patch is a claim about a codebase. The claim is only as good as the reading that preceded it
and the checks that followed it. Most damaging agent-authored changes are not wrong syntax; they
are a plausible rewrite of code whose purpose was never established.

## When to use this

- A bug fix, a feature, a refactor, or a dependency bump in an existing repository.
- A change that will be reviewed by someone else, in a branch or a pull request.
- A repository where the project already has tests, formatting, and conventions.

Not for: repository-level hygiene (use `repo-audit`), security auditing, or designing a system
from scratch.

## Modes

- **Propose mode** (default): produce the diff and the reasoning, and stop before committing.
- **Apply mode**: only when the user asks for the change to be made. Then edit in place, run the
  checks, and report. Committing, pushing, or opening a pull request each need their own explicit
  instruction.

## Procedure

1. **Read before writing.** Locate the build entry points, the test command, the formatter and
   linter configuration, and the contribution guide. Two minutes here prevents the most common
   review comment: "this does not follow the project's conventions."
2. **Establish the failure.** Reproduce the bug, or find the test that shows the current
   behaviour. If you cannot reproduce it, say so before changing anything — a patch for an
   unreproduced bug is a guess.
3. **Find the seam.** Search for the callers and the tests around the code you intend to touch.
   The correct fix is usually at the layer the project already separates, not at the surface
   where the symptom appeared.
4. **Change the minimum.** Follow the existing style, naming, and error handling. No drive-by
   reformatting, renames, or dependency additions in the same patch. If a rewrite is genuinely
   required, say why before doing it.
5. **Add the check.** A bug fix without a regression test is not finished — unless the project
   has no test harness, in which case say that the check is manual and describe the exact steps.
6. **Run what the project runs.** The project's own commands, not approximations of them. Capture
   the output.
7. **Review your own diff.** Read `git diff` as a reviewer would. Look for accidental whitespace
   churn, debug output, commented-out code, and files that should not be committed.
8. **Report.** Change, evidence, verification, and gaps — in that order.

## Reporting a change

```text
Changed:    <files> — one line each, why this file
Reproduced: <command or test> — before: <output>
Verified:   <command> — after: <output>
Not run:    <check> — and why
Risk:       <what could break, and where to look first>
```

"Tests pass" without the command and its output is not verification. It is a sentence.

## Rules that prevent the usual failures

- **Never invent output.** If a command was not run, or failed, report that. A pasted success
  message that was not produced is worse than a missing one.
- **Never widen scope silently.** An unrelated cleanup found mid-task is reported, not bundled.
- **Never change behaviour the user did not ask about** — validation, defaults, error messages,
  public signatures — without flagging it.
- **Never commit secrets, generated artifacts, or dependency directories.** Check the diff for
  them explicitly.
- **Destructive operations are opt-in.** `git reset --hard`, force pushes, history rewrites,
  branch deletion, and database migrations against real data require explicit confirmation.
- **Deployments and releases are a separate decision.** Building is not deploying.
- **A failing check is information.** Fix it, or report it with the output; do not disable it.

## Working with a hosted agent

Some hosts give you a working copy of a repository, a diff panel, and a branch rather than a
terminal on the user's machine. Two consequences worth stating when they apply:

- The change is delivered as commits on a branch and a pull request; the user reviews the diff
  there. Say which branch and what the pull request contains.
- Hosts commonly allow one pull request per session. Bundle related work into that pull request,
  and open a new session for unrelated work.

## Boundaries

- May read the whole repository, edit files, and run the project's build, test, lint, and
  formatter commands.
- May create a branch and commits when Apply mode is requested; pushing and opening a pull
  request need a separate explicit instruction.
- Must never do without explicit confirmation: force-push, rewrite history, delete branches or
  files it did not create, run migrations against non-local data, install system packages,
  change CI credentials, or deploy.
- Must never report a check as passing without having run it, or omit a failing check from the
  summary.

## References

- [How to use coding in Agent Mode](https://help.arena.ai/articles/1655691990-how-to-use-coding-in-agent-mode)
  — sandbox copy, diff panel, checks window, one pull request per session; read 2026-10-31.

## ملخص عربي

اقرأ المستودع قبل أن تكتب: أوامر البناء والاختبار والتنسيق، ثم اصطلاحات المشروع. أعِد إنتاج
الخطأ قبل إصلاحه، وضع التغيير في الطبقة الصحيحة، واجعله أصغر ما يمكن دون إعادة تنسيق جانبية.
شغّل أوامر المشروع نفسها وسجّل مخرجاتها، وراجع الفروق بعين المراجع. لا تنسب نجاحًا لأمر لم
تشغّله، ولا تخفِ اختبارًا فاشلًا، ولا تدمج تغييرات غير مطلوبة. الدفع والنشر والعمليات المدمّرة
تحتاج إذنًا صريحًا منفصلًا.
