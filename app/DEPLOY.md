# النشر التلقائي — Vercel + GitHub Actions

## ما يعمل تلقائياً من اليوم

كل دفع على أي فرع يشغّل `.github/workflows/ci.yml`: تثبيت نظيف (`npm ci`)،
ثم `typecheck`، ثم `next build`. الفحص يظهر على الـ PR قبل الدمج — لا كود
مكسور يمر بصمت.

## النشر التلقائي على Vercel (خطوات المالك — مرة واحدة)

الحساب الحالي `limited: true` (قراءة فقط)، فإنشاء المشروع بيد المالك حصراً:

1. [vercel.com/new](https://vercel.com/new) ← استيراد `r84577-crypto/arena-skills`.
2. **Root Directory:** `app`.
3. **Environment Variables** (كل بيئة على حدة):
   - `NEXT_PUBLIC_SUPABASE_URL` = `https://hkgdtybmlrgbvakjgrxl.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = المفتاح العام (publishable/anon) من Supabase
   - `RESEND_API_KEY` (خادم فقط — للإرسال، وإلا `not_configured` بصدق)
   - `RESEND_FROM` (نطاق موثّق للإنتاج)
   - `WHATSAPP_TOKEN` + `WHATSAPP_PHONE_NUMBER_ID` (خادم فقط)
4. لا تضع `SUPABASE_SERVICE_ROLE_KEY` هنا — لا حاجة له في هذه الواجهة أصلاً.
5. انشر. بعدها: كل دفع على `main` ينشر للإنتاج تلقائياً، وكل PR يأخذ
   رابط معاينة مستقلاً.

## قبل أول نشر إنتاجي

- [ ] ترقية حساب Vercel (الكتابة محجوبة حالياً).
- [ ] توثيق نطاق Resend (وإلا الإرسال مقيّد ببريد الحساب).
- [ ] نافذة واتساب نشطة أو قالب معتمد (وإلا Meta يرفض خارج 24 ساعة).
- [ ] `security_sweep` أخضر: `select public.security_sweep()->>'verdict'`.

---

تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدير الحاسب
