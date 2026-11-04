-- =============================================================================
-- faw_ai: signed external webhook intake (open-mesh, phase 1)
-- Project : faw-marketing (tbvtzuspjcxsidpqknid)
-- Apply   : after 20261104140000_faw_ai_profile_preview.sql. Idempotent.
--
-- WHAT THIS IS
--   A single door for the outside world: Telegram, WhatsApp Business callbacks,
--   Zapier/Make, or any custom REST client. One door with a token per source,
--   a size ceiling, a rate ceiling, and idempotency — instead of one bespoke
--   endpoint per vendor.
--
-- WHY THE DOOR IS IN THE DATABASE AND NOT IN THE FUNCTION
--   Token comparison, deduplication, and throttling all need to be atomic. If an
--   edge function enforced them, two concurrent deliveries could both pass the
--   "have I seen this?" check. The function only forwards bytes; the rules live
--   where the data does.
--
-- WHAT IT DELIBERATELY DOES NOT DO
--   It does not write into `memory_documents`. Capturing a message and deciding
--   it is worth remembering are two decisions; the second one is reviewed (see
--   skills/faw-ai-memory/AUTOMATION.md). A webhook that writes straight into
--   long-term memory is how a chat log becomes a permanent record of somebody
--   else's private message.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Sources: one row per caller, with a hashed token
-- ---------------------------------------------------------------------------
create table if not exists faw_ai.webhook_sources (
  id            text primary key check (id ~ '^[a-z0-9][a-z0-9_-]{1,40}$'),
  label         text not null,
  kind          text not null check (kind in
                  ('telegram','whatsapp','zapier','make','custom','test')),
  token_sha256  text not null check (token_sha256 ~ '^[0-9a-f]{64}$'),
  active        boolean not null default true,
  max_per_min   integer not null default 60 check (max_per_min between 1 and 6000),
  payload_limit integer not null default 65536 check (payload_limit between 1024 and 1048576),
  notes         text,
  created_at    timestamptz not null default now(),
  last_seen_at  timestamptz
);

comment on table faw_ai.webhook_sources is
  'One row per external caller. The plaintext token is never stored — only its SHA-256.';

alter table faw_ai.webhook_sources enable row level security;
-- No policies on purpose: readable only by service_role, which is what the edge
-- function uses. A logged-in staff member must not be able to list tokens.

-- ---------------------------------------------------------------------------
-- 2. Events: the capture log
-- ---------------------------------------------------------------------------
create table if not exists faw_ai.webhook_events (
  id           uuid primary key default gen_random_uuid(),
  source_id    text not null references faw_ai.webhook_sources (id) on delete cascade,
  external_id  text,
  received_at  timestamptz not null default now(),
  payload      jsonb not null,
  payload_bytes integer not null default 0,
  status       text not null default 'new' check (status in ('new','processed','ignored')),
  processed_at timestamptz
);

create index if not exists webhook_events_source_time_idx
  on faw_ai.webhook_events (source_id, received_at desc);

-- Idempotency: a retried delivery with the same vendor id is a no-op. Rows with
-- no external id are not deduplicated, because nothing identifies them.
create unique index if not exists webhook_events_dedupe_idx
  on faw_ai.webhook_events (source_id, external_id)
  where external_id is not null;

alter table faw_ai.webhook_events enable row level security;
-- No policies on purpose: the payload may be a third party's message.

revoke all on faw_ai.webhook_sources from anon, public;
revoke all on faw_ai.webhook_events  from anon, public;
grant all on faw_ai.webhook_sources to service_role;
grant all on faw_ai.webhook_events  to service_role;

-- ---------------------------------------------------------------------------
-- 3. Register a source (service_role only). The token enters here and nowhere
--    else; the caller keeps the plaintext, the database keeps the hash.
-- ---------------------------------------------------------------------------
create or replace function faw_ai.register_webhook_source(
  p_id      text,
  p_label   text,
  p_kind    text,
  p_token   text,
  p_notes   text default null
)
returns text
language plpgsql
security definer
set search_path = faw_ai, extensions, pg_temp
as $$
begin
  if p_token is null or length(p_token) < 24 then
    raise exception 'token must be at least 24 characters';
  end if;

  insert into faw_ai.webhook_sources (id, label, kind, token_sha256, notes)
  values (p_id, p_label, p_kind, encode(digest(p_token, 'sha256'), 'hex'), p_notes)
  on conflict (id) do update
    set label = excluded.label,
        kind = excluded.kind,
        token_sha256 = excluded.token_sha256,
        notes = coalesce(excluded.notes, faw_ai.webhook_sources.notes),
        active = true;

  return p_id;
end;
$$;

revoke all on function faw_ai.register_webhook_source(text, text, text, text, text)
  from public, anon, authenticated;
grant execute on function faw_ai.register_webhook_source(text, text, text, text, text)
  to service_role;

-- ---------------------------------------------------------------------------
-- 4. Ingest: authenticate, throttle, deduplicate, store
-- ---------------------------------------------------------------------------
create or replace function faw_ai.webhook_ingest(
  p_source      text,
  p_token       text,
  p_payload     jsonb,
  p_external_id text default null
)
returns jsonb
language plpgsql
security definer
set search_path = faw_ai, extensions, pg_temp
as $$
declare
  v_src       faw_ai.webhook_sources;
  v_hash      text;
  v_bytes     integer;
  v_recent    integer;
  v_event_id  uuid;
  v_external  text := nullif(btrim(coalesce(p_external_id, '')), '');
begin
  select * into v_src from faw_ai.webhook_sources where id = p_source and active;
  if not found then
    return jsonb_build_object('ok', false, 'status', 'unknown_source');
  end if;

  v_hash := encode(digest(coalesce(p_token, ''), 'sha256'), 'hex');
  if v_hash <> v_src.token_sha256 then
    return jsonb_build_object('ok', false, 'status', 'bad_token');
  end if;

  if p_payload is null or jsonb_typeof(p_payload) <> 'object' then
    return jsonb_build_object('ok', false, 'status', 'bad_payload');
  end if;

  v_bytes := octet_length(p_payload::text);
  if v_bytes > v_src.payload_limit then
    return jsonb_build_object('ok', false, 'status', 'too_large', 'bytes', v_bytes);
  end if;

  select count(*) into v_recent
  from faw_ai.webhook_events
  where source_id = p_source and received_at > now() - interval '1 minute';

  if v_recent >= v_src.max_per_min then
    return jsonb_build_object('ok', false, 'status', 'throttled', 'per_minute', v_recent);
  end if;

  insert into faw_ai.webhook_events (source_id, external_id, payload, payload_bytes)
  values (p_source, v_external, p_payload, v_bytes)
  on conflict (source_id, external_id) where external_id is not null
    do nothing
  returning id into v_event_id;

  update faw_ai.webhook_sources
     set last_seen_at = now()
   where id = p_source;

  if v_event_id is null then
    return jsonb_build_object('ok', true, 'status', 'duplicate', 'external_id', v_external);
  end if;

  return jsonb_build_object('ok', true, 'status', 'accepted',
                            'event_id', v_event_id, 'bytes', v_bytes);
end;
$$;

revoke all on function faw_ai.webhook_ingest(text, text, jsonb, text)
  from public, anon, authenticated;
grant execute on function faw_ai.webhook_ingest(text, text, jsonb, text)
  to service_role;
