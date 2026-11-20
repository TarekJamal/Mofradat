# غريب القرآن — Flask + SQLite

## التشغيل على جهازك
```
pip install -r requirements.txt
python app.py        # http://localhost:5000
```
عند أول تشغيل تُبنى `gharib.db` تلقائيًا من `data/words.csv`.

## استخدام بياناتك أنت
الطريقة 1: استبدل `data/words.csv` بملفك (الأعمدة: الكلمة، الشرح، السورة اختياري).
الطريقة 2: ابنِ القاعدة بنفسك واحفظها في المشروع:
```
python import_data.py mydata.csv              # CSV أو TSV أو JSON
python import_data.py mydb.sqlite --table words --word-col word --meaning-col text
```
هذا ينتج `gharib.db`. إن وُجدت في المشروع فلن يُعاد بناؤها.
ملاحظة: الشرح الذي يحتوي فواصل يجب وضعه بين علامتي تنصيص في CSV.

## النشر على Render
1. ارفع المجلد كله على GitHub.
2. في Render: New ← Blueprint ← اختر المستودع (يقرأ `render.yaml`).
   أو New ← Web Service وضع: Build `pip install -r requirements.txt` و Start `gunicorn app:app --bind 0.0.0.0:$PORT`.
3. بعد انتهاء البناء يظهر الرابط. أي تعديل تدفعه على GitHub ينشر تلقائيًا.

## الواجهة البرمجية
- `GET /api/words` كل الكلمات
- `GET /api/search?q=...&limit=50&offset=0` بحث بدون تشكيل
- `GET /api/random?n=5` كلمات عشوائية
- `GET /health`
