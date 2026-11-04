-- =============================================================================
-- faw_ai: the morning digest (Open-Mesh, phase 3a)
-- Project : faw-marketing (tbvtzuspjcxsidpqknid)
-- Apply   : after 20261104150000_faw_ai_webhook_intake.sql. Idempotent.
--
-- WHAT
--   One notification per morning, not one per item. It reads what the institute's
--   own tables already know — overdue periodic reports, overdue tasks, pending
--   approvals — and writes a single row to `public.notifications`, which the
--   existing app already renders. No new delivery channel was invented.
--
-- WHY ONE ROW AND NOT A LIST
--   A digest that fires five separate notifications trains the reader to ignore
--   all five. One row is a decision to make; five are noise.
--
-- DUPLICATE PROTECTION
--   The deterministic id `auto_digest_<date>` plus an advisory lock. A retried
--   cron run cannot produce a second digest, and two concurrent runs cannot race.
--
-- WHAT IT DELIBERATELY DOES NOT INCLUDE
--   Medication, CPAP, workouts, and money. Those live in `faw_ai` under
--   `sensitivity = 'secret'`, and a row in `public.notifications` is readable by
--   the whole staff. A pill reminder must not become visible to a colleague's
--   screen. Health nudges get their own private channel, later, on purpose.
-- =============================================================================

create or replace function faw_private.owner_id()
returns uuid
language sql
stable
security definer
set search_path = public, pg_temp
as $$
  select id from public.profiles
  where role = 'owner' and status = 'active'
  order by created_at
  limit 1;
$$;

revoke all on function faw_private.owner_id() from public, anon, authenticated;

create or replace function faw_private.morning_digest()
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_owner    uuid := faw_private.owner_id();
  v_today    date := (now() at time zone 'Asia/Riyadh')::date;
  v_id       text := 'auto_digest_' || v_today::text;
  v_reports  integer;
  v_tasks    integer;
  v_pending  integer;
  v_already  boolean;
  v_body     text;
begin
  if v_owner is null then
    return jsonb_build_object('ok', false, 'reason', 'no_active_owner');
  end if;

  perform pg_advisory_xact_lock(hashtext('faw_digest_' || v_today::text));

  select exists (select 1 from public.notifications where id = v_id) into v_already;
  if v_already then
    return jsonb_build_object('ok', true, 'skipped', 'already_sent_today', 'id', v_id);
  end if;

  select count(*) into v_reports
  from public.periodic_reports
  where status in ('due', 'in_progress')
    and nullif(left(due_at, 10), '')::date < v_today;

  select count(*) into v_tasks
  from public.tasks
  where status not in ('done', 'cancelled', 'archived')
    and nullif(left(due_at, 10), '')::date < v_today;

  select count(*) into v_pending
  from public.profiles
  where status = 'pending';

  if v_reports + v_tasks + v_pending = 0 then
    return jsonb_build_object('ok', true, 'skipped', 'nothing_to_report', 'id', null);
  end if;

  v_body := concat_ws(' · ',
    case when v_reports > 0 then v_reports || ' تقرير دوري مستحق' end,
    case when v_tasks   > 0 then v_tasks   || ' مهمة متأخرة' end,
    case when v_pending > 0 then v_pending || ' حساب بانتظار الاعتماد' end);

  insert into public.notifications (id, user_id, type, title, body, entity_type, entity_id)
  values (v_id, v_owner, 'digest.morning', 'ملخّص الصباح', v_body, 'digest', v_id);

  insert into faw_ai.agent_runs (owner_id, agent, action, target, status, detail, finished_at)
  values (v_owner, 'cron', 'morning_digest', 'public.notifications', 'ok',
          jsonb_build_object('reports', v_reports, 'tasks', v_tasks,
                             'pending_accounts', v_pending, 'notification_id', v_id),
          now());

  return jsonb_build_object('ok', true, 'id', v_id, 'reports', v_reports,
                            'tasks', v_tasks, 'pending_accounts', v_pending);
end;
$$;

revoke all on function faw_private.morning_digest() from public, anon, authenticated;
grant execute on function faw_private.morning_digest() to service_role;

-- 05:15 UTC is 08:15 in Riyadh: after the 05:00 UTC periodic job, before the
-- working day starts. The existing jobs run at 01:00 and 05:00 UTC.
select cron.schedule('faw_morning_digest', '15 5 * * *',
                     $$select faw_private.morning_digest();$$);
