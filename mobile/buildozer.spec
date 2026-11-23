[app]

# اسم التطبيق كما سيظهر على جهاز أندرويد
title = Arabic Timer

# الاسم الذي يظهر في ملفات المشروع (بدون مسافات، بالحروف اللاتينية)
package.name = arabictimer
package.domain = org.gjfhig878

# مسار مكتبة التطبيق الرئيسي
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,wav,json

# نسخة التطبيق (تُحدَّث مع كل إصدار)
version = 1.0.0

# المتطلبات: kivy للواجهة، و arabic-reshaper + python-bidi لدعم تشكيل
# الحروف العربية واتجاه RTL في Kivy.
requirements = python3,kivy==2.3.1,arabic-reshaper,python-bidi

# (os) أي ملفات/مجلدات لا تُدرج في الحزمة
# exclude_dirs = tests

# إعدادات أندرويد
orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a

# python-for-android ثابت على master؛ إصدار 2.3.1 من Kivy مطلوب لأن
# p4a يبني Python 3.14 افتراضياً ولا يتوافق مع الكود المُولَّد في Kivy 2.3.0.
p4a.branch = master

# هل تريد الإبقاء على الشاشة مضاءة أثناء تشغيل التطبيق؟
android.wakelock = False

# صلاحيات إضافية (غير مطلوبة لهذا التطبيق)
# android.permissions =

# إعدادات iOS (غير مستخدمة هنا؛ تُترك فارغة)
ios.kivy_ios_url = https://github.com/kivy/kivy-ios
ios.kivy_ios_branch = master
ios.reload_app = False

#
# Themes
#

# خلال بناء debug يتم توقيع التطبيق بمفتاح تجريبي تلقائياً.

[buildozer]

# مستوى تفصيل السجل (1 عادي، 2 مفصّل)
log_level = 2

# مجلد عمل sdk/ndk
buildozer_dir = %(here)s/.buildozer

warn_on_root = 1

# قوالب بناء جاهزة
# android.accept_sdk_license = True (يُفعّل تلقائياً عند البناء الأول)
