-- =============================================================================
-- personal/0009_comms_log.sql
--
-- Outbound communications ledger: every email and WhatsApp message the
-- dashboard sends (or refuses to send) leaves one row here.
--
-- Enforcement, not documentation:
--   * RLS owner-only: actor must equal auth.uid() AND be the principal.
--   * WhatsApp destination is a CHECK constraint: only 966508247153 can ever
--     be stored. Any other number fails at INSERT, before any provider call.
--   * Delivery providers live behind server-only env vars; without them the
--     API routes answer not_configured honestly instead of pretending.
--
-- Idempotent: re-applying only replaces the status function and re-issues
-- idempotent DDL (IF NOT EXISTS / DROP IF EXISTS).
-- =============================================================================

create table if not exists public.comms_log (
  id           bigserial constraint comms_log_pkey primary key,
  created_at   timestamptz not null default now(),
  actor        uuid not null,
  channel      text not null constraint comms_log_channel_check
                 check (channel in ('email','whatsapp')),
  scope        text not null constraint comms_log_scope_check
                 check (scope in ('PERSONAL','TRAINING','AON')),
  to_addr      text not null constraint comms_log_to_check
                 check (char_length(to_addr) between 3 and 320),
  subject      text,
  body         text not null constraint comms_log_body_check
                 check (char_length(body) between 1 and 4000),
  status       text not null default 'queued' constraint comms_log_status_check
                 check (status in ('queued','sent','blocked','failed','not_configured')),
  reason       text,
  provider_ref text,
  sent_at      timestamptz,
  -- The WhatsApp gate, as a constraint: only the principal's number.
  constraint comms_log_whatsapp_gate_check
    check (channel <> 'whatsapp' or to_addr = '966508247153')
);

alter table public.comms_log enable row level security;

drop policy if exists p_comms_owner_all on public.comms_log;
create policy p_comms_owner_all on public.comms_log
  for all to authenticated
  using (actor = auth.uid() and personal.is_principal())
  with check (actor = auth.uid() and personal.is_principal());

revoke all on public.comms_log from public, anon;
grant select, insert, update, delete on public.comms_log to authenticated;
grant all on public.comms_log to service_role;

-- ---------------------------------------------------------------------------
-- sovereign_status v2: same anonymous counters as 0008, plus comms totals.
-- The dashboard reads these; nothing else changes.
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
    'comms_queued', (select count(*) from public.comms_log where status = 'queued'),
    'comms_sent', (select count(*) from public.comms_log where status = 'sent'),
    'security_verdict', (select verdict from public.security_audit order by id desc limit 1),
    'last_sync', (select max(ran_at) from personal.sync_runs),
    'generated_at', now()
  );
$function$;

revoke all on function public.sovereign_status() from public, anon;
grant execute on function public.sovereign_status() to authenticated, service_role;
