---
name: document-delivery
description: >
  Produces a document a specific reader can act on: audienced fixed first, an
  outline before prose, every claim sourced or marked as an assumption, and a
  final pass for structure, stale links, and statements the evidence does not
  support. Use when asked to write, restructure, translate, or review a guide,
  specification, report, README, or policy; when a draft reads as generated
  filler; or when a document will be handed to someone who cannot ask follow-up
  questions. Do not use for code comments, commit messages, or chat replies.
license: MIT
version: 1.0.0
allowed-tools: Read, Write, Edit
---

# Document delivery

A document is finished when a reader who cannot ask you a question gets the right action from
it. That standard rules out most of what passes for a draft: long preambles, sections that
restate their headings, and confident sentences with nothing behind them.

## When to use this

- A guide, specification, report, policy, or README is being written or rewritten.
- A draft exists but reads as filler, repeats itself, or buries the decision.
- A document must survive without its author — a handoff, a public page, a compliance artifact.
- A translation or restructuring has to preserve meaning, not word order.

Not for: chat answers, code comments, commit messages, or release notes generated from a diff.

## Procedure

1. **Name the reader and the outcome.** One sentence each: who reads this, and what they should
   be able to do afterwards. If the answer is "everyone", the document is for no one; propose a
   narrower reader.
2. **Fix the shape before the prose.** Write the headings first, as an outline, and check that
   each one earns its place. A section that only restates its heading is deleted, not rewritten.
3. **Write the load-bearing parts first.** The decision, the constraint, the procedure. Preamble
   and background are written last, and only if they change what the reader does.
4. **Mark what is not known.** Assumptions, open questions, and unverified statements get an
   explicit label. A document that hides its uncertainty transfers the risk to the reader.
5. **Pass for accuracy.** Every number, date, name, and claim: is it from a source, from the
   repository, or from memory? Memory is not a source. Fix or label.
6. **Pass for structure.** Headings nest without skipping; no section appears once; tables have
   a header row and consistent columns; lists are parallel in grammar.
7. **Pass for mechanics.** Links resolve; code blocks declare a language; the file's own
   conventions (line width, heading case, punctuation) are followed. Run the project's linter if
   it has one — a document that fails `make check` is not delivered.
8. **Read the first and last paragraph aloud.** The first must state what this is and who it is
   for. The last must state what to do next.

## Structural patterns worth reusing

| Need | Shape |
| --- | --- |
| A procedure | Numbered steps, one action each, prerequisites stated before step 1 |
| A decision record | Context, options, decision, consequences, date |
| A reference page | Table with a stable schema; prose only where a table cannot carry it |
| A handoff | What was done, what was verified, what is open, next step |
| A correction | What was wrong, what is right, what changes for the reader, date |

## Reviewing someone else's draft

Report in this order, and stop at the first category that applies — a document with a wrong
claim does not need its commas fixed:

1. **Wrong or unsupported claims.** The only category that is fatal.
2. **Missing content** the stated reader needs in order to act.
3. **Structure** that hides the decision or the procedure.
4. **Mechanics**: links, headings, formatting, tone.

Quote the line and say what to do instead. "This section is unclear" is not a review.

## Bilingual and translated documents

- Translate meaning, not syntax. Idiom and sentence order change; numbers, names, and code do not.
- Keep identifiers, commands, paths, and API names in their original form inside translated prose.
- When a document exists in two languages, say which one is authoritative. Two translations of
  equal standing drift within a release.
- Right-to-left text mixed with code and Latin terms needs explicit direction control in the
  final format; check the rendered output, not the source.

## Boundaries

- May read any file needed for context, and write only the document the user asked for, at the
  path they asked for.
- May run read-only checks (link checkers, linters, word counts) and reports their output.
- Must never do without explicit confirmation: overwrite an existing document wholesale, delete
  sections the user wrote, publish or send the document anywhere, or translate material the user
  has not cleared for that audience.
- Must never invent a citation, a statistic, a date, or a quotation to make a paragraph land.

## References

- [Write the Docs — documentation guide](https://www.writethedocs.org/guide/) — audience-first
  structure, read 2026-10-31.
- [`skill-authoring`](../skill-authoring/SKILL.md) — the adjacent case: turning a document into a
  skill an agent loads, rather than one a person reads.

## ملخص عربي

حدّد القارئ والنتيجة قبل الكتابة: من يقرأ هذا، وماذا يجب أن يستطيع فعله بعده. ارسم العناوين أولًا،
واحذف كل قسم لا يضيف شيئًا، واكتب الفكرة الحاملة أولًا ثم المقدمة أخيرًا. ميّز بوضوح بين المؤكد
والافتراض والمجهول، ولا تنسب رقمًا أو اقتباسًا بلا مصدر. راجع المستند ثلاث مرات: للدقة، فللبنية،
فللشكل والروابط. وعند المراجعة ابدأ بالخطأ في المعلومة قبل الأسلوب، واقتبس السطر واقترح البديل.
