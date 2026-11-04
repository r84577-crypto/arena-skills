-- =============================================================================
-- personal/0003_recall_and_seed.sql
-- Owner-scoped recall and snapshot functions only.
-- Person-specific profile values are intentionally not stored in this public file.
-- Supply owner data through a private, authenticated deployment channel.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Recall
-- ---------------------------------------------------------------------------
create or replace function personal.add_memory(
  p_source_kind text,
  p_content     text,
  p_title       text default null,
  p_metadata    jsonb default '{}'::jsonb
)
returns uuid
language plpgsql
security invoker
set search_path = personal, extensions, pg_temp
as $$
declare
  v_uid uuid := auth.uid();
  v_id  uuid;
begin
  if v_uid is null or not personal.is_principal() then
    raise exception 'add_memory is for the principal only' using errcode = '42501';
  end if;

  insert into personal.memory (owner_id, source_kind, title, content, content_hash, metadata)
  values (v_uid, p_source_kind, p_title, p_content, md5(p_content), coalesce(p_metadata, '{}'::jsonb))
  on conflict (owner_id, content_hash) do update
    set title = coalesce(excluded.title, personal.memory.title),
        metadata = personal.memory.metadata || excluded.metadata
  returning id into v_id;

  return v_id;
end;
$$;

create or replace function personal.search_memory(p_query text, p_limit integer default 10)
returns table (id uuid, title text, snippet text, source_kind text, score real)
language sql
stable
security invoker
set search_path = personal, extensions, pg_temp
as $$
  select m.id,
         coalesce(m.title, left(m.content, 80)),
         left(m.content, 400),
         m.source_kind,
         similarity(m.content, p_query)::real
  from personal.memory m
  where m.owner_id = auth.uid()
    and coalesce(p_query, '') <> ''
  order by similarity(m.content, p_query) desc, m.created_at desc
  limit least(greatest(coalesce(p_limit, 10), 1), 50);
$$;

create or replace function personal.match_memory(
  p_embedding text,
  p_limit integer default 8,
  p_min_similarity real default 0.2
)
returns table (id uuid, title text, snippet text, source_kind text, score real)
language plpgsql
stable
security invoker
set search_path = personal, extensions, pg_temp
as $$
declare
  v extensions.vector;
begin
  v := nullif(btrim(p_embedding), '')::extensions.vector;
  if v is null then
    return;
  end if;
  if vector_dims(v) <> 1536 then
    raise exception 'embedding has % dimensions, this column is 1536', vector_dims(v)
      using hint = 'Embed with text-embedding-3-small, or add a new column and re-embed.';
  end if;

  return query
    select m.id, coalesce(m.title, left(m.content, 80)), left(m.content, 400), m.source_kind,
           (1 - (m.embedding <=> v))::real
    from personal.memory m
    where m.owner_id = auth.uid()
      and m.embedding is not null
      and (1 - (m.embedding <=> v)) >= coalesce(p_min_similarity, 0.2)
    order by m.embedding <=> v
    limit least(greatest(coalesce(p_limit, 8), 1), 50);
end;
$$;

create or replace function personal.snapshot()
returns jsonb
language sql
stable
security invoker
set search_path = personal, pg_temp
as $$
  select jsonb_build_object(
    'principal', (select full_name from personal.principal where user_id = auth.uid()),
    'facts', coalesce((select jsonb_object_agg(category, n) from
      (select category, count(*) n from personal.facts where owner_id = auth.uid() group by category) c), '{}'::jsonb),
    'facts_secret', (select count(*) from personal.facts where owner_id = auth.uid() and sensitivity = 'secret'),
    'memory', (select count(*) from personal.memory where owner_id = auth.uid()),
    'memory_embedded', (select count(*) from personal.memory where owner_id = auth.uid() and embedding is not null),
    'health_logs', (select count(*) from personal.health_logs where owner_id = auth.uid()),
    'finance_entries', (select count(*) from personal.finance where owner_id = auth.uid()),
    'milestones', (select count(*) from personal.milestones where owner_id = auth.uid()),
    'attribution', personal.attribution_footer());
$$;

revoke all on function personal.add_memory(text, text, text, jsonb) from public, anon;
revoke all on function personal.search_memory(text, integer) from public, anon;
revoke all on function personal.match_memory(text, integer, real) from public, anon;
revoke all on function personal.snapshot() from public, anon;
grant execute on function personal.add_memory(text, text, text, jsonb) to authenticated, service_role;
grant execute on function personal.search_memory(text, integer) to authenticated, service_role;
grant execute on function personal.match_memory(text, integer, real) to authenticated, service_role;
grant execute on function personal.snapshot() to authenticated, service_role;

