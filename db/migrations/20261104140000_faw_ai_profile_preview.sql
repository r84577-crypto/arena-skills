-- =============================================================================
-- faw_ai: safe preview of a staged profile (Phase 1d)
-- Project : faw-marketing (tbvtzuspjcxsidpqknid)
-- Apply   : after 20261104130000_faw_ai_profile_subject.sql. Idempotent.
--
-- WHY
--   Before anything is materialised, the subject should be able to see WHAT is
--   about to be written and at WHICH tier — without the values being echoed
--   back into a screen, a log, or a screenshot. `api_profile_preview` returns
--   the field map with a `present` flag and nothing else.
--
--   The field map also gains the paths the second manifest supplied that the
--   first one did not: where he grew up, the composition of the household, what
--   the CPAP is for, working hours, and the dialect set.
-- =============================================================================

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
      ('identity','full_name',          'identity.full_name',       'personal'),
      ('identity','honorific',          'identity.honorific',       'public'),
      ('identity','date_of_birth',      'identity.dob_gregorian',   'sensitive'),
      ('identity','date_of_birth_hijri','identity.dob_hijri',       'sensitive'),
      ('identity','nationality',        'identity.nationality',     'personal'),
      ('identity','tribe',              'identity.tribe',           'personal'),
      ('identity','home_city',          'identity.city',            'public'),
      ('identity','region',             'identity.region',          'public'),
      ('identity','grew_up_in',         'identity.grew_up_in',      'public'),
      ('identity','family_context',     'identity.family_context',  'personal'),
      ('identity','family_composition', 'identity.family_composition','personal'),
      ('identity','dialects',           'identity.dialects',        'personal'),
      ('identity','handle_x',           'identity.handles.x',       'public'),
      ('identity','handle_threads',     'identity.handles.threads', 'public'),
      ('identity','handle_linkedin',    'identity.handles.linkedin','public'),
      -- contact: a phone number is not "public" just because it was shared
      ('contact','mobile',              'identity.phone',           'sensitive'),
      -- work
      ('work','job_title',              'work.position',            'public'),
      ('work','employer',               'work.employer',            'public'),
      ('work','education',              'work.education',           'public'),
      ('work','contract_pattern',       'work.contract',            'personal'),
      ('work','working_hours',          'work.hours',               'personal'),
      ('work','teaching_subjects',      'work.subjects',            'public'),
      ('work','outreach',               'work.outreach',            'public'),
      -- preferences
      ('preference','gaming',           'interests.gaming',         'public'),
      ('preference','reading',          'interests.reading',        'public'),
      ('preference','devices',          'interests.devices',        'public'),
      -- health: secret by default
      ('health','medication',           'health.medication',        'secret'),
      ('health','condition',            'health.condition',         'secret'),
      ('health','therapy_purpose',      'health.cpap_purpose',      'secret'),
      ('health','vitals_baseline',      'health.vitals',            'secret'),
      ('health','training',             'health.training',          'secret'),
      -- finance: secret
      ('finance','ledger_practice',     'finance.practice',         'secret')
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
-- Preview: shape and tier, never the value
-- ---------------------------------------------------------------------------
create or replace function public.api_profile_preview(p_subject text default 'adel')
returns jsonb
language plpgsql
stable
security invoker
set search_path = public, faw_ai, pg_temp
as $$
declare
  v_intake faw_ai.profile_intake;
  v_fields jsonb;
  v_tiers  jsonb;
begin
  if auth.uid() is null then
    raise exception 'api_profile_preview requires an authenticated session' using errcode = '42501';
  end if;

  select * into v_intake
  from faw_ai.profile_intake
  where subject = p_subject
    and subject_user_id = auth.uid()
    and status in ('pending','approved')
  order by requested_at desc
  limit 1;

  if not found then
    return jsonb_build_object('subject', p_subject, 'status', 'none',
                              'fields', '[]'::jsonb, 'by_tier', '{}'::jsonb);
  end if;

  select coalesce(jsonb_agg(jsonb_build_object(
           'category', f.category,
           'key', f.key,
           'sensitivity', f.sensitivity) order by f.category, f.key), '[]'::jsonb)
    into v_fields
  from faw_ai.flatten_profile(v_intake.payload) f;

  select coalesce(jsonb_object_agg(sensitivity, n), '{}'::jsonb)
    into v_tiers
  from (
    select sensitivity, count(*) as n
    from faw_ai.flatten_profile(v_intake.payload)
    group by sensitivity
  ) c;

  return jsonb_build_object(
    'subject', p_subject,
    'intake_id', v_intake.id,
    'status', v_intake.status,
    'field_count', jsonb_array_length(v_fields),
    'fields', v_fields,
    'by_tier', v_tiers,
    'values_included', false,
    'attribution', public.api_attribution_footer()
  );
end;
$$;

revoke all on function public.api_profile_preview(text) from public, anon;
grant execute on function public.api_profile_preview(text) to authenticated, service_role;
