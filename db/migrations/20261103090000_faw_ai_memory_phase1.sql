-- =============================================================================
-- faw_ai — ذاكرة المشروع والملف الرقمي (المرحلة الأولى / Phase 1)
-- Project : faw-marketing (tbvtzuspjcxsidpqknid) — منصة معهد الفاو («عون»)
-- Apply   : supabase create_migration / SQL editor. Safe to re-run (idempotent).
-- Attribution (mandatory on every generated artifact):
--   «تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدير الحاسب»
--
-- DESIGN CONTRACT
--   * Additive only. Nothing in `public`, `faw_private`, `auth`, `storage`, or
--     `cron` is dropped, renamed, or rewritten. Existing RPCs (`api_*`) and the
--     Cloudflare-hosted front end keep working unchanged.
--   * Every AI table in `faw_ai` is owner-scoped: RLS `for all` compares
--     `owner_id` with `auth.uid()`, so one staff account can never read
--     another person's twin data — not even a supervisor.
--   * Embeddings: pgvector column is `vector(1536)` (text-embedding-3-small).
--     Changing the model means a new column + re-embed migration, because the
--     dimension is part of the type.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Extensions
-- ---------------------------------------------------------------------------
create extension if not exists vector  with schema extensions;
create extension if not exists pg_trgm with schema extensions;

-- ---------------------------------------------------------------------------
-- 2. Private schema
-- ---------------------------------------------------------------------------
create schema if not exists faw_ai;

revoke all on schema faw_ai from public;
revoke all on schema faw_ai from anon;
grant usage on schema faw_ai to authenticated, service_role;

comment on schema faw_ai is
  'Personal AI memory for the institute lead: profile facts, pgvector document memory, health, finance, milestones, agent telemetry. Owner-scoped by RLS.';

-- ---------------------------------------------------------------------------
-- 3. Shared trigger: keep updated_at honest
-- ---------------------------------------------------------------------------
create or replace function faw_ai.touch_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = faw_ai, pg_temp
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- 4. Tables
-- ---------------------------------------------------------------------------

-- 4.1 Structured facts about the owner (the "digital twin" core).
--     A fact is a key/value row with provenance and a confidence score, so a
--     later extraction pass can overwrite what it wrote without clobbering
--     hand-entered values.
create table if not exists faw_ai.profile_facts (
  id           uuid primary key default gen_random_uuid(),
  owner_id     uuid not null references auth.users (id) on delete cascade,
  category     text not null check (category in
                 ('identity','health','work','institute','finance','preference','goal','contact')),
  key          text not null check (char_length(key) between 1 and 120),
  value        text not null,
  value_json   jsonb,
  source       text not null default 'manual' check (source in
                 ('manual','voice','gmail','calendar','drive','linear','notion','import','system')),
  source_ref   text,
  confidence   numeric(3,2) not null default 1.00 check (confidence between 0 and 1),
  sensitivity  text not null default 'personal' check (sensitivity in
                 ('public','personal','sensitive','secret')),
  verified_at  timestamptz,
  expires_at   timestamptz,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now(),
  constraint profile_facts_owner_key unique (owner_id, category, key)
);

comment on table faw_ai.profile_facts is
  'Atomic, sourced facts about the account owner. `source` + `confidence` decide whether an automated pass may overwrite a value.';

create index if not exists profile_facts_owner_category_idx
  on faw_ai.profile_facts (owner_id, category);

drop trigger if exists trg_profile_facts_touch on faw_ai.profile_facts;
create trigger trg_profile_facts_touch
  before update on faw_ai.profile_facts
  for each row execute function faw_ai.touch_updated_at();

-- 4.2 Chunked document memory with pgvector embeddings and Arabic trigram search.
create table if not exists faw_ai.memory_documents (
  id              uuid primary key default gen_random_uuid(),
  owner_id        uuid not null references auth.users (id) on delete cascade,
  source_kind     text not null check (source_kind in
                    ('voice','note','email','doc','sheet','slide','event','task','visit',
                     'report','web','system')),
  source_table    text,
  source_id       text,
  title           text,
  content         text not null check (char_length(content) between 1 and 200000),
  content_hash    text not null,
  lang            text not null default 'ar',
  metadata        jsonb not null default '{}'::jsonb,
  embedding       extensions.vector(1536),
  embedding_model text,
  embedded_at     timestamptz,
  created_at      timestamptz not null default now(),
  constraint memory_documents_owner_hash unique (owner_id, content_hash)
);

comment on table faw_ai.memory_documents is
  'Chunk-level memory. `content_hash` makes re-ingesting the same text a no-op. `embedding` is NULL until an embedder has run; keyword search works without it.';

create index if not exists memory_documents_embedding_idx
  on faw_ai.memory_documents using hnsw (embedding extensions.vector_cosine_ops)
  with (m = 16, ef_construction = 64);

create index if not exists memory_documents_content_trgm_idx
  on faw_ai.memory_documents using gin (content extensions.gin_trgm_ops);

create index if not exists memory_documents_owner_created_idx
  on faw_ai.memory_documents (owner_id, created_at desc);

-- 4.3 Biometric / treatment / training log (medication, CPAP, workouts, vitals).
create table if not exists faw_ai.health_logs (
  id          uuid primary key default gen_random_uuid(),
  owner_id    uuid not null references auth.users (id) on delete cascade,
  kind        text not null check (kind in
                ('vitals','medication','cpap','workout','sleep','meal','mood','lab')),
  metric      text not null check (char_length(metric) between 1 and 120),
  value_num   numeric,
  value_text  text,
  unit        text,
  measured_at timestamptz not null default now(),
  source      text not null default 'manual',
  notes       text,
  metadata    jsonb not null default '{}'::jsonb,
  created_at  timestamptz not null default now(),
  constraint health_logs_has_value check (value_num is not null or value_text is not null)
);

comment on table faw_ai.health_logs is
  'One row per measurement or adherence event. Medication and CPAP reminders read from here; no dosing logic lives in the database.';

create index if not exists health_logs_owner_kind_time_idx
  on faw_ai.health_logs (owner_id, kind, measured_at desc);

-- 4.4 Financial ledger (personal and small-institute scale, not an accounting system).
create table if not exists faw_ai.finance_entries (
  id           uuid primary key default gen_random_uuid(),
  owner_id     uuid not null references auth.users (id) on delete cascade,
  occurred_on  date not null default current_date,
  direction    text not null check (direction in ('in','out')),
  category     text not null check (char_length(category) between 1 and 120),
  amount       numeric(14,2) not null check (amount >= 0),
  currency     char(3) not null default 'SAR',
  counterparty text,
  reference    text,
  notes        text,
  metadata     jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now()
);

create index if not exists finance_entries_owner_date_idx
  on faw_ai.finance_entries (owner_id, occurred_on desc);

-- 4.5 Institute milestones, optionally tied to a row in public.organizations.
create table if not exists faw_ai.institute_milestones (
  id           uuid primary key default gen_random_uuid(),
  owner_id     uuid not null references auth.users (id) on delete cascade,
  title        text not null check (char_length(title) between 1 and 200),
  detail       text,
  category     text not null default 'other' check (category in
                 ('course','diploma','report','campaign','partnership','accreditation','other')),
  happened_on  date not null default current_date,
  org_id       text references public.organizations (id) on delete set null,
  evidence_url text,
  metadata     jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now()
);

create index if not exists institute_milestones_owner_date_idx
  on faw_ai.institute_milestones (owner_id, happened_on desc);

-- 4.6 Agent telemetry — what ran, when, and whether it worked.
create table if not exists faw_ai.agent_runs (
  id          uuid primary key default gen_random_uuid(),
  owner_id    uuid references auth.users (id) on delete set null,
  agent       text not null default 'arena',
  action      text not null check (char_length(action) between 1 and 200),
  target      text,
  status      text not null check (status in ('started','ok','failed','skipped')),
  detail      jsonb not null default '{}'::jsonb,
  started_at  timestamptz not null default now(),
  finished_at timestamptz
);

create index if not exists agent_runs_started_idx
  on faw_ai.agent_runs (started_at desc);

-- ---------------------------------------------------------------------------
-- 5. Row Level Security — owner only, on every table
-- ---------------------------------------------------------------------------
alter table faw_ai.profile_facts        enable row level security;
alter table faw_ai.memory_documents     enable row level security;
alter table faw_ai.health_logs          enable row level security;
alter table faw_ai.finance_entries      enable row level security;
alter table faw_ai.institute_milestones enable row level security;
alter table faw_ai.agent_runs           enable row level security;

do $$
declare
  t text;
begin
  foreach t in array array[
    'profile_facts','memory_documents','health_logs',
    'finance_entries','institute_milestones','agent_runs'
  ]
  loop
    execute format('drop policy if exists p_%1$s_owner on faw_ai.%1$s', t);
    execute format(
      'create policy p_%1$s_owner on faw_ai.%1$s for all to authenticated '
      'using (owner_id = auth.uid()) with check (owner_id = auth.uid())', t);
  end loop;
end;
$$;

revoke all on all tables in schema faw_ai from anon, public;
grant select, insert, update, delete on all tables in schema faw_ai to authenticated;
grant all on all tables in schema faw_ai to service_role;

-- ---------------------------------------------------------------------------
-- 6. RPCs, exposed through PostgREST alongside the existing public.api_* set
-- ---------------------------------------------------------------------------

-- 6.1 The attribution line, single source of truth for every generator.
create or replace function public.api_attribution_footer()
returns text
language sql
stable
security invoker
set search_path = public, pg_temp
as $$
  select coalesce(
    (select value_json ->> 'text' from public.settings where key = 'attribution_footer'),
    'تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدير الحاسب'
  );
$$;

comment on function public.api_attribution_footer() is
  'Mandatory credit line. Every generated Doc, Slide, Sheet, PDF, and report must call this instead of hard-coding the text.';

-- 6.2 Keyword recall. Works today, before any embedder exists.
create or replace function public.api_memory_search(p_query text, p_limit integer default 10)
returns table (id uuid, title text, snippet text, source_kind text, score real)
language sql
stable
security invoker
set search_path = public, faw_ai, extensions, pg_temp
as $$
  select d.id,
         coalesce(d.title, left(d.content, 80)),
         left(d.content, 400),
         d.source_kind,
         similarity(d.content, p_query)::real as score
  from faw_ai.memory_documents d
  where d.owner_id = auth.uid()
    and coalesce(p_query, '') <> ''
  order by similarity(d.content, p_query) desc, d.created_at desc
  limit least(greatest(coalesce(p_limit, 10), 1), 50);
$$;

-- 6.3 Semantic recall. `p_embedding` is the JSON array form, e.g. '[0.1,0.2,...]'.
--     plpgsql, not sql, so a wrong-dimension vector fails with a readable message
--     instead of pgvector's "different vector dimensions" from inside a sort.
create or replace function public.api_memory_match(
  p_embedding text,
  p_limit integer default 8,
  p_min_similarity real default 0.2
)
returns table (id uuid, title text, snippet text, source_kind text, score real)
language plpgsql
stable
security invoker
set search_path = public, faw_ai, extensions, pg_temp
as $$
declare
  v extensions.vector;
begin
  v := nullif(btrim(p_embedding), '')::extensions.vector;
  if v is null then
    return;
  end if;
  if vector_dims(v) <> 1536 then
    raise exception 'embedding has % dimensions, this memory column is 1536', vector_dims(v)
      using hint = 'Embed with text-embedding-3-small, or add a new column and re-embed for a different model.';
  end if;

  return query
    select d.id,
           coalesce(d.title, left(d.content, 80)),
           left(d.content, 400),
           d.source_kind,
           (1 - (d.embedding <=> v))::real as score
    from faw_ai.memory_documents d
    where d.owner_id = auth.uid()
      and d.embedding is not null
      and (1 - (d.embedding <=> v)) >= coalesce(p_min_similarity, 0.2)
    order by d.embedding <=> v
    limit least(greatest(coalesce(p_limit, 8), 1), 50);
end;
$$;

-- 6.3b Ingest one memory chunk. The hash is computed here so every writer
--      (agent, n8n, edge function, SQL console) deduplicates the same way.
create or replace function public.api_memory_add(
  p_source_kind text,
  p_content text,
  p_title text default null,
  p_metadata jsonb default '{}'::jsonb,
  p_source_table text default null,
  p_source_id text default null
)
returns uuid
language plpgsql
security invoker
set search_path = public, faw_ai, extensions, pg_temp
as $$
declare
  new_id uuid;
begin
  if auth.uid() is null then
    raise exception 'api_memory_add requires an authenticated session';
  end if;

  insert into faw_ai.memory_documents
    (owner_id, source_kind, source_table, source_id, title, content, content_hash, metadata)
  values
    (auth.uid(), p_source_kind, p_source_table, p_source_id, p_title,
     p_content, md5(p_content), coalesce(p_metadata, '{}'::jsonb))
  on conflict (owner_id, content_hash) do update
    set title = coalesce(excluded.title, faw_ai.memory_documents.title),
        metadata = faw_ai.memory_documents.metadata || excluded.metadata
  returning id into new_id;

  return new_id;
end;
$$;

-- 6.4 Telemetry for the dashboard header: one call, one JSON object.
create or replace function public.api_ai_snapshot()
returns jsonb
language sql
stable
security invoker
set search_path = public, faw_ai, pg_temp
as $$
  select jsonb_build_object(
    'facts', coalesce((
      select jsonb_object_agg(category, n)
      from (select category, count(*) as n from faw_ai.profile_facts
            where owner_id = auth.uid() group by category) c
    ), '{}'::jsonb),
    'memory_documents', (select count(*) from faw_ai.memory_documents where owner_id = auth.uid()),
    'memory_embedded',  (select count(*) from faw_ai.memory_documents
                         where owner_id = auth.uid() and embedding is not null),
    'health_logs',      (select count(*) from faw_ai.health_logs where owner_id = auth.uid()),
    'finance_entries',  (select count(*) from faw_ai.finance_entries where owner_id = auth.uid()),
    'milestones',       (select count(*) from faw_ai.institute_milestones where owner_id = auth.uid()),
    'agent_runs_7d',    (select count(*) from faw_ai.agent_runs
                         where owner_id = auth.uid() and started_at > now() - interval '7 days'),
    'attribution',      public.api_attribution_footer()
  );
$$;

revoke all on function public.api_attribution_footer() from public, anon;
revoke all on function public.api_memory_search(text, integer) from public, anon;
revoke all on function public.api_memory_match(text, integer, real) from public, anon;
revoke all on function public.api_memory_add(text, text, text, jsonb, text, text) from public, anon;
revoke all on function public.api_ai_snapshot() from public, anon;

grant execute on function public.api_attribution_footer() to authenticated, service_role;
grant execute on function public.api_memory_search(text, integer) to authenticated, service_role;
grant execute on function public.api_memory_match(text, integer, real) to authenticated, service_role;
grant execute on function public.api_memory_add(text, text, text, jsonb, text, text) to authenticated, service_role;
grant execute on function public.api_ai_snapshot() to authenticated, service_role;

-- Future functions in this schema should start closed too.
alter default privileges in schema faw_ai revoke execute on functions from public;

-- ---------------------------------------------------------------------------
-- 7. Configuration rows (additive; existing keys are untouched)
-- ---------------------------------------------------------------------------
insert into public.settings (key, value_json)
values
  ('attribution_footer', jsonb_build_object(
     'text', 'تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدير الحاسب',
     'required', true,
     'applies_to', jsonb_build_array('doc','slide','sheet','pdf','report','email'))),
  ('ai_memory', jsonb_build_object(
     'embedding_model', 'text-embedding-3-small',
     'embedding_dim', 1536,
     'enabled', true,
     'phase', 1))
on conflict (key) do nothing;
