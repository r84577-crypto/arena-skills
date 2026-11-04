---
name: source-verification
description: >
  Checks claims against primary sources before they are repeated, and keeps the
  difference between what was verified, what was inferred, and what is unknown
  visible in the answer. Use when a task depends on current product behaviour,
  pricing, model names, limits, or rankings; when a claim came from a summary,
  a screenshot, or another model's output; when the user asks "is that still
  true"; or when writing documentation that will be trusted later. Do not use
  for questions answerable from the repository or from first principles.
license: MIT
version: 1.0.0
allowed-tools: Read, WebSearch, WebFetch
---

# Source verification

Most wrong answers are not invented from nothing. They are a real fact, one version out of
date, or a real fact about a different plan. Verification is the work of deciding *which* kind
of claim you are making, and labelling it so the reader can discount it correctly.

## When to use this

- The claim is about a product, price, limit, model name, or ranking — things that change.
- The source is a summary, a search snippet, a screenshot, or another model's answer.
- The output will be trusted later, by a person or by an agent.
- Two sources disagree.

Not for: reading the repository in front of you, or reasoning that needs no external fact.

## Three buckets, never blended

Every factual statement in the answer carries one of these, explicitly or by clear implication:

| Bucket | Meaning | How it reads |
| --- | --- | --- |
| **Verified** | Read on a primary source, dated | "Arena's help page (read 2026-10-31) says …" |
| **Inferred** | Follows from verified facts, not stated | "Inference: the free tier therefore excludes …" |
| **Unknown** | Not found, or not checkable | "Not documented; I could not confirm it." |

The failure this prevents is the confident middle: a sentence that sounds verified but is
inference. "Connectors are free, so heavy use costs nothing" is the shape of it — the first
clause is documented, the second is not.

## Procedure

1. **Name the claim.** Write it as a single checkable sentence before searching. "Is the
   free tier still free?" is checkable; "how does pricing work" is not.
2. **Go to the primary source.** Product documentation, the changelog, the pricing page, the
   repository, the specification. Not a blog summarising them, and not a search result snippet —
   open the page and read the section.
3. **Record the date.** A fact without a read date cannot be re-checked, and product docs move.
   Quote the line that carries the claim.
4. **Check for the second-order fact.** Documentation often states the feature and omits the
   limit: which plan, which region, which role, how many per session. If the limit is missing,
   the limit is unknown — not unlimited.
5. **Look for the contradiction.** Skim for a limitations or FAQ section. A single page can
   contradict itself between the marketing paragraph and the footnote.
6. **Prefer a dated snapshot to a live claim.** When the answer depends on a ranking, a price, or
   a count, report it as a snapshot: value, source, date. "Ranked first on 2026-10-28" ages
   honestly; "is the best model" does not.
7. **Write the answer with the buckets visible**, and cite the URL beside the claim it supports.

## What "verified" is allowed to mean

- A documentation page stating it, read today: verified, with the date.
- A screenshot in a help article: verified that the article showed it; not verified that the
  product still behaves that way.
- Another model's answer: never a source. It is a lead.
- Your own memory of a product: a hypothesis to check, not a fact.

## Ranking and benchmark claims

Numbers deserve more care than prose, because they look objective:

- Report the metric, the population, and the date together. A leaderboard score without its
  sample size or confidence interval invites over-reading.
- Treat overlapping confidence intervals as a tie. A one-point gap with ±3% is noise.
- Separate *measured* from *reported*. A vendor's own benchmark is a claim by an interested party.
- Say what the metric does not measure. A ranking of task success does not rank code quality,
  cost, or suitability for one specific job.

## Output

A short block at the end of any answer that leans on external facts:

```text
Verified:  <claim> — <URL>, read YYYY-MM-DD
Inferred:  <claim> — from the above, not stated by the source
Unknown:   <question> — no primary source found
```

Keep it to the claims the answer actually rests on. A bibliography nobody reads is decoration.

## Boundaries

- Reads pages and searches; may run read-only commands to inspect a local source tree.
- Writes nothing outside the file the user asked for; saves no copies of fetched pages.
- Must never present an inference as verified, cite a URL it did not open, or invent a date,
  version, quotation, or sample size.
- Must never resolve two conflicting sources by silently picking one — report the conflict.
- Requires explicit confirmation before acting on a finding (deploying, buying, migrating);
  verification is not authorisation.

## References

- [How to use Agent Mode on Arena](https://help.arena.ai/articles/5432423882-how-to-use-agent-mode)
  — an example of a page whose FAQ carries the limits the marketing copy omits; read 2026-10-31.
- [Arena Agent Mode setup, verified](../../docs/arena-agent-mode.md) — a worked example of the
  verified / unconfirmed split, with dates.

## ملخص عربي

لا تخلط بين ما تحقّقت منه وما استنتجته وما لم تجده. القاعدة: افتح المصدر الأول بنفسك — لا
الملخص ولا مقتطف البحث — وسجّل تاريخ القراءة، واقتبس السطر الذي يحمل الادعاء. وإذا ذكرت الوثيقة
الميزة ولم تذكر حدّها، فالحدّ مجهول وليس بلا حد. الأرقام والترتيبات تُذكر كلمحة بتاريخها لا
كحقيقة دائمة، والفروق داخل هامش الخطأ تُعدّ تعادلًا. وأي إجابة من نموذج آخر تُعدّ مؤشرًا للبحث
لا مصدرًا.
