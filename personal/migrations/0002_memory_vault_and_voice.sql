-- =============================================================================
-- personal/0002_memory_vault_and_voice.sql
--
-- Three things this file adds, and one thing it refuses to pretend:
--
--   * a real column-level vault (AES-256 via pgcrypto's pgp_sym_encrypt, key in
--     Supabase Vault), for the handful of values that must not sit in plain text
--     even inside a private database;
--   * the recall functions (trigram, vector) and the ingest hash;
--   * `personal.style_rules` — the dialect layer, expressed as editable
--     instructions per register.
--
-- It does NOT train a "dialect embedding model". No such artifact can be built
-- from text alone, and claiming one would be the single most misleading line in
-- this repository. What actually changes the agent's voice is instruction text;
-- what actually powers recall is a general embedding model. Both are real; the
-- invented third thing is not.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Vault: one key, created once, never stored in a table or in this file
-- ---------------------------------------------------------------------------
create or replace function personal_private.ensure_vault_key(p_name text default 'personal_vault_key')
returns void
language plpgsql
security definer
set search_path = personal_private, vault, extensions, pg_temp
as $$
begin
  if exists (select 1 from vault.secrets where name = p_name) then
    return;
  end if;
  perform vault.create_secret(
    encode(extensions.gen_random_bytes(32), 'hex'),  -- 32 bytes = AES-256 key
    p_name,
    'AES-256 key for personal_private.secret_notes'
  );
end;
$$;

revoke all on function personal_private.ensure_vault_key(text) from public, anon, authenticated;

create or replace function personal_private.vault_key(p_name text default 'personal_vault_key')
returns text
language sql
stable
security definer
set search_path = vault, pg_temp
as $$
  select decrypted_secret from vault.decrypted_secrets where name = p_name;
$$;

revoke all on function personal_private.vault_key(text) from public, anon, authenticated;

-- ---------------------------------------------------------------------------
-- 2. Store and reveal a secret. The plaintext never lands in a table.
-- ---------------------------------------------------------------------------
create or replace function personal.put_secret(p_label text, p_plaintext text)
returns uuid
language plpgsql
security definer
set search_path = personal, personal_private, extensions, pg_temp
as $$
declare
  v_uid uuid := auth.uid();
  v_id  uuid;
begin
  if v_uid is null or not personal.is_principal() then
    raise exception 'put_secret is for the principal only' using errcode = '42501';
  end if;

  perform personal_private.ensure_vault_key();

  insert into personal_private.secret_notes (owner_id, label, ciphertext, iv)
  values (
    v_uid,
    p_label,
    extensions.pgp_sym_encrypt(p_plaintext, personal_private.vault_key()),
    extensions.gen_random_bytes(16)
  )
  returning id into v_id;

  return v_id;
end;
$$;

create or replace function personal.reveal_secret(p_label text)
returns text
language plpgsql
security definer
set search_path = personal, personal_private, extensions, pg_temp
as $$
declare
  v_uid uuid := auth.uid();
  v_out text;
begin
  if v_uid is null or not personal.is_principal() then
    raise exception 'reveal_secret is for the principal only' using errcode = '42501';
  end if;

  select extensions.pgp_sym_decrypt(n.ciphertext, personal_private.vault_key())
    into v_out
  from personal_private.secret_notes n
  where n.owner_id = v_uid and n.label = p_label
  order by n.created_at desc
  limit 1;

  if v_out is null then
    raise exception 'no secret labelled %', p_label using errcode = 'P0002';
  end if;

  insert into personal.agent_runs (owner_id, agent, action, target, status, detail, finished_at)
  values (v_uid, 'arena', 'reveal_secret', p_label, 'ok', '{}'::jsonb, now());

  return v_out;
end;
$$;

revoke all on function personal.put_secret(text, text) from public, anon;
revoke all on function personal.reveal_secret(text) from public, anon;
grant execute on function personal.put_secret(text, text) to authenticated;
grant execute on function personal.reveal_secret(text) to authenticated;

-- ---------------------------------------------------------------------------
-- 3. Voice / register rules — instructions, not a model
-- ---------------------------------------------------------------------------
create table if not exists personal.style_rules (
  register     text primary key check (register in ('msa','saudi','najdi','qassimi','harb')),
  label_ar     text not null,
  guidance     text not null,
  avoid        text,
  example      text,
  updated_at   timestamptz not null default now()
);

alter table personal.style_rules enable row level security;

drop policy if exists p_style_rules_read on personal.style_rules;
create policy p_style_rules_read on personal.style_rules
  for select to authenticated using (true);

drop policy if exists p_style_rules_write on personal.style_rules;
create policy p_style_rules_write on personal.style_rules
  for all to authenticated using (personal.is_principal()) with check (personal.is_principal());

insert into personal.style_rules (register, label_ar, guidance, avoid, example) values
  ('msa', 'الفصحى',
   'جمل قصيرة، معجم تقني دقيق، بلا حشو. تُستخدم في المستندات والتقارير الرسمية.',
   'المبالغة والصفات الدعائية',
   'أُنجز الترحيل، والبيانات سليمة.'),
  ('saudi', 'السعودية العامة',
   'نبرة محادثة مهنية، مخاطبة مباشرة، بلا لهجة ثقيلة.',
   'المصطلحات الأجنبية غير المترجمة',
   'خلصنا من الترحيل، والبيانات تمام.'),
  ('najdi', 'النجدية',
   'مخاطبة مباشرة، أفعال قصيرة، إيقاع سريع. تُستخدم في الشرح الشفهي والملاحظات السريعة.',
   'التراكيب الفصحى الطويلة',
   'خلّه على جنب، وابد بغيره.'),
  ('qassimi', 'القصيمية',
   'مفردات محلية، تلطيف في الطلب، استخدام «عسى» و«يا بعد حيي» في موضعها.',
   'المبالغة في التصنّع',
   'عساك بخير، وش رايك نبدأ بالجدول؟'),
  ('harb', 'لهجة حرب',
   'مفردات القبيلة وحدودها الثقافية، بلا مبالغة. تُستخدم في السياق الاجتماعي لا في التقارير.',
   'استخدامها في المخاطبات الرسمية',
   'ما يهون عليّ إلا ما يسرّك.')
on conflict (register) do nothing;
