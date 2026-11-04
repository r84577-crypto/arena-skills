-- =============================================================================
-- personal/0001_sovereign_core.sql
-- The personal digital twin: one person, one owner, no institution.
--
-- Design constraints, in order of priority:
--   1. No second reader. Every table is readable by exactly one auth user
--      (the principal). There are no supervisor, admin, or `service_role`-only
--      tables that a staff member could inherit later.
--   2. No institute coupling. This schema has no foreign key into any
--      operational table, so it can be restored or deleted on its own.
--   3. Reconstructable. Every fact carries its source, confidence, and tier.
--   4. Honest about encryption: at-rest encryption is the platform's job;
--      `personal_private.secret_notes` is the one column-level encrypted vault,
--      using pgcrypto with a key held in Supabase Vault.
--
-- Attribution (every generated artifact): see public.attribution_footer().
-- =============================================================================

create extension if not exists vector    with schema extensions;
create extension if not exists pg_trgm   with schema extensions;
create extension if not exists pgcrypto  with schema extensions;

create schema if not exists personal;
create schema if not exists personal_private;

revoke all on schema personal from public, anon;
revoke all on schema personal_private from public, anon;
grant usage on schema personal to authenticated, service_role;

-- ---------------------------------------------------------------------------
-- 1. The principal. One row, created by seeding, not by signup.
-- ---------------------------------------------------------------------------
create table if not exists personal.principal (
  user_id      uuid primary key references auth.users (id) on delete cascade,
  full_name    text not null,
  honorific    text,
  created_at   timestamptz not null default now(),
  bootstrapped_at timestamptz
);

comment on table personal.principal is
  'Exactly one row. Its presence is what makes an account "the principal"; a second row is a configuration error, enforced by the constraint below.';

create unique index if not exists principal_single_row on personal.principal ((true));

-- ---------------------------------------------------------------------------
-- 2. Facts: the twin's structured memory, tiered and sourced
-- ---------------------------------------------------------------------------
create table if not exists personal.facts (
  id          uuid primary key default gen_random_uuid(),
  owner_id    uuid not null references personal.principal (user_id) on delete cascade,
  category    text not null check (category in
                ('identity','contact','work','health','finance','preference','goal','milestone')),
  key         text not null check (char_length(key) between 1 and 120),
  value       text not null,
  value_json  jsonb,
  source      text not null default 'manual' check (source in
                ('manual','voice','gmail','calendar','drive','telegram','whatsapp','import','system')),
  source_ref  text,
  confidence  numeric(3,2) not null default 1.00 check (confidence between 0 and 1),
  sensitivity text not null default 'personal' check (sensitivity in
                ('public','personal','sensitive','secret')),
  verified_at timestamptz,
  expires_at  timestamptz,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (owner_id, category, key)
);

create index if not exists facts_owner_category_idx on personal.facts (owner_id, category);

-- ---------------------------------------------------------------------------
-- 3. Memory: chunks + embeddings + Arabic-tolerant keyword search
-- ---------------------------------------------------------------------------
create table if not exists personal.memory (
  id              uuid primary key default gen_random_uuid(),
  owner_id        uuid not null references personal.principal (user_id) on delete cascade,
  source_kind     text not null check (source_kind in
                    ('voice','note','email','doc','event','task','web','system','chat')),
  title           text,
  content         text not null check (char_length(content) between 1 and 200000),
  content_hash    text not null,
  lang            text not null default 'ar',
  metadata        jsonb not null default '{}'::jsonb,
  embedding       extensions.vector(1536),
  embedding_model text,
  embedded_at     timestamptz,
  created_at      timestamptz not null default now(),
  unique (owner_id, content_hash)
);

create index if not exists memory_embedding_idx on personal.memory
  using hnsw (embedding extensions.vector_cosine_ops) with (m = 16, ef_construction = 64);
create index if not exists memory_content_trgm_idx on personal.memory
  using gin (content extensions.gin_trgm_ops);
create index if not exists memory_owner_created_idx on personal.memory (owner_id, created_at desc);

-- ---------------------------------------------------------------------------
-- 4. Health, money, milestones — the three that leak worst if misconfigured
-- ---------------------------------------------------------------------------
create table if not exists personal.health_logs (
  id          uuid primary key default gen_random_uuid(),
  owner_id    uuid not null references personal.principal (user_id) on delete cascade,
  kind        text not null check (kind in
                ('vitals','medication','cpap','workout','sleep','meal','mood','lab','symptom')),
  metric      text not null,
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
create index if not exists health_owner_kind_time_idx on personal.health_logs (owner_id, kind, measured_at desc);

create table if not exists personal.finance (
  id           uuid primary key default gen_random_uuid(),
  owner_id     uuid not null references personal.principal (user_id) on delete cascade,
  occurred_on  date not null default current_date,
  direction    text not null check (direction in ('in','out')),
  category     text not null,
  amount       numeric(14,2) not null check (amount >= 0),
  currency     char(3) not null default 'SAR',
  counterparty text,
  notes        text,
  metadata     jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now()
);
create index if not exists finance_owner_date_idx on personal.finance (owner_id, occurred_on desc);

create table if not exists personal.milestones (
  id           uuid primary key default gen_random_uuid(),
  owner_id     uuid not null references personal.principal (user_id) on delete cascade,
  title        text not null,
  detail       text,
  category     text not null default 'other' check (category in
                 ('career','education','project','health','finance','family','other')),
  happened_on  date not null default current_date,
  evidence_url text,
  metadata     jsonb not null default '{}'::jsonb,
  created_at   timestamptz not null default now()
);
create index if not exists milestones_owner_date_idx on personal.milestones (owner_id, happened_on desc);

-- ---------------------------------------------------------------------------
-- 5. Column-level vault: the few things that must not sit in plain text even
--    inside a private database. Key lives in Supabase Vault, not in a table.
-- ---------------------------------------------------------------------------
create table if not exists personal_private.secret_notes (
  id           uuid primary key default gen_random_uuid(),
  owner_id     uuid not null references personal.principal (user_id) on delete cascade,
  label        text not null,
  ciphertext   bytea not null,
  iv           bytea not null,
  created_at   timestamptz not null default now()
);

comment on table personal_private.secret_notes is
  'AES-256 via pgcrypto (encrypt_iv, ciphertext+HMAC) with the key read from Vault by name at call time. Never selected directly by a client; only through personal.reveal_secret().';

revoke all on personal_private.secret_notes from public, anon, authenticated;

-- ---------------------------------------------------------------------------
-- 6. Agent runs: an honest log of what the system did
-- ---------------------------------------------------------------------------
create table if not exists personal.agent_runs (
  id          uuid primary key default gen_random_uuid(),
  owner_id    uuid references personal.principal (user_id) on delete set null,
  agent       text not null default 'arena',
  action      text not null,
  target      text,
  status      text not null check (status in ('started','ok','failed','skipped')),
  detail      jsonb not null default '{}'::jsonb,
  started_at  timestamptz not null default now(),
  finished_at timestamptz
);
create index if not exists agent_runs_started_idx on personal.agent_runs (started_at desc);

-- ---------------------------------------------------------------------------
-- 7. Attribution: one source of truth, same wording as the institute system
-- ---------------------------------------------------------------------------
create or replace function personal.attribution_footer()
returns text
language sql
immutable
as $$
  select 'تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدير الحاسب';
$$;

-- ---------------------------------------------------------------------------
-- 8. RLS: the principal, or nobody
-- ---------------------------------------------------------------------------
alter table personal.principal   enable row level security;
alter table personal.facts       enable row level security;
alter table personal.memory      enable row level security;
alter table personal.health_logs enable row level security;
alter table personal.finance     enable row level security;
alter table personal.milestones  enable row level security;
alter table personal.agent_runs  enable row level security;

create or replace function personal.is_principal()
returns boolean
language sql
stable
security definer
set search_path = personal, pg_temp
as $$
  select exists (select 1 from personal.principal where user_id = auth.uid());
$$;

do $$
declare t text;
begin
  foreach t in array array['principal','facts','memory','health_logs','finance','milestones','agent_runs']
  loop
    execute format('drop policy if exists p_%1$s_self on personal.%1$s', t);
    if t = 'principal' then
      execute 'create policy p_principal_self on personal.principal for select to authenticated using (user_id = auth.uid())';
    else
      execute format('create policy p_%1$s_self on personal.%1$s for all to authenticated using (owner_id = auth.uid()) with check (owner_id = auth.uid())', t);
    end if;
  end loop;
end;
$$;

revoke all on all tables in schema personal from anon, public;
grant select, insert, update, delete on all tables in schema personal to authenticated;
grant all on all tables in schema personal to service_role;

-- ---------------------------------------------------------------------------
-- 9. Bootstrapping: the first sign-in claims the twin, once
-- ---------------------------------------------------------------------------
create or replace function personal.bootstrap()
returns jsonb
language plpgsql
security definer
set search_path = personal, pg_temp
as $$
declare
  v_uid uuid := auth.uid();
  v_row personal.principal;
begin
  if v_uid is null then
    raise exception 'bootstrap requires an authenticated session' using errcode = '42501';
  end if;

  select * into v_row from personal.principal limit 1;
  if found and v_row.user_id <> v_uid then
    raise exception 'this twin already belongs to another account' using errcode = '42501';
  end if;

  insert into personal.principal (user_id, full_name, honorific, bootstrapped_at)
  values (v_uid, 'عادل عبدالله الحربي', 'أبو عبدالله', now())
  on conflict (user_id) do update set bootstrapped_at = coalesce(personal.principal.bootstrapped_at, now());

  insert into personal.agent_runs (owner_id, agent, action, target, status, finished_at)
  values (v_uid, 'arena', 'bootstrap', 'personal.principal', 'ok', now());

  return jsonb_build_object('ok', true, 'user_id', v_uid,
                            'attribution', personal.attribution_footer());
end;
$$;

revoke all on function personal.bootstrap() from public, anon;
grant execute on function personal.bootstrap() to authenticated, service_role;
