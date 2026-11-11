-- توحيد ملحمة دفتر المراسلة: comms_log + security_audit + is_owner +
-- sovereign_status + security_sweep + التقسية (سحب anon).
--
-- كانت هذه الكائنات مطبقة مباشرة على القاعدة الحية؛ هذا الملف يعيد
-- بناءها من الصفر بشكل آمن التكرار — تشغيله على القاعدة الحية
-- لا يغيّر شيئاً (IF NOT EXISTS / OR REPLACE / DROP IF EXISTS).
--
-- الترتيب: مخططات المرحلة 1 (personal/training/aon_app) أولاً، ثم هذا
-- الملف — فالدوال تستعلم تلك المخططات. انظر docs/database-dr.md.

-- ======================= دفتر المراسلة =======================
create table if not exists public.comms_log (
  id bigint generated always as identity primary key,
  actor uuid,
  channel text,
  scope text,
  to_addr text,
  subject text,
  body text,
  status text not null default 'queued',
  reason text,
  provider_ref text,
  sent_at timestamptz,
  created_at timestamptz not null default now()
);

do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'comms_log_channel_check') then
    alter table public.comms_log add constraint comms_log_channel_check
      check (channel = any (array['email'::text, 'whatsapp'::text]));
  end if;
  if not exists (select 1 from pg_constraint where conname = 'comms_log_scope_check') then
    alter table public.comms_log add constraint comms_log_scope_check
      check (scope = any (array['PERSONAL'::text, 'TRAINING'::text, 'AON'::text]));
  end if;
  if not exists (select 1 from pg_constraint where conname = 'comms_log_status_check') then
    alter table public.comms_log add constraint comms_log_status_check
      check (status = any (array['queued'::text, 'sent'::text, 'blocked'::text, 'failed'::text, 'not_configured'::text]));
  end if;
  if not exists (select 1 from pg_constraint where conname = 'comms_log_body_check') then
    alter table public.comms_log add constraint comms_log_body_check
      check (char_length(body) >= 1 and char_length(body) <= 4000);
  end if;
  if not exists (select 1 from pg_constraint where conname = 'comms_log_to_check') then
    alter table public.comms_log add constraint comms_log_to_check
      check (char_length(to_addr) >= 3 and char_length(to_addr) <= 320);
  end if;
  -- بوابة الواتساب: أي صف واتساب لغير رقم المالك مرفوض من القاعدة نفسها.
  if not exists (select 1 from pg_constraint where conname = 'comms_log_whatsapp_gate_check') then
    alter table public.comms_log add constraint comms_log_whatsapp_gate_check
      check (channel <> 'whatsapp'::text or to_addr = '966508247153'::text);
  end if;
end $$;

alter table public.comms_log enable row level security;

drop policy if exists p_comms_owner_all on public.comms_log;
create policy p_comms_owner_all
  on public.comms_log
  for all
  to authenticated
  using ((actor = auth.uid()) and personal.is_principal())
  with check ((actor = auth.uid()) and personal.is_principal());

-- ======================= سجل التدقيق =======================
-- RLS مفعّل بلا سياسات = رفض شامل (service_role يتجاوز). الكتابة من
-- security_sweep (SECURITY DEFINER) فقط، والقراءة للمالك عبر الدوال.
create table if not exists public.security_audit (
  id bigint generated always as identity primary key,
  run_at timestamptz not null default now(),
  verdict text check (verdict = any (array['clean'::text, 'drift'::text])),
  matrix jsonb,
  drift jsonb not null default '[]'::jsonb
);

alter table public.security_audit enable row level security;

-- ======================= غلاف المالكية =======================
create or replace function public.is_owner()
returns boolean
language sql
stable security definer
set search_path to 'personal', 'pg_temp'
as $function$
  select personal.is_principal();
$function$;

revoke all on function public.is_owner() from public, anon, authenticated;
grant execute on function public.is_owner() to authenticated, service_role;

-- ======================= حالة السيادة (للقراءة) =======================
create or replace function public.sovereign_status()
returns jsonb
language sql
stable security definer
set search_path to 'personal', 'training', 'public', 'pg_temp'
as $function$
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
    'comms_queued', (select count(*) from public.comms_log where status = 'queued'),
    'comms_sent', (select count(*) from public.comms_log where status = 'sent'),
    'security_verdict', (select verdict from public.security_audit order by id desc limit 1),
    'last_sync', (select max(ran_at) from personal.sync_runs),
    'generated_at', now()
  );
$function$;

-- التقسية: سحب anon — العدّادات للمسجّل وحده.
revoke all on function public.sovereign_status() from public, anon, authenticated;
grant execute on function public.sovereign_status() to authenticated, service_role;

-- ======================= المسح الأمني (خدمة فقط) =======================
-- يعتمد على public.isolation_matrix() وموجّه الصلاحيات من المرحلة 1.
create or replace function public.security_sweep()
returns jsonb
language plpgsql
security definer
set search_path to 'public', 'personal', 'training', 'aon_app', 'pg_temp'
as $function$
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

-- الأشد: حتى المسجّل العادي لا ينفّذ المسح — الخدمة فقط.
revoke all on function public.security_sweep() from public, anon, authenticated;
grant execute on function public.security_sweep() to service_role;
