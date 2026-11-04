-- =============================================================================
-- faw_ai: the twin belongs to its SUBJECT, not to the system owner (Phase 1c)
-- Project : faw-marketing (tbvtzuspjcxsidpqknid)
-- Apply   : after 20261104120000_faw_ai_profile_intake.sql. Idempotent.
--
-- WHY
--   `public.is_owner()` resolves to the account with role = 'owner', which in
--   this database is the deputy director — not Adel. The first version of the
--   intake table was readable by `is_owner()` only, which meant the person the
--   data describes could not read, approve, or seed his own profile.
--
--   Correct model:
--     * `subject_user_id` is whose twin this is;
--     * only the subject may read, approve, or seed their own intake;
--     * the system owner gets no read access to the payload. They administer
--       the database and could read it with a service key, but "an admin could
--       technically see it" is not a reason to hand it to them in the product:
--       the intake holds phone, date of birth, and medication.
-- =============================================================================

alter table faw_ai.profile_intake
  add column if not exists subject_user_id uuid references auth.users (id) on delete cascade;

-- Empty at the time of writing; fail loudly rather than leave orphan rows if not.
do $$
begin
  if exists (select 1 from faw_ai.profile_intake where subject_user_id is null) then
    raise exception 'profile_intake has rows without subject_user_id; backfill before setting NOT NULL';
  end if;
end;
$$;

alter table faw_ai.profile_intake
  alter column subject_user_id set not null;

comment on column faw_ai.profile_intake.subject_user_id is
  'Whose twin the payload describes. Only this user may read, approve, or seed it.';

create index if not exists profile_intake_subject_idx
  on faw_ai.profile_intake (subject_user_id, status);

-- ---------------------------------------------------------------------------
-- Policies: the subject always; the system owner read-only
-- ---------------------------------------------------------------------------
drop policy if exists p_profile_intake_owner_read on faw_ai.profile_intake;
drop policy if exists p_profile_intake_owner_write on faw_ai.profile_intake;
drop policy if exists p_profile_intake_read on faw_ai.profile_intake;
drop policy if exists p_profile_intake_decide on faw_ai.profile_intake;

create policy p_profile_intake_read on faw_ai.profile_intake
  for select to authenticated
  using (subject_user_id = auth.uid());

create policy p_profile_intake_decide on faw_ai.profile_intake
  for update to authenticated
  using (subject_user_id = auth.uid())
  with check (subject_user_id = auth.uid());

-- ---------------------------------------------------------------------------
-- Seed: subject-only, writes to the subject's twin
-- ---------------------------------------------------------------------------
create or replace function public.api_profile_seed(p_subject text default 'adel')
returns jsonb
language plpgsql
security invoker
set search_path = public, faw_ai, pg_temp
as $$
declare
  v_intake  faw_ai.profile_intake;
  v_count   integer;
  v_by_cat  jsonb;
  v_secret  integer;
begin
  if auth.uid() is null then
    raise exception 'api_profile_seed requires an authenticated session' using errcode = '42501';
  end if;

  select * into v_intake
  from faw_ai.profile_intake
  where subject = p_subject
    and status = 'approved'
    and subject_user_id = auth.uid()
  order by requested_at desc
  limit 1;

  if not found then
    raise exception 'no approved intake for subject % owned by the caller', p_subject
      using hint = 'The subject must approve first: update faw_ai.profile_intake set status = ''approved'', decided_by = auth.uid(), decided_at = now() where id = ...';
  end if;

  insert into faw_ai.profile_facts
    (owner_id, category, key, value, value_json, source, source_ref,
     confidence, sensitivity, verified_at)
  select v_intake.subject_user_id, f.category, f.key, f.value, f.value_json,
         'manual', 'intake:' || v_intake.id, 1.00, f.sensitivity, now()
  from faw_ai.flatten_profile(v_intake.payload) f
  on conflict (owner_id, category, key) do update
    set value       = excluded.value,
        value_json  = excluded.value_json,
        source      = excluded.source,
        source_ref  = excluded.source_ref,
        confidence  = excluded.confidence,
        sensitivity = excluded.sensitivity,
        verified_at = excluded.verified_at,
        updated_at  = now();

  get diagnostics v_count = row_count;

  -- Counted in a separate statement on purpose: changes made by a data-modifying
  -- CTE are not visible to other parts of the same query, so counting there
  -- reported 0 rows written.
  -- Grouped by category only for the breakdown: aggregating over
  -- (category, sensitivity) collapses to one row per category and silently
  -- under-counts when a category spans two tiers.
  select coalesce(jsonb_object_agg(category, n), '{}'::jsonb)
    into v_by_cat
  from (
    select category, count(*) as n
    from faw_ai.profile_facts
    where owner_id = v_intake.subject_user_id
      and source_ref = 'intake:' || v_intake.id
    group by category
  ) c;

  select count(*) filter (where sensitivity = 'secret') into v_secret
  from faw_ai.profile_facts
  where owner_id = v_intake.subject_user_id
    and source_ref = 'intake:' || v_intake.id;

  insert into faw_ai.agent_runs (owner_id, agent, action, target, status, detail, finished_at)
  values (v_intake.subject_user_id, 'arena', 'profile_seed', 'faw_ai.profile_facts', 'ok',
          jsonb_build_object('intake_id', v_intake.id, 'subject', p_subject,
                             'facts', v_count, 'by_category', v_by_cat,
                             'secret_tier', v_secret),
          now());

  return jsonb_build_object(
    'subject', p_subject,
    'subject_user_id', v_intake.subject_user_id,
    'intake_id', v_intake.id,
    'facts_written', v_count,
    'by_category', coalesce(v_by_cat, '{}'::jsonb),
    'secret_tier', v_secret,
    'attribution', public.api_attribution_footer()
  );
end;
$$;

revoke all on function public.api_profile_seed(text) from public, anon;
grant execute on function public.api_profile_seed(text) to authenticated, service_role;
