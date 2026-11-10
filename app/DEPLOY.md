# النشر التلقائي — Netlify (المعتمد) + Vercel (بديل) + GitHub Actions

## ما يعمل تلقائياً من اليوم

كل دفع على أي فرع يشغّل `.github/workflows/ci.yml`: تثبيت نظيف (`npm ci`)،
ثم `typecheck`، ثم `next build`. الفحص يظهر على الـ PR قبل الدمج — لا كود
مكسور يمر بصمت.

## النشر على Netlify — المضيف المعتمد (خطوات المالك — مرة واحدة)

التطبيق يعمل بوضع SSR الكامل (مسارات `/api/*` ديناميكية) عبر
`@netlify/plugin-nextjs` المثبتة في `package.json` والمفعّلة في
`netlify.toml` الجذري — لا حاجة لأي إعداد يدوي للبناء.

1. Netlify ← **Add new site** ← **Import an existing project** ← GitHub ←
   `r84577-crypto/arena-skills` (المستودع خاص: امنح تطبيق Netlify الوصول
   من **GitHub App Permissions** إذا لم يظهر).
   - أو اربط مستودع Git بموقعك الحالي `alfao` من: Site settings ←
     Build & deploy ← **Link repository**.
2. **Base directory:** `app` — أمر البناء والنشر يُقرأ تلقائياً من `netlify.toml`.
3. **Environment Variables** (نفس القيم المعتمدة):
   - `NEXT_PUBLIC_SUPABASE_URL` = `https://hkgdtybmlrgbvakjgrxl.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = المفتاح العام (anon) من Supabase
   - `GMAIL_USER` + `GMAIL_APP_PASSWORD` (خادم فقط — كلمة مرور التطبيقات
     من `myaccount.google.com/apppasswords` بعد تفعيل التحقق بخطوتين)
   - اترك `RESEND_*` و`WHATSAPP_*` فارغة الآن — الموقع يعمل بدونها.
4. لا تضع `SUPABASE_SERVICE_ROLE_KEY` هنا — لا حاجة له في هذه الواجهة أبداً.
5. انشر. بعدها: كل دفع على `main` يعيد النشر تلقائياً.

## النشر التلقائي على Vercel (بديل — خطوات المالك — مرة واحدة)

الحساب الحالي `limited: true` (قراءة فقط)، فإنشاء المشروع بيد المالك حصراً:

1. [vercel.com/new](https://vercel.com/new) ← استيراد `r84577-crypto/arena-skills`.
2. **Root Directory:** `app`.
3. **Environment Variables** (كل بيئة على حدة):
   - `NEXT_PUBLIC_SUPABASE_URL` = `https://hkgdtybmlrgbvakjgrxl.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = المفتاح العام (publishable/anon) من Supabase
   - `RESEND_API_KEY` (خادم فقط — 3000 رسالة/شهر مجاناً، وإلا `not_configured`)
   - `RESEND_FROM` (نطاق موثّق للإنتاج؛ للتجربة `onboarding@resend.dev` لبريدك فقط)
   - أو البديل المجاني الكامل: `GMAIL_USER` + `GMAIL_APP_PASSWORD` (خادم فقط —
     كلمة مرور التطبيقات من `myaccount.google.com/apppasswords` بعد تفعيل
     التحقق بخطوتين؛ ترسل لأي مستلم بحدود Gmail اليومية).
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

تم إعداد وتطوير هذا العمل بواسطة: الأستاذ عادل الحربي - مدرب الحاسب
