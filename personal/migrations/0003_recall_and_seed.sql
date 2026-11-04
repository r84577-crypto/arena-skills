-- =============================================================================
-- personal/0003_recall_and_seed.sql
--
-- Recall functions, then a seed of the profile facts that are safe to publish.
--
-- WHAT IS DELIBERATELY ABSENT
--   Phone number, both birth dates, medication, diagnosis, and financial
--   practice. They are applied to the live database through a private channel
--   and are not written to this repository, which — until the principal flips
--   it — is public. The published seed therefore covers the non-identifying
--   remainder (name, handles, work, preferences).
--
--   If that is inconvenient, it is inconvenient on purpose: the alternative is
--   a public record of somebody's medical history.
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

-- ---------------------------------------------------------------------------
-- 2. Seed — publishable facts only (26 of 32; the 6 withheld are listed above)
-- ---------------------------------------------------------------------------
create or replace function personal.seed_profile()
returns jsonb
language plpgsql
security definer
set search_path = personal, pg_temp
as $$
declare
  v_uid   uuid;
  v_count integer;
begin
  select user_id into v_uid from personal.principal limit 1;
  if v_uid is null then
    raise exception 'bootstrap the twin first: select personal.bootstrap();' using errcode = '42501';
  end if;
  if v_uid <> auth.uid() then
    raise exception 'seed_profile must run as the principal' using errcode = '42501';
  end if;

  with payload (category, key, value, sensitivity) as (
    values
      ('identity','full_name','عادل عبدالله الحربي','personal'),
      ('identity','honorific','أبو عبدالله','public'),
      ('identity','nationality','سعودي','personal'),
      ('identity','tribe','حرب','personal'),
      ('identity','home_city','بريدة','public'),
      ('identity','region','منطقة القصيم','public'),
      ('identity','grew_up_in','الرياض حتى سن ١٨','public'),
      ('identity','family_composition','الوالدان وأربعة أبناء وأربع بنات','personal'),
      ('identity','dialects','الفصحى، السعودية العامة، النجدية، القصيمية، لهجة حرب','personal'),
      ('identity','handle_x','@adel__alharbi','public'),
      ('identity','handle_threads','@sultan86427','public'),
      ('identity','handle_linkedin','https://www.linkedin.com/in/adel-abdullah-alharbi','public'),
      ('work','job_title','مدرب الحاسب الآلي ومسؤول التطوير','public'),
      ('work','employer','معهد الفاو العالي للتدريب — بريدة','public'),
      ('work','education','بكالوريوس علوم الحاسب — 2024','public'),
      ('work','contract_pattern','تعاقدياً ٦ أيام، فعلياً ٥ أيام أسبوعياً','personal'),
      ('work','working_hours','٩ ساعات يومياً','personal'),
      ('work','teaching_subjects','إدخال البيانات ومعالجة النصوص، أعمال المكاتب، نظم التشغيل، البرمجة، الشبكات وأساسيات الحاسب، الطباعة العربية والإنجليزية، ومقررات التدريب التقني والمهني','public'),
      ('work','outreach','معرض اليوم الوطني، معرض ريادة، زيارات مؤسسية لجهات حكومية في بريدة، قاعدة بيانات متدربين، نماذج آلية، مواد ترويجية، استبيان QR، واتساب أعمال','public'),
      ('preference','gaming','ألعاب RPG قصصية وسيرفايفل على PC وPS5','public'),
      ('preference','reading','مانهوا كورية، روايات ويب، أنمي','public'),
      ('preference','devices','بيئة سامسونج، بناء أجهزة PC واختبار الأداء، شاشة منحنية 1440p 165Hz','public')
  )
  insert into personal.facts (owner_id, category, key, value, source, confidence, sensitivity, verified_at)
  select v_uid, p.category, p.key, p.value, 'manual', 1.00, p.sensitivity, now()
  from payload p
  on conflict (owner_id, category, key) do update
    set value = excluded.value, source = excluded.source, confidence = excluded.confidence,
        sensitivity = excluded.sensitivity, verified_at = excluded.verified_at, updated_at = now();

  get diagnostics v_count = row_count;

  insert into personal.agent_runs (owner_id, agent, action, target, status, detail, finished_at)
  values (v_uid, 'arena', 'seed_profile', 'personal.facts', 'ok',
          jsonb_build_object('facts', v_count, 'scope', 'publishable_only'), now());

  return personal.snapshot() || jsonb_build_object('facts_written', v_count);
end;
$$;

revoke all on function personal.seed_profile() from public, anon;
grant execute on function personal.seed_profile() to authenticated, service_role;
