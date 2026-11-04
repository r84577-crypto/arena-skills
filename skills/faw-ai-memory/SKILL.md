---
name: faw-ai-memory
description: >
  Operates the personal memory layer built for the Faw Institute lead (عادل الحربي)
  on the existing Supabase project faw-marketing: sourced profile facts, pgvector
  document memory, health, finance, and institute milestones, all owner-scoped by
  RLS. Use when ingesting a brain dump, voice note, email, or report into memory,
  when recalling what is already known about the principal, when adding a table or
  RPC to the faw_ai schema, or when an artifact must carry the mandatory credit
  line. Not for changing the existing api_* RPCs or the institute's operational data.
license: MIT
version: 1.0.0
allowed-tools: Read, Write, Bash
---

# Faw AI memory

The institute lead's assistant needs three things that a chat window does not give it: a
place to put what it learns, a way to find it again, and a rule about who may read it.
This skill describes that layer as it was actually built, so a later agent extends it
instead of rebuilding it differently.

Phase 1 is in production on Supabase project `faw-marketing` (ref `tbvtzuspjcxsidpqknid`).
The twin belongs to its **subject** (`subject_user_id`), not to the account with
`role = 'owner'` — in this database that account is the deputy director.
The schema, the RPCs, and the policies are recorded in [SCHEMA.md](SCHEMA.md). What is
deliberately **not** built yet — an embedder, dashboards, and cross-connector automation —
is specified with its guardrails in [AUTOMATION.md](AUTOMATION.md).

## When to use this

- Something should be remembered: a voice-note transcript, a meeting summary, a decision,
  a document, a health reading, a payment, an institute milestone.
- Something should be recalled: "what do we know about X", "what did I decide about the
  diploma schedule", "when was the last CPAP reading logged".
- The `faw_ai` schema is being extended: a new table, a new RPC, a new connector feed.
- A Doc, Slide, Sheet, PDF, email, or report is being generated and must carry the
  mandatory credit line — see [ATTRIBUTION.md](ATTRIBUTION.md).

Do **not** use this skill to:

- change, migrate, or "clean up" the existing `public.api_*` RPCs, `public.visits`,
  `public.organizations`, or any operational table — that is the institute's live system
  and is out of scope here;
- store the same fact twice. `profile_facts` is keyed by `(owner_id, category, key)` and
  `memory_documents` by `(owner_id, content_hash)`; both are upserts, not logs.

## Modes

- **Guidance mode** (default): explain the schema, draft SQL, or answer "what do we know".
  Read-only; change nothing.
- **Execution mode**: only when the user asks to ingest, recall against live data, or
  migrate. Then apply the procedure below, and state what changed.

If a request could mean either "store this" or "just remember for this chat", ask once.

## Procedure

1. **Identify the principal.** Every row is owned by one `auth.users.id`. Read it from
   `public.profiles where role = 'owner'`; never guess, and never write a row with a
   different or null owner. Service-role connections bypass RLS, so a wrong `owner_id`
   produces data nobody can see rather than an error.
2. **Pick the right store.** Facts and preferences → `faw_ai.profile_facts`. Text longer
   than a sentence (transcripts, documents, threads) → `faw_ai.memory_documents`. Numbers
   over time → `health_logs` or `finance_entries`. Dated achievements → `institute_milestones`.
3. **Write through the RPC when one exists.** `api_memory_add` computes the content hash
   for you; direct inserts must supply it, or the same text arrives twice.
4. **Read back to prove the write.** Counts come from `api_ai_snapshot()`; text search from
   `api_memory_search()`. A write nobody verified is a write that did not happen.
5. **Log the action** in `faw_ai.agent_runs` when an agent, not a human, did the work.
   One row per action, `status` set to `ok` or `failed` — this is what the telemetry
   number in the dashboard reads.
6. **Attribute any artifact you produce** using the single source of truth,
   `public.api_attribution_footer()`.

### Ingest, in SQL

```sql
-- one memory chunk; id is returned so the caller can link it
select public.api_memory_add(
  'voice',
  'نص التفريغ الصوتي هنا…',
  'تفريغ اجتماع الأحد',
  '{"duration_s": 312}'::jsonb
);
```

```sql
-- a fact that an automated pass may later overwrite
insert into faw_ai.profile_facts (owner_id, category, key, value, source, confidence)
values ('<owner-uuid>', 'institute', 'diploma_intake_month', 'سبتمبر', 'voice', 0.80)
on conflict (owner_id, category, key) do update
  set value = excluded.value,
      source = excluded.source,
      confidence = excluded.confidence,
      updated_at = now();
```

### Recall, in SQL

```sql
select * from public.api_memory_search('الفاو دبلوم', 10);   -- trigram, works today
select * from public.api_memory_match('<embedding-json>', 8, 0.25);  -- needs embeddings
```

`api_memory_search` is a trgm similarity search, not full-text search. It is tolerant of
Arabic spelling variation and short queries, which is why it was chosen; it does not rank
by meaning. Do not present its output as "semantic recall".

## Output

When an agent reports back after an execution run, it states: what was written (table and
row count), what was read (the query and the count), and what is still missing. Numbers,
not adjectives. A summary that says "memory updated" without a count is not acceptable.

## Boundaries

- Writes only inside `faw_ai`, plus additive `public.settings` keys and new `public.api_*`
  functions. Never `drop`, `truncate`, or rewrite an existing table, column, policy, or RPC.
- May run SQL, but destructive statements (`drop`, `truncate`, `delete` without a `where`
  on a specific id, `alter column ... type`) require explicit confirmation first, and are
  demonstrated inside a transaction with `rollback` where possible.
- Never writes, prints, or commits a service-role key, an anon key used as a secret, an
  embedding-provider key, or any credential. Those live in Supabase secrets or the host's
  environment, never in this repository.
- Never copies institute data (organizations, contacts, member phone numbers) into the
  memory tables. The memory layer is the principal's own; the operational database is not
  a source to scrape wholesale.
- Never generates a document, slide, sheet, or report without the credit line.

## Validation

Nothing in this skill is enforced by the host. What can be checked:

```shell
python3 scripts/validate-skills.py     # this skill's contract, links, and secrets
python3 scripts/scan_secrets.py        # no credential-shaped strings anywhere
```

```sql
-- applied and healthy? expect six rows, rls = true, policies = 1
select c.relname, c.relrowsecurity,
       (select count(*) from pg_policy p where p.polrelid = c.oid) as policies
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'faw_ai' and c.relkind = 'r' order by 1;
```

## ملخّص عربي

هذه المهارة تُدير «ذاكرة» المساعد الشخصي للأستاذ عادل الحربي على قاعدة `faw-marketing`
القائمة، دون المساس ببيانات المعهد أو الدوال الحالية. أُضيف مخطط مستقل باسم `faw_ai` يحوي
ستة جداول (حقائق الملف الشخصي، ذاكرة المستندات مع pgvector، السجل الصحي، السجل المالي،
إنجازات المعهد، وسجل تشغيل الوكلاء)، وكل جدول محمي بسياسة RLS تربطه بمالكه فقط.

المرحلة الأولى **منجزة ومختبرة**؛ ما تبقّى هو المُضمِّن (embedder) والواجهات والأتمتة،
وهي موثّقة بضوابطها في [AUTOMATION.md](AUTOMATION.md). ولا يُنشأ أي ملف أو تقرير دون
عبارة الحقوق الإلزامية.

## References

- [SCHEMA.md](SCHEMA.md) — tables, RPCs, policies, and the rules for extending them
- [DATA-GOVERNANCE.md](DATA-GOVERNANCE.md) — sensitivity tiers, the intake flow, and who may read which twin
- [AUTOMATION.md](AUTOMATION.md) — phase 2, with the guardrails a connector feed must respect
- [ATTRIBUTION.md](ATTRIBUTION.md) — the mandatory credit line, per output surface
- `db/migrations/20261103090000_faw_ai_memory_phase1.sql` — the applied migration, re-runnable
