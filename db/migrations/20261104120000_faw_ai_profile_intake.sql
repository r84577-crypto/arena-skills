-- =============================================================================
-- faw_ai profile intake + sensitivity tiers (Phase 1b)
-- Project : faw-marketing (tbvtzuspjcxsidpqknid)
-- Apply   : after 20261103090000_faw_ai_memory_phase1.sql. Idempotent.
--
-- WHY THIS FILE EXISTS
--   The manifest profile contains a phone number, a date of birth, a medication,
--   a medical condition, and financial details. Those are not the same kind of
--   data as "job title", and a single `sensitivity` default is not enough.
--   So: the profile enters through an intake table, a human approves it, and the
--   materialised facts carry a per-field tier that decides who may read them and
--   whether they may ever leave the database.
--
--   Nothing is materialised into `profile_facts` until `api_profile_seed` is
--   called with an approved intake row. The intake payload itself is readable
--   only by the owner.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Intake table — the staging area, not the twin
-- ---------------------------------------------------------------------------
create table if not exists faw_ai.profile_intake (
  id            uuid primary key default gen_random_uuid(),
  subject       text not null,
  payload       jsonb not null,
  status        text not null default 'pending'
                  check (status in ('pending','approved','rejected','superseded')),
  requested_by  uuid references auth.users (id) on delete set null,
  requested_at  timestamptz not null default now(),
  decided_by    uuid references auth.users (id) on delete set null,
  decided_at    timestamptz,
  decision_note text,
  constraint profile_intake_one_pending_per_subject
    unique (subject, status) deferrable initially deferred
);

comment on table faw_ai.profile_intake is
  'Staging for a profile that was pasted into a conversation. Readable by the owner only. Materialised into profile_facts by api_profile_seed(), only after status = approved.';

alter table faw_ai.profile_intake enable row level security;

drop policy if exists p_profile_intake_owner_read on faw_ai.profile_intake;
create policy p_profile_intake_owner_read on faw_ai.profile_intake
  for select to authenticated
  using (public.is_owner());

drop policy if exists p_profile_intake_owner_write on faw_ai.profile_intake;
create policy p_profile_intake_owner_write on faw_ai.profile_intake
  for update to authenticated
  using (public.is_owner()) with check (public.is_owner());

revoke all on faw_ai.profile_intake from anon, public;
grant select, update on faw_ai.profile_intake to authenticated;
grant all on faw_ai.profile_intake to service_role;

-- ---------------------------------------------------------------------------
-- 2. Field map: path in the payload -> category / key / sensitivity tier
--
--    Tiers, and what each one permits:
--      public    — may appear in a staff-facing document
--      personal  — the principal's own; never in a staff document without asking
--      sensitive — never leaves the database except to the principal; never in a
--                  prompt sent to a third-party model
--      secret    — health and money; never embedded, never quoted, never exported
-- ---------------------------------------------------------------------------
create or replace function faw_ai.flatten_profile(p_payload jsonb)
returns table (
  category    text,
  key         text,
  value       text,
  value_json  jsonb,
  sensitivity text
)
language sql
immutable
set search_path = faw_ai, pg_temp
as $$
  with field_map (category, key, path, sensitivity) as (
    values
      -- identity
      ('identity','full_name',        'identity.full_name',        'personal'),
      ('identity','honorific',        'identity.honorific',        'public'),
      ('identity','date_of_birth',    'identity.dob_gregorian',    'sensitive'),
      ('identity','date_of_birth_hijri','identity.dob_hijri',      'sensitive'),
      ('identity','nationality',      'identity.nationality',      'personal'),
      ('identity','tribe',            'identity.tribe',            'personal'),
      ('identity','home_city',        'identity.city',             'public'),
      ('identity','region',           'identity.region',           'public'),
      ('identity','family_context',   'identity.family_context',   'personal'),
      ('identity','handle_x',         'identity.handles.x',        'public'),
      ('identity','handle_threads',   'identity.handles.threads',  'public'),
      ('identity','handle_linkedin',  'identity.handles.linkedin', 'public'),
      -- contact: a phone number is not "public" just because it was shared
      ('contact','mobile',            'identity.phone',            'sensitive'),
      -- work
      ('work','job_title',            'work.position',             'public'),
      ('work','employer',             'work.employer',             'public'),
      ('work','education',            'work.education',            'public'),
      ('work','contract_pattern',     'work.contract',             'personal'),
      ('work','teaching_subjects',    'work.subjects',             'public'),
      ('work','outreach',             'work.outreach',             'public'),
      -- preferences
      ('preference','gaming',         'interests.gaming',          'public'),
      ('preference','reading',        'interests.reading',         'public'),
      ('preference','devices',        'interests.devices',         'public'),
      -- health: secret by default; the principal decides otherwise, per query
      ('health','medication',         'health.medication',         'secret'),
      ('health','condition',          'health.condition',          'secret'),
      ('health','vitals_baseline',    'health.vitals',             'secret'),
      ('health','training',           'health.training',           'secret'),
      -- finance: secret
      ('finance','ledger_practice',   'finance.practice',          'secret')
  )
  select m.category,
         m.key,
         case when jsonb_typeof(v.val) = 'string'
              then v.val #>> '{}'
              else v.val::text end as value,
         v.val as value_json,
         m.sensitivity
  from field_map m
  cross join lateral (
    select p_payload #> string_to_array(m.path, '.') as val
  ) v
  where v.val is not null
    and jsonb_typeof(v.val) <> 'null';
$$;

-- ---------------------------------------------------------------------------
-- 3. Materialise an approved intake into profile_facts (owner only)
-- ---------------------------------------------------------------------------
create or replace function public.api_profile_seed(p_subject text default 'adel')
returns jsonb
language plpgsql
security invoker
set search_path = public, faw_ai, pg_temp
as $$
declare
  v_owner    uuid := auth.uid();
  v_intake   faw_ai.profile_intake;
  v_count    integer;
  v_by_cat   jsonb;
begin
  if v_owner is null or not public.is_owner() then
    raise exception 'api_profile_seed is owner-only' using errcode = '42501';
  end if;

  select * into v_intake
  from faw_ai.profile_intake
  where subject = p_subject and status = 'approved'
  order by requested_at desc
  limit 1;

  if not found then
    raise exception 'no approved intake for subject %', p_subject
      using hint = 'Approve the pending row first: update faw_ai.profile_intake set status = ''approved'', decided_by = auth.uid(), decided_at = now() where id = ...';
  end if;

  with fields as (
    select * from faw_ai.flatten_profile(v_intake.payload)
  ), upserted as (
    insert into faw_ai.profile_facts
      (owner_id, category, key, value, value_json, source, source_ref,
       confidence, sensitivity, verified_at)
    select v_owner, f.category, f.key, f.value, f.value_json,
           'manual', 'intake:' || v_intake.id, 1.00, f.sensitivity, now()
    from fields f
    on conflict (owner_id, category, key) do update
      set value       = excluded.value,
          value_json  = excluded.value_json,
          source      = excluded.source,
          source_ref  = excluded.source_ref,
          confidence  = excluded.confidence,
          sensitivity = excluded.sensitivity,
          verified_at = excluded.verified_at,
          updated_at  = now()
    returning 1
  )
  select count(*), jsonb_object_agg(category, n) into v_count, v_by_cat
  from (
    select category, count(*) as n
    from faw_ai.profile_facts
    where owner_id = v_owner
      and source_ref = 'intake:' || v_intake.id
    group by category
  ) c;

  insert into faw_ai.agent_runs (owner_id, agent, action, target, status, detail, finished_at)
  values (v_owner, 'arena', 'profile_seed', 'faw_ai.profile_facts', 'ok',
          jsonb_build_object('intake_id', v_intake.id, 'subject', p_subject,
                             'facts', v_count, 'by_category', v_by_cat),
          now());

  return jsonb_build_object(
    'subject', p_subject,
    'intake_id', v_intake.id,
    'facts_written', v_count,
    'by_category', coalesce(v_by_cat, '{}'::jsonb),
    'attribution', public.api_attribution_footer()
  );
end;
$$;

-- ---------------------------------------------------------------------------
-- 4. A staff-safe brief. Deliberately boring: no phone, no birth date,
--    no health, no money. Staff need to know whose twin they are NOT seeing.
-- ---------------------------------------------------------------------------
create or replace function public.api_profile_brief()
returns jsonb
language sql
stable
security invoker
set search_path = public, faw_ai, pg_temp
as $$
  select jsonb_build_object(
    'principal', (
      select jsonb_build_object('full_name', p.full_name, 'job_title', p.job_title, 'role', p.role)
      from public.profiles p where p.role = 'owner' order by p.created_at limit 1
    ),
    'caller_own_facts', coalesce((
      select jsonb_object_agg(category, n)
      from (select category, count(*) as n from faw_ai.profile_facts
            where owner_id = auth.uid() group by category) c
    ), '{}'::jsonb),
    'note', 'Twin data is owner-scoped. Supervisors cannot read it, by design.',
    'attribution', public.api_attribution_footer()
  );
$$;

revoke all on function public.api_profile_seed(text) from public, anon;
revoke all on function public.api_profile_brief() from public, anon;
grant execute on function public.api_profile_seed(text) to authenticated, service_role;
grant execute on function public.api_profile_brief() to authenticated, service_role;
