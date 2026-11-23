"""تطبيق المؤقت الزمني وساعة الإيقاف — نسخة الأندرويد (Kivy)
=========================================================
إعادة بناء لتطبيق سطح المكتب بنفس المحركات المُختبرة (timer_engines.py) وواجهة
مخصصة للأندرويد:
  - عدّاد تنازلي بأوقات جاهزة ومؤقتات محفوظة باسم (حفظ/تشغيل/حذف بالنقر المطوّل).
  - ساعة إيقاف بمه عالية الدقة وتسجيل لفات مع تمييز الأسرع والأبطأ.
  - تنبيه صوتي مولّد برمجياً مع تكرار تلقائي.
  - وضع داكن/فاتح وإعدادات محفوظة بين الجلسات.
"""

import json
import math
import os
import wave
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle
from kivy.metrics import dp
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

from timer_engines import (
    CountdownEngine,
    StopwatchEngine,
    format_hms,
    format_stopwatch,
    split_hms,
)

# -----------------------------------------------------------------------------
# دعم اللغة العربية: Kivy لا يُشكّل الحروف العربية أو يطبّق اتجاه RTL تلقائياً،
# لذا نستخدم arabic_reshaper + python-bidi (مُدرجة في buildozer requirements).
# -----------------------------------------------------------------------------

try:
    import arabic_reshaper
    from bidi.algorithm import get_display

    def ar(text: str) -> str:
        return get_display(arabic_reshaper.reshape(text))
except ImportError:
    def ar(text: str) -> str:
        return text


APP_TITLE = "المؤقت والساعة"
PRESETS_MINUTES = [1, 3, 5, 10, 15, 25, 45, 60]
MAX_CUSTOM_PRESETS = 12
MAX_SECONDS = 99 * 3600 + 59 * 60 + 59

THEMES = {
    "dark": {
        "bg": "#0B1120", "surface": "#131C31", "surface_alt": "#1A2540",
        "border": "#263554", "text": "#F8FAFC", "text_muted": "#94A3B8",
        "text_dim": "#64748B", "track": "#1E293B",
        "primary": "#10B981", "primary_hover": "#059669",
        "sky": "#0EA5E9", "danger": "#EF4444", "danger_hover": "#DC2626",
        "secondary": "#1E293B", "secondary_text": "#E2E8F0",
    },
    "light": {
        "bg": "#F1F5F9", "surface": "#FFFFFF", "surface_alt": "#F8FAFC",
        "border": "#CBD5E1", "text": "#0F172A", "text_muted": "#475569",
        "text_dim": "#64748B", "track": "#E2E8F0",
        "primary": "#059669", "primary_hover": "#047857",
        "sky": "#0369A1", "danger": "#DC2626", "danger_hover": "#B91C1C",
        "secondary": "#E2E8F0", "secondary_text": "#1E293B",
    },
}


def hex_to_rgba(value: str) -> tuple:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)


def _round_rect(canvas, x: float, y: float, w: float, h: float, r: float) -> None:
    """إضافة تعليمات مستطيل بزوايا مستديرة إلى canvas (داخل with canvas:)."""
    r = max(0.0, min(r, w / 2.0, h / 2.0))
    if r < 0.5:
        canvas.add(Rectangle(pos=(x, y), size=(w, h)))
        return
    from kivy.graphics import Ellipse as _E
    d = 2.0 * r
    canvas.add(_E(pos=(x, y), size=(d, d)))
    canvas.add(_E(pos=(x + w - d, y), size=(d, d)))
    canvas.add(_E(pos=(x, y + h - d), size=(d, d)))
    canvas.add(_E(pos=(x + w - d, y + h - d), size=(d, d)))
    canvas.add(Rectangle(pos=(x + r, y), size=(w - d, h)))
    canvas.add(Rectangle(pos=(x, y + r), size=(w, h - d)))


# =============================================================================
# 1. عناصر واجهة مخصصة
# =============================================================================

class FlatButton(ButtonBehavior, Label):
    """زر مسطح بألوان ثيم قابلة للتغيير أثناء التشغيل."""

    bg_color = StringProperty("#10B981")
    fg_color = StringProperty("#FFFFFF")
    border_color = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bold = True
        self.halign = "center"
        self.valign = "middle"
        self.padding = (dp(6), dp(6))
        self._hover_color = self.bg_color
        for prop in ("pos", "size", "bg_color", "fg_color", "border_color", "text"):
            self.bind(**{prop: self._redraw})
        self.bind(state=self._redraw)

    def set_scheme(self, bg: str, hover: str, fg: str, border: str = "") -> None:
        self.bg_color = bg
        self._hover_color = hover
        self.fg_color = fg
        self.border_color = border
        self._redraw()

    def _redraw(self, *args) -> None:
        self.canvas.clear()
        fill = self._hover_color if (self.state == "down" and self._hover_color) else self.bg_color
        radius = dp(10)
        with self.canvas:
            Color(*hex_to_rgba(fill))
            _round_rect(self.canvas, self.x, self.y, self.width, self.height, radius)
            if self.border_color:
                Color(*hex_to_rgba(self.border_color))
                Line(
                    rounded_rectangle=(self.x, self.y, self.width, self.height, radius),
                    width=1.0,
                )
        self.color = hex_to_rgba(self.fg_color)


class Gauge(Widget):
    """قرص دائري متدرج مع نص الوقت في المنتصف."""

    progress = NumericProperty(1.0)
    main_text = StringProperty("")
    sub_text = StringProperty("")
    accent = StringProperty("#10B981")
    track_color = StringProperty("#1E293B")
    main_color = StringProperty("#F8FAFC")
    sub_color = StringProperty("#64748B")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.main_label = Label(font_size=dp(34), bold=True)
        self.sub_label = Label(font_size=dp(13))
        self.add_widget(self.main_label)
        self.add_widget(self.sub_label)
        for prop in ("pos", "size", "progress", "main_text", "sub_text",
                     "accent", "track_color", "main_color", "sub_color"):
            self.bind(**{prop: self._redraw})

    def _redraw(self, *args) -> None:
        self.canvas.clear()
        cx, cy = self.center_x, self.center_y
        radius = min(self.width, self.height) / 2.0 - dp(12)
        with self.canvas:
            Color(*hex_to_rgba(self.track_color))
            Line(circle=(cx, cy, radius), width=dp(10), cap="round")
            if self.progress > 0.004:
                Color(*hex_to_rgba(self.accent))
                start = 90.0
                sweep = -360.0 * max(0.01, min(1.0, self.progress))
                segments = max(2, int(abs(sweep) / 5))
                step = sweep / segments
                cur = start
                for _ in range(segments):
                    Line(circle=(cx, cy, radius, cur + step, cur), width=dp(10), cap="round")
                    cur += step
        self.main_label.color = hex_to_rgba(self.main_color)
        self.sub_label.color = hex_to_rgba(self.sub_color)
        self.main_label.text = self.main_text
        self.sub_label.text = self.sub_text
        self.main_label.center = (cx, cy + dp(8))
        self.sub_label.center = (cx, cy - dp(26))


def section_label(text: str) -> Label:
    lb = Label(
        text=ar(text), font_size=dp(12), bold=True,
        size_hint=(1, None), height=dp(20), halign="right", valign="middle",
    )
    lb.bind(size=lambda inst, s: setattr(inst, "text_size", (s[0], s[1])))
    return lb


class PresetChip(ButtonBehavior, BoxLayout):
    """زر المؤقت المحفوظ: نقرة للتشغيل، نقرة مطوّلة للحذف."""

    LONG_PRESS_DELAY = 0.8

    def __init__(self, preset: dict, app_root: "TimerRoot", **kwargs):
        super().__init__(orientation="horizontal", size_hint=(None, 1), **kwargs)
        self.preset = preset
        self.app_root = app_root
        self._press_event = None
        self._long_fired = False

        name = preset["name"]
        dur = app_root.format_duration_short(preset["seconds"])
        self.add_widget(Label(text=f"{name} ({dur})", font_size=dp(12), bold=True))
        x_label = Label(text="✕", font_size=dp(12), bold=True, size_hint=(None, 1), width=dp(16))
        self.add_widget(x_label)
        for prop in ("pos", "size"):
            self.bind(**{prop: self._redraw_background})

    def _redraw_background(self, *args) -> None:
        theme = THEMES[self.app_root.theme_name]
        self.canvas.clear()
        with self.canvas:
            Color(*hex_to_rgba(theme["surface_alt"] if self.state != "down" else theme["surface"]))
            _round_rect(self.canvas, self.x, self.y, self.width, self.height, dp(9))

    def on_press(self):
        self._long_fired = False
        self._press_event = Clock.schedule_once(self._fire_long, self.LONG_PRESS_DELAY)

    def on_release(self):
        if self._press_event is not None:
            self._press_event.cancel()
            self._press_event = None
        if not self._long_fired:
            self.app_root.apply_custom_preset(self.index)

    def _fire_long(self, dt):
        self._long_fired = True
        self._press_event = None
        self.app_root.delete_custom_preset(self.index)

    @property
    def index(self) -> int:
        try:
            return self.app_root.custom_presets.index(self.preset)
        except ValueError:
            return -1


# =============================================================================
# 2. واجهة التطبيق
# =============================================================================

class TimerRoot(BoxLayout):

    def __init__(self, app: "ArabicTimerApp", **kwargs):
        super().__init__(orientation="vertical", padding=dp(14), spacing=dp(8), **kwargs)
        self.app = app

        self.countdown = CountdownEngine(initial_seconds=300)
        self.stopwatch = StopwatchEngine()
        self.theme_name = "dark"
        self.custom_presets: list = []
        self.alarm_enabled = True
        self.continuous_alarm = False
        self.active_mode = "countdown"
        self.alarm_ringing = False
        self._press_event = None

        settings = app.load_raw_settings()
        self._consume_settings(settings)

        self._build_static()
        self._build_countdown_view()
        self._build_stopwatch_view()
        self._show_active_view()
        self.sync_countdown_entries()
        self.apply_theme()
        self._ticker = Clock.schedule_interval(self._tick, 1 / 30.0)

    # ---------------- الثيم ----------------

    def _consume_settings(self, data: dict) -> None:
        if data.get("theme") in THEMES:
            self.theme_name = data["theme"]
        self.alarm_enabled = bool(data.get("alarm_enabled", True))
        self.continuous_alarm = bool(data.get("continuous_alarm", False))
        self.countdown.auto_repeat = bool(data.get("auto_repeat", False))
        if data.get("active_mode") in ("countdown", "stopwatch"):
            self.active_mode = data["active_mode"]
        try:
            last = float(data.get("last_duration", 300))
            self.countdown.set_total_seconds(last)
        except (TypeError, ValueError):
            self.countdown.set_total_seconds(300)
        raw = data.get("custom_presets", [])
        presets = []
        if isinstance(raw, list):
            for item in raw:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name", "")).strip()[:40]
                if not name:
                    continue
                try:
                    seconds = int(item.get("seconds", 0))
                except (TypeError, ValueError):
                    continue
                presets.append({"name": name, "seconds": max(1, min(seconds, MAX_SECONDS))})
                if len(presets) >= MAX_CUSTOM_PRESETS:
                    break
        self.custom_presets = presets

    def t(self, key: str) -> str:
        return THEMES[self.theme_name][key]

    def toggle_theme(self, *args) -> None:
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self.apply_theme()
        self.app.save_settings()

    def apply_theme(self, *args) -> None:
        try:
            Window.clearcolor = hex_to_rgba(self.t("bg"))
        except Exception:
            pass
        self._style_label(self.title_label, self.t("text"))
        for lb in (self.quick_title, self.saved_title, self.picker_title, self.laps_title):
            self._style_label(lb, self.t("text_muted"))

        mode = self.active_mode
        self.btn_mode_cd.set_scheme(
            self.t("primary") if mode == "countdown" else self.t("secondary"),
            self.t("primary_hover") if mode == "countdown" else self.t("secondary"),
            "#FFFFFF" if mode == "countdown" else self.t("secondary_text"),
        )
        self.btn_mode_sw.set_scheme(
            self.t("primary") if mode == "stopwatch" else self.t("secondary"),
            self.t("primary_hover") if mode == "stopwatch" else self.t("secondary"),
            "#FFFFFF" if mode == "stopwatch" else self.t("secondary_text"),
        )

        muted = not self.alarm_enabled
        self.mute_btn.set_scheme(
            self.t("danger") if muted else self.t("secondary"),
            self.t("danger_hover") if muted else self.t("secondary"),
            "#FFFFFF",
        )
        self.mute_btn.text = ar("مكتوم ✓") if muted else ar("الصوت")
        self.theme_btn.text = ar("فاتح ✓") if self.theme_name == "dark" else ar("داكن ✓")
        self.theme_btn.set_scheme(self.t("secondary"), self.t("secondary"), self.t("secondary_text"))

        for b in self.quick_buttons:
            b.set_scheme(self.t("surface_alt"), self.t("surface_alt"),
                         self.t("text"), self.t("border"))
        self.btn_add_min.set_scheme(self.t("secondary"), self.t("secondary"), self.t("secondary_text"))
        self.btn_reset.set_scheme(self.t("secondary"), self.t("secondary"), self.t("secondary_text"))
        self.btn_save_preset.set_scheme(self.t("sky"), self.t("sky"), "#FFFFFF")
        self.btn_lap.set_scheme(self.t("sky"), self.t("sky"), "#FFFFFF")
        self.btn_sw_reset.set_scheme(self.t("secondary"), self.t("secondary"), self.t("secondary_text"))

        if self.stopwatch.running:
            self.btn_sw_toggle.set_scheme(self.t("secondary"), self.t("secondary"), "#FFFFFF")
            self.btn_sw_toggle.text = ar("إيقاف مؤقت")
        else:
            self.btn_sw_toggle.set_scheme(self.t("primary"), self.t("primary_hover"), "#FFFFFF")
            self.btn_sw_toggle.text = ar("ابدأ")

        if self.alarm_ringing:
            self.btn_start.set_scheme(self.t("danger"), self.t("danger_hover"), "#FFFFFF")
            self.btn_start.text = ar("إيقاف التنبيه")
        elif self.countdown.running:
            self.btn_start.set_scheme(self.t("secondary"), self.t("secondary"), "#FFFFFF")
            self.btn_start.text = ar("إيقاف مؤقت")
        else:
            self.btn_start.set_scheme(self.t("primary"), self.t("primary_hover"), "#FFFFFF")
            self.btn_start.text = ar("ابدأ")

        self.cd_gauge.accent = self.t("danger") if self.alarm_ringing else self.t("primary")
        self.sw_gauge.accent = self.t("sky")
        for g in (self.cd_gauge, self.sw_gauge):
            g.track_color = self.t("track")
            g.main_color = self.t("text")
            g.sub_color = self.t("text_dim")

        for entry in [self.entry_note] + self.entries:
            entry.background_color = hex_to_rgba(self.t("surface"))
            entry.foreground_color = hex_to_rgba(self.t("text"))
            entry.cursor_color = hex_to_rgba(self.t("primary"))
            entry.hint_text_color = hex_to_rgba(self.t("text_dim"))

        for chip in list(self.saved_grid.children):
            if isinstance(chip, PresetChip):
                chip._redraw_background()
        for lb in getattr(self, "lap_labels", []):
            base = self.t("text")
            self._style_label(lb, getattr(lb, "theme_color", base))

    @staticmethod
    def _style_label(label: Label, color: str) -> None:
        label.color = hex_to_rgba(color)

    # ---------------- بناء الهيكل ----------------

    def _build_static(self) -> None:
        header = BoxLayout(size_hint=(1, None), height=dp(46))
        self.title_label = Label(
            text=ar("المؤقت والساعة"), font_size=dp(20), bold=True,
            size_hint=(1, 1), halign="right", valign="middle",
        )
        self.title_label.bind(size=lambda inst, s: setattr(inst, "text_size", (s[0], s[1])))
        self.mute_btn = FlatButton(text=ar("الصوت"), size_hint=(None, None), size=(dp(84), dp(38)))
        self.mute_btn.bind(on_release=self._on_mute)
        self.theme_btn = FlatButton(text=ar("فاتح ✓"), size_hint=(None, None), size=(dp(84), dp(38)))
        self.theme_btn.bind(on_release=self.toggle_theme)
        header.add_widget(self.title_label)
        header.add_widget(self.mute_btn)
        header.add_widget(self.theme_btn)
        self.add_widget(header)

        mode_row = BoxLayout(size_hint=(1, None), height=dp(44), spacing=dp(6))
        self.btn_mode_cd = FlatButton(text=ar("المؤقت التنازلي"))
        self.btn_mode_cd.bind(on_release=lambda *a: self.switch_mode("countdown"))
        self.btn_mode_sw = FlatButton(text=ar("ساعة الإيقاف"))
        self.btn_mode_sw.bind(on_release=lambda *a: self.switch_mode("stopwatch"))
        mode_row.add_widget(self.btn_mode_cd)
        mode_row.add_widget(self.btn_mode_sw)
        self.add_widget(mode_row)

        self.view_holder = BoxLayout()
        self.add_widget(self.view_holder)

    def switch_mode(self, mode: str) -> None:
        if self.active_mode == mode:
            return
        self.active_mode = mode
        self._show_active_view()
        self.app.save_settings()

    def _show_active_view(self) -> None:
        self.view_holder.clear_widgets()
        self.view_holder.add_widget(self.cd_view if self.active_mode == "countdown" else self.sw_view)
        self.apply_theme()

    def _on_mute(self, *args) -> None:
        self.alarm_enabled = not self.alarm_enabled
        if not self.alarm_enabled:
            self.dismiss_alarm()
        self.apply_theme()
        self.app.save_settings()

    # ---------------- تبويب المؤقت ----------------

    def _build_countdown_view(self) -> None:
        view = BoxLayout(orientation="vertical", spacing=dp(8))

        self.entry_note = TextInput(
            multiline=False, font_size=dp(15), size_hint=(1, None), height=dp(42),
            background_normal="", background_active="",
            hint_text=ar("اسم الجلسة (اختياري)"),
        )
        view.add_widget(self.entry_note)

        gauge_holder = BoxLayout(size_hint=(1, 1))
        self.cd_gauge = Gauge(size_hint=(None, None), size=(dp(230), dp(230)),
                              pos_hint={"center_x": 0.5, "center_y": 0.5})
        gauge_holder.add_widget(self.cd_gauge)
        view.add_widget(gauge_holder)

        controls = BoxLayout(size_hint=(1, None), height=dp(50), spacing=dp(6))
        self.btn_add_min = FlatButton(text=ar("+1 دقيقة"))
        self.btn_add_min.bind(on_release=lambda *a: self.cd_add_minute())
        self.btn_reset = FlatButton(text=ar("إعادة تعيين"))
        self.btn_reset.bind(on_release=lambda *a: self.cd_reset())
        self.btn_start = FlatButton(text=ar("ابدأ"))
        self.btn_start.bind(on_release=lambda *a: self.cd_primary())
        controls.add_widget(self.btn_add_min)
        controls.add_widget(self.btn_reset)
        controls.add_widget(self.btn_start)
        view.add_widget(controls)

        self.quick_title = section_label("أوقات جاهزة سريعة")
        view.add_widget(self.quick_title)
        quick_grid = GridLayout(
            cols=4, size_hint=(1, None), height=dp(2 * 38 + 8), spacing=dp(4),
        )
        self.quick_buttons = []
        for mins in PRESETS_MINUTES:
            b = FlatButton(text=ar(f"{mins} دق"))
            b.bind(on_release=lambda *a, m=mins: self.apply_quick_preset(m))
            quick_grid.add_widget(b)
            self.quick_buttons.append(b)
        view.add_widget(quick_grid)

        self.saved_title = section_label("المؤقتات المحفوظة — نقرة للتشغيل، نقرة مطوّلة للحذف")
        view.add_widget(self.saved_title)
        saved_row = BoxLayout(size_hint=(1, None), height=dp(36), spacing=dp(4))
        self.btn_save_preset = FlatButton(text=ar("حفظ"), size_hint=(None, 1), width=dp(64))
        self.btn_save_preset.bind(on_release=lambda *a: self.open_save_preset_popup())
        saved_row.add_widget(self.btn_save_preset)
        self.saved_scroll = ScrollView(
            size_hint=(1, 1), bar_width=0, do_scroll_x=True, do_scroll_y=False,
        )
        self.saved_grid = GridLayout(
            cols=None, size_hint=(None, 1), spacing=dp(4),
            row_default_height=dp(32),
        )
        self.saved_grid.bind(minimum_width=lambda inst, w: setattr(inst, "width", w))
        self.saved_scroll.add_widget(self.saved_grid)
        saved_row.add_widget(self.saved_scroll)
        view.add_widget(saved_row)
        self.rebuild_saved_presets()

        self.picker_title = section_label("ضبط الوقت")
        view.add_widget(self.picker_title)
        picker = BoxLayout(size_hint=(1, None), height=dp(96), spacing=dp(8))
        self.var_h = TextInput(multiline=False, input_filter="int", text="00", font_size=dp(22), size_hint=(1, None), height=dp(44), background_normal="", background_active="", halign="center")
        self.var_m = TextInput(multiline=False, input_filter="int", text="05", font_size=dp(22), size_hint=(1, None), height=dp(44), background_normal="", background_active="", halign="center")
        self.var_s = TextInput(multiline=False, input_filter="int", text="00", font_size=dp(22), size_hint=(1, None), height=dp(44), background_normal="", background_active="", halign="center")
        self.entries = [self.var_h, self.var_m, self.var_s]
        for e in self.entries:
            e.bind(focus=self._commit_on_blur)
        for i, (caption, entry) in enumerate(zip(["ساعات", "دقائق", "ثواني"], self.entries)):
            col = BoxLayout(orientation="vertical", spacing=dp(2))
            lb = Label(text=ar(caption), font_size=dp(11), size_hint=(1, None), height=dp(16))
            lb.color = hex_to_rgba(self.t("text_muted"))
            lb.theme_color_key = "text_muted"
            col.add_widget(lb)
            entry.color = hex_to_rgba(self.t("text"))
            col.add_widget(entry)
            steps = BoxLayout(size_hint=(1, None), height=dp(26), spacing=dp(2))
            up = FlatButton(text="+", font_size=dp(15))
            up.bind(on_release=lambda *a, u=i, d=1: self.cd_step(u, d))
            dn = FlatButton(text="-", font_size=dp(15))
            dn.bind(on_release=lambda *a, u=i, d=-1: self.cd_step(u, d))
            steps.add_widget(dn)
            steps.add_widget(up)
            col.add_widget(steps)
            picker.add_widget(col)
            if i < 2:
                sep = Label(text=":", font_size=dp(20), bold=True,
                            size_hint=(None, 1), width=dp(12))
                sep.theme_color_key = "text_muted"
                sep.color = hex_to_rgba(self.t("text_muted"))
                picker.add_widget(sep)
        view.add_widget(picker)

        self.cd_view = view

    def _commit_on_blur(self, instance, focused) -> None:
        if not focused:
            self.commit_entries()

    # ---------------- تبويب ساعة الإيقاف ----------------

    def _build_stopwatch_view(self) -> None:
        view = BoxLayout(orientation="vertical", spacing=dp(8))

        gauge_holder = BoxLayout(size_hint=(1, None), height=dp(230))
        self.sw_gauge = Gauge(size_hint=(None, None), size=(dp(230), dp(230)),
                              pos_hint={"center_x": 0.5, "center_y": 0.5})
        gauge_holder.add_widget(self.sw_gauge)
        view.add_widget(gauge_holder)

        controls = BoxLayout(size_hint=(1, None), height=dp(50), spacing=dp(6))
        self.btn_sw_toggle = FlatButton(text=ar("ابدأ"))
        self.btn_sw_toggle.bind(on_release=lambda *a: self.sw_toggle())
        self.btn_lap = FlatButton(text=ar("لفة"))
        self.btn_lap.bind(on_release=lambda *a: self.sw_lap())
        self.btn_sw_reset = FlatButton(text=ar("إعادة تعيين"))
        self.btn_sw_reset.bind(on_release=lambda *a: self.sw_reset())
        controls.add_widget(self.btn_sw_toggle)
        controls.add_widget(self.btn_lap)
        controls.add_widget(self.btn_sw_reset)
        view.add_widget(controls)

        self.laps_title = section_label("اللفات — الأسرع والأبطأ مميّزان بالألوان")
        view.add_widget(self.laps_title)

        self.laps_scroll = ScrollView(bar_width=dp(4))
        self.laps_grid = GridLayout(
            cols=1, size_hint_y=None, spacing=dp(4), padding=[0, 0, 0, dp(4)],
            row_default_height=dp(28),
        )
        self.laps_grid.bind(minimum_height=lambda inst, h: setattr(inst, "height", h))
        self.laps_scroll.add_widget(self.laps_grid)
        view.add_widget(self.laps_scroll)
        self._refresh_laps_list()
        self.sw_view = view

    def sw_toggle(self) -> None:
        self.stopwatch.toggle()
        self.apply_theme()

    def sw_reset(self) -> None:
        self.stopwatch.reset()
        self._refresh_laps_list()
        self.apply_theme()

    def sw_lap(self) -> None:
        if not self.stopwatch.running and self.stopwatch.elapsed() <= 0:
            return
        if self.stopwatch.record_lap():
            self._refresh_laps_list()

    def average_lap_label(self):
        avg = self.stopwatch.average_lap()
        return (ar("المتوسط:") + " " + format_hms(avg)) if avg else ""

    def _refresh_laps_list(self) -> None:
        self.laps_grid.clear_widgets()
        self.lap_labels = []
        if not self.stopwatch.laps:
            hint = Label(
                text=ar("ابدأ التشغيل ثم اضغط «لفة» لتسجيل اللفات"),
                font_size=dp(12), size_hint=(1, None), height=dp(28),
                color=hex_to_rgba(self.t("text_dim")),
            )
            self.laps_grid.add_widget(hint)
            return
        fastest, slowest = self.stopwatch.fastest_and_slowest_indices()
        for rec in reversed(self.stopwatch.laps):
            text = f"{ar('لفة')} {rec.index}  {format_hms(rec.lap_seconds)}  ({format_hms(rec.total_seconds)})"
            color_key = "text"
            if fastest is not None and rec.index == fastest:
                text += " " + ar("أسرع")
                color_key = "primary"
            elif slowest is not None and rec.index == slowest:
                text += " " + ar("أبطأ")
                color_key = "danger"
            lb = Label(
                text=text, font_size=dp(13), size_hint=(1, None), height=dp(26),
                color=hex_to_rgba(self.t(color_key)), halign="right", valign="middle",
            )
            lb.text_size = (self.laps_grid.width - dp(8), lb.height)
            lb.theme_color = self.t(color_key)
            self.laps_grid.add_widget(lb)
            self.lap_labels.append(lb)

    # ---------------- منطق المؤقت ----------------

    def _parse_entries(self):
        def read(entry):
            digits = "".join(ch for ch in entry.text if ch.isdigit())
            return int(digits) if digits else 0
        h = min(read(self.var_h), 99)
        m = min(read(self.var_m), 59)
        s = min(read(self.var_s), 59)
        if h == 0 and m == 0 and s == 0:
            s = 1
        return h, m, s

    def commit_entries(self) -> None:
        if self.countdown.running:
            self.sync_countdown_entries()
            return
        h, m, s = self._parse_entries()
        self.countdown.set_duration(h, m, s)
        self.dismiss_alarm()
        self.sync_countdown_entries()
        self.apply_theme()
        self.app.save_settings()

    def cd_step(self, unit_index: int, delta: int) -> None:
        if self.countdown.running:
            return
        h, m, s = self._parse_entries()
        if unit_index == 0:
            h = (h + delta) % 100
        elif unit_index == 1:
            m = (m + delta) % 60
        else:
            s = (s + delta) % 60
        h, m, s = max(0, h), max(0, m), max(0, s)
        if h == 0 and m == 0 and s == 0:
            s = 1
        self.countdown.set_duration(h, m, s)
        self.dismiss_alarm()
        self.sync_countdown_entries()
        self.apply_theme()
        self.app.save_settings()

    def cd_add_minute(self) -> None:
        self.dismiss_alarm()
        self.countdown.add_seconds(60)
        if not self.countdown.running:
            self.sync_countdown_entries()

    def cd_primary(self) -> None:
        if self.alarm_ringing:
            self.dismiss_alarm()
            return
        if not self.countdown.running:
            h, m, s = self._parse_entries()
            entered = h * 3600 + m * 60 + s
            if entered > 0 and abs(entered - self.countdown.total_seconds) >= 1:
                self.countdown.set_duration(h, m, s)
                self.sync_countdown_entries()
            self.countdown.start()
        else:
            self.countdown.pause()
        self.apply_theme()

    def cd_reset(self) -> None:
        self.dismiss_alarm()
        self.countdown.reset()
        self.sync_countdown_entries()
        self.apply_theme()

    def sync_countdown_entries(self) -> None:
        h, m, s = split_hms(self.countdown.total_seconds)
        for entry, value in zip(self.entries, (h, m, s)):
            entry.text = f"{value:02d}"

    def apply_quick_preset(self, minutes: int) -> None:
        self.dismiss_alarm()
        self.countdown.set_total_seconds(minutes * 60)
        self.sync_countdown_entries()
        self.apply_theme()
        self.app.save_settings()

    # ---------------- المؤقتات المحفوظة ----------------

    def format_duration_short(self, total_seconds: float) -> str:
        secs = max(1, int(round(float(total_seconds))))
        h, m, s = split_hms(secs)
        parts = []
        if h:
            parts.append(f"{h}س")
        if m:
            parts.append(f"{m}د")
        if s or not parts:
            parts.append(f"{s}ث")
        return " و".join(parts)

    def open_save_preset_popup(self) -> None:
        seconds = int(round(self.countdown.total_seconds))
        if seconds <= 0:
            return
        default_name = self.entry_note.text.strip() or self.format_duration_short(seconds)
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        name_field = TextInput(multiline=False, text=default_name, font_size=dp(15))
        box.add_widget(name_field)
        row = BoxLayout(size_hint=(1, None), height=dp(42), spacing=dp(6))
        box.add_widget(row)
        popup = Popup(
            title=ar("اسم المؤقت"), content=box,
            size_hint=(0.85, None), height=dp(190), title_font_size=dp(15),
        )

        def confirm(_widget=None):
            popup.dismiss()
            self.confirm_save_preset(name_field.text, seconds)

        b_ok = FlatButton(text=ar("حفظ"))
        b_ok.bind(on_release=lambda *a: confirm())
        b_cancel = FlatButton(text=ar("إلغاء"))
        b_cancel.bind(on_release=lambda *a: popup.dismiss())
        row.add_widget(b_cancel)
        row.add_widget(b_ok)
        name_field.bind(on_text_validate=lambda *a: confirm())
        popup.open()
        name_field.focus = True

    def confirm_save_preset(self, name: str, seconds: int) -> None:
        name = (name or "").strip()[:40]
        if not name:
            self.app.toast(ar("يرجى إدخال اسم للمؤقت"))
            return
        existing = next((p for p in self.custom_presets if p["name"] == name), None)
        if existing is not None:
            existing["seconds"] = seconds
        else:
            if len(self.custom_presets) >= MAX_CUSTOM_PRESETS:
                self.app.toast(ar("الحد الأقصى 12 مؤقتاً محفوظاً. احذف واحداً أولاً"))
                return
            self.custom_presets.append({"name": name, "seconds": seconds})
        self.app.save_settings()
        self.rebuild_saved_presets()
        self.apply_theme()
        self.app.toast(ar("تم حفظ المؤقت ✓"))

    def rebuild_saved_presets(self) -> None:
        self.saved_grid.clear_widgets()
        if not self.custom_presets:
            hint = Label(
                text=ar("اضبط الوقت ثم اضغط «حفظ» لتخزينه بالاسم"),
                font_size=dp(11), size_hint=(None, 1), width=dp(300),
                color=hex_to_rgba(self.t("text_dim")),
            )
            hint.theme_color = self.t("text_dim")
            self.saved_grid.add_widget(hint)
            return
        for preset in self.custom_presets:
            self.saved_grid.add_widget(PresetChip(preset=preset, app_root=self))

    def apply_custom_preset(self, index: int) -> None:
        if not (0 <= index < len(self.custom_presets)):
            return
        self.dismiss_alarm()
        self.countdown.set_total_seconds(float(self.custom_presets[index]["seconds"]))
        self.sync_countdown_entries()
        self.apply_theme()
        self.app.save_settings()

    def delete_custom_preset(self, index: int) -> None:
        if not (0 <= index < len(self.custom_presets)):
            return
        name = self.custom_presets[index]["name"]
        self.app.confirm_dialog(
            f"{ar('حذف المؤقت')} «{name}» ؟",
            self._do_delete_custom_preset, index,
        )

    def _do_delete_custom_preset(self, index: int) -> None:
        if 0 <= index < len(self.custom_presets):
            del self.custom_presets[index]
            self.app.save_settings()
            self.rebuild_saved_presets()
            self.apply_theme()

    # ---------------- الحلقة الدورية والتنبيه ----------------

    def _tick(self, dt) -> None:
        if self.active_mode == "countdown":
            if self.countdown.tick():
                self.trigger_alarm()
            self.cd_gauge.progress = self.countdown.progress()
            self.cd_gauge.main_text = format_hms(self.countdown.remaining())
            self.cd_gauge.sub_text = ar("تشغيل…") if self.countdown.running else \
                (ar("انتهى!") if self.countdown.finished else ar("قائمة البرنامج"))
        else:
            whole, centis = format_stopwatch(self.stopwatch.elapsed())
            self.sw_gauge.main_text = whole
            self.sw_gauge.sub_text = centis

    def trigger_alarm(self) -> None:
        self.alarm_ringing = not self.countdown.auto_repeat
        if self.alarm_enabled:
            self.app.play_alarm(loop=(self.continuous_alarm and not self.countdown.auto_repeat))
        else:
            self.app.stop_alarm()
        self.apply_theme()

    def dismiss_alarm(self) -> None:
        was_ringing = self.alarm_ringing
        self.alarm_ringing = False
        self.app.stop_alarm()
        if was_ringing:
            self.apply_theme()


# =============================================================================
# 3. التطبيق (النغمة، التخزين، الحوارات)
# =============================================================================

class ArabicTimerApp(App):

    def build(self):
        self.title = ar(APP_TITLE)
        self.alarm_sound = None
        try:
            self.root_widget = TimerRoot(self)
            self._ensure_alarm_wav()
            return self.root_widget
        except Exception:
            return self._build_crash_screen()

    def _build_crash_screen(self):
        import traceback
        tb = traceback.format_exc()
        try:
            with open(os.path.join(self.user_data_dir, "crash.txt"), "w", encoding="utf-8") as fh:
                fh.write(tb)
        except Exception:
            pass
        from kivy.uix.scrollview import ScrollView
        box = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(4))
        with box.canvas.before:
            Color(0.02, 0.02, 0.02, 1)
            Rectangle(pos=(0, 0), size=(Window.width, Window.height))
        header = Label(
            size_hint=(1, None), height=dp(36),
            color=(1, 0.8, 0.2, 1), bold=True, font_size=dp(15),
            text="CRASH REPORT - take a screenshot and send it",
        )
        sv = ScrollView(size_hint=(1, 1))
        lb = Label(
            size_hint=(1, None),
            font_size=dp(10), color=(0.9, 0.9, 0.9, 1),
            halign="left", valign="top",
            text=tb,
        )
        lb.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
        lb.bind(texture_size=lambda inst, s: setattr(inst, "height", s[1]))
        sv.add_widget(lb)
        box.add_widget(header)
        box.add_widget(sv)
        return box

    # ---------- النغمة ----------

    def _ensure_alarm_wav(self) -> None:
        try:
            target = Path(self.user_data_dir) / "alarm.wav"
            if not target.exists():
                write_alarm_wav(target)
        except Exception:
            pass

    def play_alarm(self, loop: bool = False) -> None:
        self.stop_alarm()
        try:
            sound = SoundLoader.load(os.path.join(self.user_data_dir, "alarm.wav"))
            if sound is None:
                return
            sound.loop = bool(loop)
            sound.play()
            self.alarm_sound = sound
        except Exception:
            pass

    def stop_alarm(self) -> None:
        try:
            if self.alarm_sound is not None:
                self.alarm_sound.stop()
                self.alarm_sound.unload()
        except Exception:
            pass
        self.alarm_sound = None

    # ---------- التخزين ----------

    def settings_path(self) -> str:
        return os.path.join(self.user_data_dir, "timer_settings.json")

    def load_raw_settings(self) -> dict:
        try:
            with open(self.settings_path(), encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}

    def save_settings(self, *args) -> None:
        root = getattr(self, "root_widget", None)
        if root is None:
            return
        try:
            data = {
                "theme": root.theme_name,
                "alarm_enabled": root.alarm_enabled,
                "continuous_alarm": root.continuous_alarm,
                "auto_repeat": root.countdown.auto_repeat,
                "active_mode": root.active_mode,
                "last_duration": root.countdown.total_seconds,
                "custom_presets": root.custom_presets,
            }
            with open(self.settings_path(), "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def on_pause(self) -> bool:
        self.save_settings()
        return True

    def on_stop(self) -> None:
        self.save_settings()
        self.stop_alarm()

    # ---------- أدوات ----------

    def toast(self, message: str) -> None:
        box = Label(text=message, font_size=dp(14), padding=(dp(12), dp(12)))
        popup = Popup(
            content=box, size_hint=(0.7, None), height=dp(100),
            title="", title_size=0, separator_height=0,
        )
        Clock.schedule_once(lambda dt: popup.dismiss(), 1.4)
        popup.open()

    def confirm_dialog(self, message: str, on_yes, *args) -> None:
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(8))
        lb = Label(text=message, font_size=dp(15))
        lb.text_size = (Window.width * 0.6, None)
        box.add_widget(lb)
        row = BoxLayout(size_hint=(1, None), height=dp(42), spacing=dp(6))
        box.add_widget(row)
        popup = Popup(
            title=ar("تأكيد"), content=box,
            size_hint=(0.8, None), height=dp(170), title_font_size=dp(15),
        )
        b_yes = FlatButton(text=ar("نعم"))
        b_yes.bind(on_release=lambda *a: (popup.dismiss(), self.call_later(0.1, on_yes, *args)))
        b_no = FlatButton(text=ar("لا"))
        b_no.bind(on_release=lambda *a: popup.dismiss())
        row.add_widget(b_no)
        row.add_widget(b_yes)
        popup.open()

    def call_later(self, delay: float, func, *args) -> None:
        Clock.schedule_once(lambda dt: func(*args), delay)


def write_alarm_wav(path) -> None:
    """توليد نغمة جرس (ثلاثة نغمات متتابعة مع تلاشٍ) بلا مكتبات خارجية."""
    sample_rate = 22050
    notes = [660.0, 880.0, 1100.0]
    note_duration = 0.28
    beep = bytearray()
    for freq in notes:
        samples = int(sample_rate * note_duration)
        for i in range(samples):
            t = i / sample_rate
            envelope = 0.5 * math.exp(-6.0 * t)
            value = int(32767.0 * 0.8 * envelope * math.sin(2 * math.pi * freq * t))
            beep += int(value).to_bytes(2, "little", signed=(value < 0))
    silence = bytearray(int(sample_rate * 0.15) * 2)
    frames = bytes(beep) + bytes(silence) + bytes(beep) + bytes(silence)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(frames)


def main() -> None:
    ArabicTimerApp().run()


if __name__ == "__main__":
    main()
