# دليل مشروع Polymarket (بالعربية)

## ما الذي يفعله هذا المشروع؟
هذا المشروع عبارة عن **بوت تداول** موجه لأسواق Polymarket، ويركز على:
- جلب بيانات السوق (APIs + Orderbook).
- تطبيق منطق **Market Making** (حساب سعر عادل + سبريد).
- إدارة مخاطر أساسية.
- تخزين/تجهيز البنية لقاعدة البيانات والكاش.
- تشغيل API للمراقبة.

في حالته الحالية، أفضل طريقة للتجربة هي **Paper Mode** (محاكاة آمنة بدون تنفيذ أوامر حقيقية).

## قبل البدء (المتطلبات)
1. Python 3.10+ (يفضل 3.11 أو أحدث).
2. تثبيت الحزم:
```bash
pip install -r src/polymarket_bot/requirements.txt
```
3. ملف `.env` في جذر المشروع يحتوي على المتغيرات الأساسية.

## إعداد `.env`
تأكد أن ملف `.env` يحتوي على الأقل:
```env
POLYMARKET_API_KEY=...
POLYMARKET_API_SECRET=...
POLYMARKET_WALLET_ADDRESS=...

TRADING_MODE=paper
ENABLE_LIVE_TRADING=false
PAPER_ITERATIONS=10
PAPER_INTERVAL_SECONDS=1
PAPER_ORDER_SIZE=10
PAPER_MARKET_ID=SIM_MARKET_001
```

## خطوات التشغيل (الترتيب الصحيح)
1. ادخل لمجلد المشروع.
2. تحقق من الإعداد:
```bash
python verify_setup.py
```
3. شغّل المحاكاة الآمنة (Paper Trading):
```bash
python src/polymarket_bot/scripts/run_paper.py
```
4. ستشاهد:
- عدد دورات (ticks).
- أوامر شراء/بيع **simulated** فقط.
- تتبع تغير الـ inventory.

## تعديل سرعة/مدة المحاكاة
يمكنك تعديلها من `.env` أو من نفس الجلسة:
```bash
$env:PAPER_ITERATIONS='50'
$env:PAPER_INTERVAL_SECONDS='0.2'
python src/polymarket_bot/scripts/run_paper.py
```

## تشغيل API للمراقبة
```bash
uvicorn src.polymarket_bot.api.main:app --reload
```
بعدها افتح:
- `http://localhost:8000`
- `http://localhost:8000/health`

## وضع Live (بحذر شديد)
الوضع الحي محمي بقفل أمان. لن يبدأ إلا إذا:
```env
ENABLE_LIVE_TRADING=true
```
ثم:
```bash
python src/polymarket_bot/scripts/run_live.py
```

## ملاحظات أمان مهمة
1. لا تشارك `API_SECRET` أو private keys نهائياً.
2. إذا تم تسريب مفتاح حساس، قم بعمل **Rotate** فوراً.
3. ابدأ دائماً بـ Paper Mode قبل أي Live.

## ملخص سريع للاستخدام اليومي
1. `python verify_setup.py`
2. `python src/polymarket_bot/scripts/run_paper.py`
3. راقب النتائج وعدّل إعدادات المحاكاة.
