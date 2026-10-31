---
name: persistent-memory
description: >
  Gives an agent durable project memory across sessions by reading and updating
  a small set of external Markdown files (profile, projects, decisions, tasks,
  session log, sources) instead of relying on chat history. Use when work spans
  more than one session, when a project has approved decisions that must not be
  silently reversed, when handing work to another agent or person, or when a
  hosted agent has no built-in cross-session memory. Use when asked to "remember"
  something for next time. Do not use for storing secrets, credentials, or
  personal data that the task does not require.
license: MIT
version: 1.0.0
allowed-tools: Read, Write, Edit, Bash
---

# Persistent memory

Chat history is not memory. It is not guaranteed to be available in the next session, it is
not readable by a different agent, and it is not a place where an approved decision can be
found later. Durable context has to live in files the agent can actually read and write, in a
place both sides can check.

This skill defines that file set, when to read it, when to update it, and how to prove the
update happened.

## When to use this

- A task will continue in another session, or another agent or person will pick it up.
- The project has decisions that were approved and must not be quietly overwritten.
- The host keeps no cross-session memory of its own — hosted agent products usually do not.
- The user says "remember this", "where did we leave off", or "continue the project".

Not for: storing credentials, tokens, or personal data; a single-session question; a task
whose entire state fits in one file that is already being edited.

## Modes

- **Read mode** (default): locate and read the memory files, then answer or plan from them.
  Do not create or modify anything.
- **Write mode**: only when the user asks to record, update, or hand off. Then follow the
  procedure below and verify each write.

If a memory file is referenced but does not exist, say so and continue with what is available.
Do not invent its contents.

## The file set

Create a directory named `ARENA-MEMORY` (or any single agreed name) and keep it in a service
the agent can read **and** write: a repository, a synced drive, or a wiki. Templates ship with
this skill in `templates/`.

| File | Holds | Changes |
| --- | --- | --- |
| [`PROFILE.md`](templates/PROFILE.md) | Language, tone, working agreements, standing constraints | Rarely |
| [`PROJECTS.md`](templates/PROJECTS.md) | One entry per project: goal, state, links, owner | When status changes |
| [`DECISIONS.md`](templates/DECISIONS.md) | Approved decisions, the reason, the date, who approved | Append-only |
| [`TASKS.md`](templates/TASKS.md) | Open, done, blocked, next step | Every session |
| [`SESSION_LOG.md`](templates/SESSION_LOG.md) | One short entry per session: what changed, what was verified | Append-only |
| [`SOURCES.md`](templates/SOURCES.md) | References that were actually used, with dates | When sources are added |

Two rules make the set work:

1. **`DECISIONS.md` is append-only.** A decision is superseded, never rewritten. The history is
   the point: it is what stops an agent from re-litigating settled questions.
2. **Every entry is dated and attributable.** "Use Postgres" without a date and a reason is
   folklore, not a decision.

Keep each file under a few hundred lines. A memory file nobody reads is worse than none: it
creates the appearance of context.

## Procedure

1. **Locate.** At the start of substantial work, find the memory directory. If the host has no
   filesystem, use the connector that can read it (a repository, a drive, a wiki page).
2. **Read, in order.** `PROFILE.md`, `PROJECTS.md`, `DECISIONS.md`, `TASKS.md`, and the tail of
   `SESSION_LOG.md`. Read `SOURCES.md` only if the task depends on prior references.
3. **State what was found.** One or two lines: current project state, open tasks, the decisions
   that constrain this task. If nothing was found, say that instead of proceeding silently.
4. **Work.** Treat approved decisions as constraints. If the task requires breaking one, stop
   and ask; do not overwrite it.
5. **Record at the end of the session.** Update `TASKS.md` and `PROJECTS.md`, append to
   `SESSION_LOG.md`, append to `DECISIONS.md` only if a decision was actually approved.
6. **Verify.** Re-read every file written and confirm the change is present. Report the path and
   what changed. If the write failed, say it failed and hand back the exact text to save.

### The handoff entry

The useful end-of-session record answers, in order:

- Project and objective.
- What was completed — with the artifact paths.
- What was verified, and how (a command and its result, a link, a test).
- What was **not** verified or is known broken.
- Decisions approved this session.
- Open tasks and blockers.
- The exact next step, specific enough to start from.

"Made progress on the site" fails all seven.

## Establishing that it works

A memory system is a claim until it is tested. This test takes two sessions:

1. Session A: write a harmless, specific decision into `DECISIONS.md` (for example, a chosen
   file-naming convention) and verify the file contains it.
2. Session B, with no history from Session A: ask the agent to retrieve that decision and quote
   the line it came from.
3. The answer must match the file. If it does, retrieval works. If the agent "remembers" without
   reading, it is guessing.

This proves the files work. It does not prove the host has built-in memory, which is a separate
question and should not be assumed.

## Failure modes to avoid

- **Treating chat history as the record.** It is not durable, portable, or auditable.
- **Updating memory silently.** An unverified write reported as done is the failure the whole
  system exists to prevent.
- **Overwriting approved decisions.** Supersede with a new dated entry.
- **Storing secrets.** No tokens, passwords, connection strings, or unnecessary personal data.
  A memory file is usually the least protected copy of anything in it.
- **Unbounded growth.** Summarise; move detail into the project's own documentation.
- **Memory that contradicts the code.** When they disagree, the tree wins; fix the memory file.

## Boundaries

- Files this skill may write: inside the agreed memory directory only — the six memory files and
  nothing else. No writes to project source unless the task separately calls for it.
- Commands it may run: read-only listings and text reads to locate and verify files. A write is
  reported with its path; a verification read follows it.
- It must never do without explicit confirmation: write outside the memory directory, delete or
  rewrite a decision entry, push a memory change to a shared branch, or store credentials or
  personal data.
- If no write-capable path exists, it returns the proposed update as text and says the memory
  was **not** saved.

## References

- [How to use Agent Mode on Arena](https://help.arena.ai/articles/5432423882-how-to-use-agent-mode)
  — session workspace behaviour, read 2026-10-31.
- [Arena Agent Mode setup, verified](../../docs/arena-agent-mode.md)
  — the host-specific caveats: workspace files are per session, and no built-in memory is documented.

## ملخص عربي

سجل المحادثة ليس ذاكرة دائمة. هذه المهارة تنشئ مجلد `ARENA-MEMORY` بستة ملفات: التفضيلات
`PROFILE.md`، المشاريع `PROJECTS.md`، القرارات `DECISIONS.md`، المهام `TASKS.md`، سجل الجلسات
`SESSION_LOG.md`، والمصادر `SOURCES.md`. تُقرأ في بداية كل مهمة كبيرة، وتُحدَّث في نهايتها،
ثم يُعاد قراءتها للتأكد من أن الحفظ تم فعلًا. قاعدة أساسية: ملف القرارات يُضاف إليه ولا يُعاد
كتابته، وكل قرار بتاريخه وسببه. ولا تُخزَّن فيه كلمات مرور أو مفاتيح أو بيانات شخصية.
الاختبار: اكتب قرارًا في جلسة، ثم استرجعه في جلسة جديدة مع ذكر السطر الذي جاءت منه الإجابة.
