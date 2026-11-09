# سجل التباعد حيّ/مستودع — 2026-11-09

الحقيقة: القاعدة الحيّة (`hkgdtybmlrgbvakjgrxl`) تحمل 28 جدولاً و36 دالة
بُنيت عبر جلسات، بينما كان المستودع يحمل `0001–0003` فقط. هذا الملف يسجّل
الفرق بدقة — ما أُعيد توثيقه، وما بقي حيّاً فقط، وكيف يُستكمل.

## أُعيد توثيقه بدقة (نص حيّ حرفي)

| الملف | المحتوى | التحقق |
| --- | --- | --- |
| `0008` | `personal.context_decisions` + سياسته | `pg_policies` |
| `0008` | `personal.resolve_scope` + `personal.route` (نص كامل) | `pg_get_functiondef` |
| `0008` | `training.can_read/can_write` (نص كامل + تشديد ACL) | `pg_get_functiondef` + `proacl` قبل/بعد |
| `0008` | `training.exams` + `training.exam_results` (أعمدة/قيود مطابقة الأسماء) | `information_schema` + `pg_constraint` |
| `0008` | سياسات `t_exams_*` و`t_results_*` ومنحهما | `pg_policies` + `role_table_grants` |
| `0008` | `training.t_grade_result` + المشغّل `trg_grade_result` | `pg_get_functiondef` + `pg_trigger` |
| `0008` | `public.security_audit` (بلا سياسات، خدمة فقط) | `role_table_grants` |
| `0008` | `public.isolation_matrix` + `public.security_sweep` (نص كامل) | `pg_get_functiondef` |
| `0008` | `public.sovereign_status` (نص كامل) + مهمة `security_sweep_nightly` | `pg_get_functiondef` + `cron.job` |
| `0009` | `public.comms_log` (جديد: قيد بوابة الواتساب + RLS مالك فقط) | فحوصات 2/23514/42501/42501 |
| `0009` | `sovereign_status` v2 (حقلي `comms_*`) | استعلام حيّ |
| `0010` | `public.is_owner` (جديد: تحقق المالك للمسارات الخلفية) | مالك true / غريب false / مجهول 42501 |

## حيّ فقط — مسجّل هنا بأدلته (الخطوة التالية)

36 دالة (مقاسة 2026-11-09، `scanned_functions` كان 31 قبل `comms`/الكشف الكامل):

- `personal`: add_memory, add_memory_for, attribution_footer, attribution_for,
  bootstrap, capture, hash_embedding_1536, is_principal, link_edge,
  link_entity, match_memory, priority_score, put_secret, recall, recall_eval
  (×2 توقيع)، resolve_scope ✓، reveal_secret, route ✓، search_memory،
  self_check, snapshot, take_daily_snapshot, trg_embed_on_write
- `training`: can_read ✓، can_write ✓، hash_embedding_1536, recall،
  t_grade_result ✓، trg_embed
- `aon_app`: issue_client_key, verify_client_key
- `public`: embedding_health, isolation_matrix ✓، security_sweep ✓،
  sovereign_status ✓، is_owner ✓ (✓ = نصه الكامل في المستودع)

28 جدولاً كلها بـ RLS مفعّل إلا `personal_private.secret_notes` (مقفلة
بالمنح لا بالسياسات — مقصود):

- `personal` (15): agent_runs, context_decisions ✓، daily_snapshots،
  embedding_probes, entities, entity_edges, facts, finance, health_logs،
  memory, milestones, principal, routines, style_rules, sync_runs
- `training` (8): courses, enrollments, exam_results ✓، exams ✓،
  instructors, reports, vector_memory, visits
- `aon_app` (4): api_clients, core_data, outbox, system_logs
- `public` (حيوي): security_audit ✓، comms_log ✓

مهمة `cron` غير موثقة النص: `1 personal_daily_snapshot '10 1 * * *'`
(`select personal.take_daily_snapshot();` — جسم الدالة لم يُلتقط بعد).

## كيف يُستكمل (خطوة واحدة لكل مجموعة)

نفس المنهج: `pg_get_functiondef` للنصوص، `information_schema` + `pg_constraint`
للجداول، `pg_policies` + `role_table_grants` للوصول — ثم ملف `0011+` بنفس
الترتيب، ثم تطبيق تجريبي على قاعدة فارغة لإثبات الترتيب.

---

تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدرب الحاسب
