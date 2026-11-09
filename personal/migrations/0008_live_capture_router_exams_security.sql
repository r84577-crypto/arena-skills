-- =============================================================================
-- personal/0008_live_capture_router_exams_security.sql
--
-- Live-state capture, reverse-engineered from project hkgdtybmlrgbvakjgrxl on
-- 2026-11-09 (pg_get_functiondef / information_schema / pg_policies /
-- pg_constraint / proacl). Everything here already runs on live; this file
-- makes the repository say the same thing the database does.
--
-- IDEMPOTENT: every section is safe to re-apply on live (CREATE OR REPLACE,
-- IF NOT EXISTS, DROP POLICY/TRIGGER IF EXISTS). The one deliberate
-- difference from live is documented in section 3 (hardened gate ACLs).
--
-- FRESH-DB ORDER: sections 1-3 and 5-7 apply on any DB with 0001-0003 plus
-- the training/aon_app base tables (see personal/LIVE-DIVERGENCE-2026-11-09.md
-- for the base-table register). Section 8 (sovereign_status) additionally
-- needs personal.entities, personal.entity_edges, personal.routines,
-- personal.sync_runs and personal.embedding_probes; on a fresh DB apply the
-- base capture first or that section fails loudly at CREATE time — by design.
--
-- Section 9 re-creates the nightly cron job (same name, same schedule 2:40 AM
-- Asia/Riyadh wall-clock via pg_cron); re-applying deletes and re-creates it
-- so the job is never duplicated.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. personal.context_decisions — the router's audit log (was empty until the
--    router was driven with real identities; now every decision lands here)
-- ---------------------------------------------------------------------------
create table if not exists personal.context_decisions (
  id         bigserial constraint context_decisions_pkey primary key,
  actor      uuid,
  email      text,
  scope      text not null,
  granted    boolean not null,
  schema_used text,
  reason     text not null,
  created_at timestamptz not null default now()
);

alter table personal.context_decisions enable row level security;

drop policy if exists p_ctx_dec_owner_read on personal.context_decisions;
create policy p_ctx_dec_owner_read on personal.context_decisions
  for select to authenticated
  using (exists (select 1 from personal.principal where user_id = auth.uid()));

-- Assumption (grants were never captured live; this matches the policy intent):
-- the principal reads his own audit trail through PostgREST, nobody else.
revoke all on personal.context_decisions from public, anon;
grant select on personal.context_decisions to authenticated;
grant all on personal.context_decisions to service_role;

-- ---------------------------------------------------------------------------
-- 2. The permission router: resolve_scope (pure decision, STABLE, writes
--    nothing) + route (the logging gateway, the ONLY writer of decisions)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION personal.resolve_scope(p_scope text)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'personal', 'training', 'pg_temp'
AS $function$
declare
  v_scope text := upper(btrim(coalesce(p_scope,'')));
  v_uid   uuid := auth.uid();
  v_email text := coalesce(auth.jwt() ->> 'email', '');
  v_is_owner boolean;
  v_is_trainer boolean;
begin
  v_is_owner := exists (select 1 from personal.principal where user_id = v_uid);
  v_is_trainer := exists (select 1 from training.instructors i
                          where i.user_id = v_uid and i.active and i.revoked_at is null);

  return case v_scope
    when 'PERSONAL' then
      case
        when v_is_owner and v_email = 'r84577@gmail.com' then
          jsonb_build_object('scope','PERSONAL','granted',true,'schema','personal',
            'title','المجال الشخصي السيادي','reason','مالك مطابق بالهوية والبريد')
        when v_is_owner then
          jsonb_build_object('scope','PERSONAL','granted',false,'schema',null,
            'title','المجال الشخصي السيادي','reason','مالك بلا بريد مطابق — رُفض احتياطاً')
        else
          jsonb_build_object('scope','PERSONAL','granted',false,'schema',null,
            'title','المجال الشخصي السيادي','reason','ليس المالك')
      end
    when 'TRAINING' then
      case
        when v_is_trainer then
          jsonb_build_object('scope','TRAINING','granted',true,'schema','training',
            'title','وحدة تدريب الحاسب','reason','مصرّح في قائمة المدرّبين')
        else
          jsonb_build_object('scope','TRAINING','granted',false,'schema',null,
            'title','وحدة تدريب الحاسب','reason','غير مصرّح — لا يوجد صف في training.instructors')
      end
    when 'AON' then
      case
        when auth.role() = 'service_role' then
          jsonb_build_object('scope','AON','granted',true,'schema','aon_app',
            'title','تطبيقات عون المستقلة','reason','service_role فقط — لا وصول بشري')
        else
          jsonb_build_object('scope','AON','granted',false,'schema',null,
            'title','تطبيقات عون المستقلة','reason','M2M فقط — الوصول البشري ممنوع بالتصميم')
      end
    else
      jsonb_build_object('scope',v_scope,'granted',false,'schema',null,
        'title',null,'reason','نطاق غير معروف — رُفض بدل التخمين')
  end;
end;
$function$;

CREATE OR REPLACE FUNCTION personal.route(p_scope text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'personal', 'pg_temp'
AS $function$
declare v_res jsonb;
begin
  v_res := personal.resolve_scope(p_scope);
  insert into personal.context_decisions (actor, email, scope, granted, schema_used, reason)
  values (auth.uid(), auth.jwt() ->> 'email', v_res->>'scope',
          (v_res->>'granted')::boolean, v_res->>'schema', v_res->>'reason');
  return v_res;
end;
$function$;

revoke all on function personal.resolve_scope(text) from public, anon;
revoke all on function personal.route(text) from public, anon;
grant execute on function personal.resolve_scope(text) to authenticated, service_role;
grant execute on function personal.route(text) to authenticated, service_role;

-- ---------------------------------------------------------------------------
-- 3. training.can_read / can_write — the boolean gates behind every training
--    RLS policy. Bodies are exact live captures.
--
--    DELIBERATE DIFFERENCE: live carries the default ACL (EXECUTE to PUBLIC,
--    proacl NULL). That is harmless for anon (both return false without a
--    session) but it is surface without purpose, so this file — and the live
--    database, hardened in the same change — revokes PUBLIC/anon and grants
--    authenticated + service_role. All legitimate flows are unchanged:
--    policies evaluate for authenticated callers, service_role bypasses RLS.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION training.can_read()
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'training', 'pg_temp'
AS $function$
  select exists (
    select 1 from training.instructors i
    where i.user_id = auth.uid() and i.active and i.revoked_at is null
  );
$function$;

CREATE OR REPLACE FUNCTION training.can_write()
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'training', 'pg_temp'
AS $function$
  select exists (
    select 1 from training.instructors i
    where i.user_id = auth.uid() and i.active and i.revoked_at is null
      and i.role in ('owner','instructor','committee')
  );
$function$;

revoke all on function training.can_read() from public, anon;
revoke all on function training.can_write() from public, anon;
grant execute on function training.can_read() to authenticated, service_role;
grant execute on function training.can_write() to authenticated, service_role;

-- ---------------------------------------------------------------------------
-- 4. training.exams + training.exam_results — constraint names match the live
--    catalog exactly, so fresh DBs and live stay comparable.
-- ---------------------------------------------------------------------------
create table if not exists training.exams (
  id           uuid primary key default gen_random_uuid(),
  course_id    uuid not null constraint exams_course_id_fkey
                 references training.courses (id) on delete cascade,
  created_by   uuid not null constraint exams_created_by_fkey
                 references auth.users (id),
  title        text not null,
  kind         text not null default 'theory'
                 constraint exams_kind_check check (kind in ('theory','practical','final')),
  max_score    numeric(5,2) not null default 100
                 constraint exams_max_score_check check (max_score > 0),
  pass_score   numeric(5,2) not null default 60
                 constraint exams_pass_score_check check (pass_score >= 0),
  scheduled_on date,
  status       text not null default 'draft'
                 constraint exams_status_check check (status in ('draft','open','closed')),
  created_at   timestamptz not null default now(),
  constraint exams_check check (pass_score <= max_score)
);

create table if not exists training.exam_results (
  id            uuid primary key default gen_random_uuid(),
  exam_id       uuid not null constraint exam_results_exam_id_fkey
                  references training.exams (id) on delete cascade,
  enrollment_id uuid not null constraint exam_results_enrollment_id_fkey
                  references training.enrollments (id) on delete cascade,
  score         numeric(5,2),
  passed        boolean,
  graded_by     uuid constraint exam_results_graded_by_fkey
                  references auth.users (id),
  graded_at     timestamptz,
  notes         text,
  constraint exam_results_exam_id_enrollment_id_key unique (exam_id, enrollment_id)
);

alter table training.exams enable row level security;
alter table training.exam_results enable row level security;

drop policy if exists t_exams_read on training.exams;
drop policy if exists t_exams_write on training.exams;
drop policy if exists t_results_read on training.exam_results;
drop policy if exists t_results_write on training.exam_results;

create policy t_exams_read on training.exams
  for select to authenticated using (training.can_read());
create policy t_exams_write on training.exams
  for all to authenticated using (training.can_write()) with check (training.can_write());
create policy t_results_read on training.exam_results
  for select to authenticated using (training.can_read());
create policy t_results_write on training.exam_results
  for all to authenticated using (training.can_write()) with check (training.can_write());

-- Policies filter rows; privileges open the door. Shipping one without the
-- other produced a live 42501 once — never again.
revoke all on training.exams, training.exam_results from public, anon;
grant select, insert, update, delete on training.exams, training.exam_results to authenticated;
grant all on training.exams, training.exam_results to service_role;

-- ---------------------------------------------------------------------------
-- 5. Auto-grading trigger: passed/graded_at are COMPUTED, never typed.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION training.t_grade_result()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'training', 'pg_temp'
AS $function$
declare v_pass numeric;
begin
  select e.pass_score into v_pass from training.exams e where e.id = new.exam_id;
  if new.score is null then
    new.passed := null;
    new.graded_at := null;
  else
    new.passed := new.score >= v_pass;
    new.graded_at := coalesce(new.graded_at, now());
  end if;
  return new;
end;
$function$;

-- Trigger functions keep the default ACL (they are never called directly).
drop trigger if exists trg_grade_result on training.exam_results;
CREATE TRIGGER trg_grade_result BEFORE INSERT OR UPDATE OF score ON training.exam_results FOR EACH ROW EXECUTE FUNCTION training.t_grade_result();

-- ---------------------------------------------------------------------------
-- 6. public.security_audit — the nightly sweep's ledger. RLS on, zero
--    policies, zero grants outside postgres/service_role: only the
--    security-definer sweep writes here, and only service_role reads it.
-- ---------------------------------------------------------------------------
create table if not exists public.security_audit (
  id       bigserial constraint security_audit_pkey primary key,
  run_at   timestamptz not null default now(),
  matrix   jsonb not null,
  verdict  text not null constraint security_audit_verdict_check check (verdict in ('clean','drift')),
  drift    jsonb not null default '[]'::jsonb
);

alter table public.security_audit enable row level security;
revoke all on public.security_audit from public, anon, authenticated;
grant all on public.security_audit to service_role;

-- ---------------------------------------------------------------------------
-- 7. public.isolation_matrix + public.security_sweep — exact live bodies,
--    including the Arabic comment that records how the \m / \b traps were
--    found (a zero from a broken regex is worse than no check at all).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.isolation_matrix()
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'personal', 'training', 'aon_app', 'pg_temp'
AS $function$
  with tables as (
    select table_schema, table_name
    from information_schema.tables
    where table_schema in ('personal','training','aon_app')
      and table_type = 'BASE TABLE'
  ),
  -- سجّل الأخطاء في هذا الفحص، لأن كل خطأ منه أنتج صفراً كاذباً:
  --   1) '\m' بعد اسم الجدول  → تُطابق بداية كلمة، فلا تُطابق شيئاً.
  --   2) '\b' في Postgres       → حرف الرجوع (0x08)، لا حدّ الكلمة.
  --   3) جمع عدّ الجداول        → يوسم دوال النطاق الواحد كعيوب.
  -- الصحيح: '\M' + عدّ المخططات، لا الجداول.
  scored as (
    select p.proname, n.nspname as home,
      (exists (select 1 from tables t where t.table_schema='personal'
         and p.prosrc ~ ('personal\s*\.\s*' || t.table_name || '\M')))::int
    + (exists (select 1 from tables t where t.table_schema='training'
         and p.prosrc ~ ('training\s*\.\s*' || t.table_name || '\M')))::int
    + (exists (select 1 from tables t where t.table_schema='aon_app'
         and p.prosrc ~ ('aon_app\s*\.\s*' || t.table_name || '\M')))::int as schemas_touched
    from pg_proc p join pg_namespace n on n.oid = p.pronamespace
    where n.nspname in ('personal','training','aon_app')
  ),
  leaks as (select proname, home from scored where schemas_touched > 1)
  select jsonb_build_object(
    'schemas', jsonb_build_object(
      'personal', (select count(*) from tables where table_schema='personal'),
      'training', (select count(*) from tables where table_schema='training'),
      'aon_app',  (select count(*) from tables where table_schema='aon_app')),
    'rls_gaps', (select count(*) from pg_tables
                  where schemaname in ('personal','training','aon_app') and not rowsecurity),
    'anon_schema_usage', (select count(*) from pg_namespace n
                  where n.nspname in ('personal','training','aon_app')
                    and has_schema_privilege('anon', n.oid, 'USAGE')),
    'anon_rpc_surface', (select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace
                  where n.nspname='public'
                    and has_function_privilege('anon', p.oid, 'EXECUTE')),
    'data_leaks', (select count(*) from leaks),
    'leak_names', coalesce((select jsonb_agg(proname) from leaks), '[]'::jsonb),
    'permission_router', (select count(*) from scored where proname='resolve_scope'),
    'scanned_tables', (select count(*) from tables),
    'scanned_functions', (select count(*) from scored),
    'checked_at', now()
  );
$function$;

CREATE OR REPLACE FUNCTION public.security_sweep()
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public', 'personal', 'training', 'aon_app', 'pg_temp'
AS $function$
declare
  v_m jsonb; v_drift jsonb := '[]'::jsonb; v_verdict text;
begin
  v_m := public.isolation_matrix();

  if (v_m->>'anon_schema_usage')::int > 0 then
    v_drift := v_drift || jsonb_build_object('kind','anon_schema','value',v_m->'anon_schema_usage');
  end if;
  if (v_m->>'anon_rpc_surface')::int > 0 then
    v_drift := v_drift || jsonb_build_object('kind','anon_rpc','value',v_m->'anon_rpc_surface');
  end if;
  if (v_m->>'rls_gaps')::int > 0 then
    v_drift := v_drift || jsonb_build_object('kind','rls_gap','value',v_m->'rls_gaps');
  end if;
  -- العبور المسموح الوحيد هو الموجّه؛ أي اسم آخر في القائمة انحراف.
  if exists (
    select 1 from jsonb_array_elements_text(v_m->'leak_names') n
    where n.value <> 'resolve_scope'
  ) then
    v_drift := v_drift || jsonb_build_object('kind','unexpected_leak','value',v_m->'leak_names');
  end if;
  if (v_m->>'permission_router')::int <> 1 then
    v_drift := v_drift || jsonb_build_object('kind','router_missing','value',v_m->'permission_router');
  end if;

  v_verdict := case when jsonb_array_length(v_drift) = 0 then 'clean' else 'drift' end;

  insert into public.security_audit (matrix, verdict, drift) values (v_m, v_verdict, v_drift);

  return jsonb_build_object('verdict', v_verdict, 'drift', v_drift, 'matrix', v_m);
end;
$function$;

revoke all on function public.isolation_matrix() from public, anon;
revoke all on function public.security_sweep() from public, anon, authenticated;
grant execute on function public.isolation_matrix() to authenticated, service_role;
grant execute on function public.security_sweep() to service_role;

-- ---------------------------------------------------------------------------
-- 8. public.sovereign_status — the single function the dashboard reads.
--    Anonymous-readable counters were a leak: anon EXECUTE stays revoked.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.sovereign_status()
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'personal', 'training', 'public', 'pg_temp'
AS $function$
  select jsonb_build_object(
    'facts', (select count(*) from personal.facts),
    'memory', (select count(*) from personal.memory),
    'memory_embedded', (select count(*) from personal.memory where embedding is not null),
    'entities', (select count(*) from personal.entities),
    'edges', (select count(*) from personal.entity_edges),
    'health_logs', (select count(*) from personal.health_logs),
    'routines', (select count(*) from personal.routines where active),
    'milestones', (select count(*) from personal.milestones),
    'sync_ok', (select count(*) from personal.sync_runs where status='ok'),
    'sync_failed', (select count(*) from personal.sync_runs where status='failed'),
    'training_courses', (select count(*) from training.courses),
    'training_visits', (select count(*) from training.visits),
    'probes', (select count(*) from personal.embedding_probes),
    'router_decisions', (select count(*) from personal.context_decisions),
    'security_verdict', (select verdict from public.security_audit order by id desc limit 1),
    'last_sync', (select max(ran_at) from personal.sync_runs),
    'generated_at', now()
  );
$function$;

revoke all on function public.sovereign_status() from public, anon;
grant execute on function public.sovereign_status() to authenticated, service_role;

-- ---------------------------------------------------------------------------
-- 9. Nightly schedule. Delete-then-create keeps re-application idempotent:
--    the job keeps its name and schedule, never duplicates.
-- ---------------------------------------------------------------------------
delete from cron.job where jobname = 'security_sweep_nightly';
select cron.schedule('security_sweep_nightly', '40 2 * * *', $$select public.security_sweep()$$);
