-- RLS لجدول الملاحظات السرية (personal_private.secret_notes).
--
-- كان هذا الجدول الوحيد في مخططات الأعمال بلا عزل صفوف. المخطط غير
-- مكشوف عبر REST أصلاً (المعروض: public وgraphql_public فقط)، فالخطر
-- الفعلي منخفض — وهذا عمق دفاعي: المالك (principal) فقط، وصفوفه فقط.
-- السياسة على غرار p_comms_owner_all، بمفتاح الملكية owner_id.

alter table personal_private.secret_notes enable row level security;

drop policy if exists p_secret_notes_owner_all on personal_private.secret_notes;
create policy p_secret_notes_owner_all
  on personal_private.secret_notes
  for all
  to authenticated
  using ((owner_id = auth.uid()) and personal.is_principal())
  with check ((owner_id = auth.uid()) and personal.is_principal());
