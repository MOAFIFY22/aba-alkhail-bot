# 🤖 شرح تشغيل بوت أبا الخيل

## الخطوات:

### 1️⃣ تحضير الملفات

```
aba_alkhail_bot/
├── aba_alkhail_bot.py
├── requirements.txt
├── Procfile
└── runtime.txt
```

### 2️⃣ إنشاء حساب Render

1. روح: https://render.com
2. اضغط "Sign Up"
3. سجل بـ GitHub أو Email

### 3️⃣ رفع الملفات على GitHub

```bash
# إنشاء repository جديد على GitHub
git init
git add .
git commit -m "Initial commit"
git push -u origin main
```

### 4️⃣ ربط Render مع GitHub

1. في Render → "New +"
2. اختر "Web Service"
3. اختر Repository بتاعك
4. الإعدادات:
   - **Name**: aba-alkhail-bot
   - **Build Command**: pip install -r requirements.txt
   - **Start Command**: python aba_alkhail_bot.py
   - **Instance Type**: Free

### 5️⃣ متغيرات البيئة (Environment Variables)

في Render → Settings → Environment Variables:

```
BOT_TOKEN=8646021850:AAGsIXcIF7ZtN8Nfv5W8GzLQdx9E86EH9OQ
YOUR_CHAT_ID=966539576137
SHEETS_URL=https://docs.google.com/spreadsheets/d/1I9dSX7mpdRly2I-SpadicLxsjcU4V_IyWX_1I6v3gUM
```

### 6️⃣ ملفات إضافية

**Procfile:**
```
web: python aba_alkhail_bot.py
```

**runtime.txt:**
```
python-3.11.7
```

---

## 🎯 كيف يشتغل البوت:

### للمهندس:
1. يكتب `/start`
2. يختار القسم (4 أزرار)
3. يشوف الرخص بتاعته
4. يختار رخصة
5. يختار قبول أو رفض
6. يكتب ملاحظات
7. يرسل صور
8. البوت ينشئ PDF ويرسله

### ليك أنت:
- تستقبل الـ PDF مباشرة في التليجرام
- اسم الـ PDF = رقم الرخصة (مثلاً: `123456.pdf`)
- تحفظه في Drive

---

## ⚠️ ملاحظات مهمة:

- الشيت بتاعتك لازم تكون متاحة للكل (عام)
- رقم التليجرام بتاعك لازم صحيح ✅
- البوت بينقرأ من الشيت كل مرة يفتح المستخدم البوت
- الصور بتنحفظ مؤقتاً في الـ server

---

## 🔧 تعديلات مستقبلية:

- إضافة Word templates (للقبول والرفض)
- تحويل الصور للـ PDF بشكل احترافي
- رفع الـ PDF تلقائياً على Google Drive
- إضافة قاعدة بيانات لحفظ السجلات

---

## 📞 إذا حصلت مشاكل:

1. شيك الـ Logs في Render
2. تأكد من Token بتاعك صحيح
3. تأكد من رقم Chat ID صحيح
4. الشيت بتاعتك متاحة للكل؟

