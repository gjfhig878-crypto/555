# بناء تطبيق الأندرويد (APK)

مجلد `mobile/` يحتوي نسخة Kivy كاملة من التطبيق (نفس محركات التوقيت المُختبرة في `timer_app.py`).

## الخيار الأسهل: البناء تلقائياً عبر GitHub Actions

عند أي دفعة (push) تُعدّل محتويات `mobile/`، يقوم ملف
`.github/workflows/build-apk.yml` ببناء ملف APK رياضياً (debug) وترفعه
كمُخرج (artifact) باسم `arabic-timer-apk` — حمّله من صفحة تشغيل الـ workflow:
**Actions → Build Android APK → Run artifacts**.

## البناء محلياً (عبر WSL على ويندوز، أو Ubuntu تسعة أضعاف Linux)

```bash
# 1) اعتمادات النظام (Ubuntu 22.04+)
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk autoconf libtool \
    pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev \
    cmake libffi-dev libssl-dev build-essential

# 2) أدوات بايثون
pip install --user cython==0.29.36 buildozer

# 3) البناء (أول مرة ينزّل SDK/NDK ~3GB، استغرق نحو 15-40 دقيقة)
cd mobile
buildozer -v android debug

# الناتج: mobile/bin/arabictimer-1.0.0-*-debug.apk
```

ثم انقل الـ APK إلى الهاتف وثبّته (فعّل «تثبيت مصادر غير معروفة»).

للإصدار النهائي الموقّع: `buildozer android release` (يتطلب إعداد مفاتيح
التوقيع في buildozer.spec أو عبر متغيرات البيئة P4A_RELEASE_KEYSTORE...).

## ملاحظات

- المؤقت يعمل بدقة أثناء فتح التطبيق؛ عند نقله للخلفية قد يتجمد العد
  حتى عودتك إليه (أندرويد يجمّد الـ threads بدون خدمة خلفية) — الحساب
  يعاد ضبطه بدقة من `perf_counter` عند العودة.
- الإعدادات والمؤقتات المحفوظة تُخزَّن في مجلد بيانات التطبيق على الجهاز.
