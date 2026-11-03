# Data governance: how personal data enters, and who can read it

The twin described by this skill includes a phone number, a date of birth, a medical
condition, medication, and financial detail. Treating those like "job title" is the mistake
that turns a helpful assistant into a liability. The rules below are what the schema
actually enforces; where it is only a convention, that is stated.

## The five tiers

| Tier | Examples | In a staff document | In a prompt to a third-party model | In an embedding |
| --- | --- | --- | --- | --- |
| `public` | job title, city, employer, public handles | yes | yes | yes |
| `personal` | full name, tribe, family context | only with the principal's agreement | yes, if the task needs it | yes |
| `sensitive` | phone, date of birth | never | only when the task is about that field | no |
| `secret` | medication, condition, finances | never | never | no |
| — | passwords, keys, OTPs | — | never | never |

The tier is stored next to the value (`profile_facts.sensitivity`), not decided at read time
by whoever writes the query. A field's tier is set in `faw_ai.flatten_profile()`, so the
classification is visible in one function instead of scattered across generators.

## Who is the owner of the twin

Not the account with `role = 'owner'` in `public.profiles`. In this database that account is
the deputy director — the system administrator, not the subject. Ownership is
`faw_ai.profile_intake.subject_user_id`, and every `faw_ai` row is scoped to
`auth.uid()`.

That distinction produced a real defect in the first version of the intake table: it was
readable by `is_owner()`, which meant the deputy could read the health declaration and the
person it describes could not approve it. Fixed in
`20261104130000_faw_ai_profile_subject.sql`; verified by reading the table as each account
in turn (deputy: 0 rows, subject: 1 row).

## How the profile enters

1. **Stage.** A payload goes into `faw_ai.profile_intake` with `subject_user_id` and
   `status = 'pending'`. The template lives at `db/seeds/profile-intake-adel.json` and is
   deliberately missing every sensitive value — those are supplied directly into the
   database, never written to a file that could be committed.
2. **Approve.** The subject sets `status = 'approved'`, `decided_by`, `decided_at`. RLS
   allows nobody else to do it.
3. **Materialise.** `api_profile_seed('adel')` flattens the payload through the field map
   and upserts `profile_facts` with the tier from that map. It runs as the caller, so it can
   only ever write the caller's own facts.
4. **Prove it.** The return value carries `facts_written`, `by_category`, and `secret_tier`.
   A seed that reports zero facts is a failure, not a success — that was a real bug (a
   data-modifying CTE is invisible to the rest of its own query) and it is why the count is
   now taken with `get diagnostics`.

## What this repository must never contain

- A phone number, national ID, date of birth, diagnosis, or medication name — in a seed
  file, a skill document, a test fixture, or a commit message. `scripts/scan_secrets.py`
  catches tokens, not personal data; that is a review rule, not a scanner rule.
- A row of institute data (organizations, member phone numbers) copied into a fixture.
- An API key, service-role key, or embedding-provider key.

The staging payload for the first principal was entered directly into the database by the
agent during the build, and the repository holds only the redacted template. The intake row
is not approved: approval is the principal's decision, not the agent's.

## Retention and deletion

- Deleting the subject's `auth.users` row cascades through every `faw_ai` table. There is no
  soft-delete layer to unwind, which is on purpose: a "deleted" twin that still exists in
  three tables is not deleted.
- `agent_runs.owner_id` is `on delete set null`, so the audit trail survives a user
  deletion without keeping the link. If the trail itself must not survive, delete those rows
  in the same transaction.
- Nothing in the memory layer is referenced by `public.*` except
  `institute_milestones.org_id`, which is `on delete set null` — so the operational system
  can be cleaned up without breaking memory, and memory can be dropped without breaking the
  institute.

## Access review, as a query

```sql
-- who can read which twin
select c.relname as table, p.polname as policy, pg_get_expr(p.polqual, p.polrelid) as using_expr
from pg_policy p join pg_class c on c.oid = p.polrelid
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'faw_ai' order by 1;
```

If the `using_expr` is anything other than `owner_id = auth.uid()` (or
`subject_user_id = auth.uid()` for the intake table), somebody widened access and owes an
explanation in the commit that did it.

## The Arabic note that belongs in every review

بيانات الأستاذ عادل الحربي — ومنها رقم الجوال وتاريخ الميلاد والدواء وحالة النوم والبيانات
المالية — لا تُكتب في ملفات المستودع، ولا تُرسل إلى خدمة خارجية إلا عند الحاجة الفعلية،
ولا تُضمَّن في أي مستند يُوزَّع على منسوبي المعهد. صلاحية القراءة محصورة بصاحب البيانات،
والموافقة على الإدخال قراره هو، لا قرار النظام ولا قرار الوكيل.
