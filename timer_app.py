#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تطبيق المؤقت الزمني وساعة الإيقاف (عداد تصاعدي وتنازلي)
=========================================================
تطبيق سطح مكتب متكامل بلغة Python وواجهة Tkinter بدون أي مكتبات خارجية.
يعمل على أنظمة Windows و macOS و Linux، ويضم:
  1. المؤقت التنازلي (Countdown Timer):
     - حلقة تقدم دائرية متدرجة الألوان بحسب الوقت المتبقي.
     - ضبط مخصص للساعات والدقائق والثواني + أوقات جاهزة سريعة (بما فيها بومودورو 25 د).
     - مؤقتات مخصصة محفوظة بالاسم (حفظ/تشغيل/حذف) وتُحفظ مع الإعدادات بين الجلسات.
     - تنبيه صوتي مدمج (نغمة جرس متعددة الترددات مولّدة برمجياً) + إمكانية التكرار التلقائي.
  2. ساعة الإيقاف / العداد التصاعدي (Stopwatch):
     - دقة عالية بدون انحراف زمني باستخدام time.perf_counter().
     - تسجيل اللفات/الجولات مع تمييز أسرع وأبطأ لفة وحساب المتوسط.
     - تصدير سجل اللفات إلى ملف CSV أو نسخه إلى الحافظة.
  3. ميزات إضافية:
     - كلا العدادين يعملان بشكل مستقل حتى عند التبديل بين التبويبين.
     - وضع داكن ووضع فاتح، تثبيت النافذة بالأعلى، واختصارات لوحة المفاتيح.
"""

from __future__ import annotations

import csv
import ctypes
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, simpledialog
from typing import Callable, Optional
import wave


# =============================================================================
# 1. إعدادات البيئة ودعم اللغة العربية عبر المنصات
# =============================================================================

APP_TITLE_NATIVE = "المؤقت الزمني وساعة الإيقاف"
SETTINGS_FILE = Path.home() / ".arabic_timer_settings.json"


def enable_windows_dpi_awareness() -> None:
    """تفعيل دقة الشاشة العالية (HiDPI) على نظام Windows إن أمكن."""
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


class ArabicTextHelper:
    """
    معالج النصوص العربية لـ Tkinter:
    - على Windows و macOS: يعيد النص كما هو لأن النظام يدعم التشكيل والربط والاتجاه RTL تلقائياً.
    - على Linux (X11/Xft): Tk 8.6 لا يدعم ربط الحروف العربية واتجاه RTL افتراضياً،
      لذلك يقوم بتحويل الحروف إلى أشكالها المتصلة (Presentation Forms-B) وعكس الترتيب البصري
      مع الحفاظ على الأرقام والنصوص الإنجليزية بترتيبها الصحيح.
    """

    # جدول أشكال الحروف العربية: (منعزل، نهائي، ابتدائي، وسطي)
    ARABIC_FORMS: dict[str, tuple[str, Optional[str], Optional[str], Optional[str]]] = {
        "\u0621": ("\uFE80", None, None, None),          # ء
        "\u0622": ("\uFE81", "\uFE82", None, None),      # آ
        "\u0623": ("\uFE83", "\uFE84", None, None),      # أ
        "\u0624": ("\uFE85", "\uFE86", None, None),      # ؤ
        "\u0625": ("\uFE87", "\uFE88", None, None),      # إ
        "\u0626": ("\uFE89", "\uFE8A", "\uFE8B", "\uFE8C"),  # ئ
        "\u0627": ("\uFE8D", "\uFE8E", None, None),      # ا
        "\u0628": ("\uFE8F", "\uFE90", "\uFE91", "\uFE92"),  # ب
        "\u0629": ("\uFE93", "\uFE94", None, None),      # ة
        "\u062A": ("\uFE95", "\uFE96", "\uFE97", "\uFE98"),  # ت
        "\u062B": ("\uFE99", "\uFE9A", "\uFE9B", "\uFE9C"),  # ث
        "\u062C": ("\uFE9D", "\uFE9E", "\uFE9F", "\uFEA0"),  # ج
        "\u062D": ("\uFEA1", "\uFEA2", "\uFEA3", "\uFEA4"),  # ح
        "\u062E": ("\uFEA5", "\uFEA6", "\uFEA7", "\uFEA8"),  # خ
        "\u062F": ("\uFEA9", "\uFEAA", None, None),      # د
        "\u0630": ("\uFEAB", "\uFEAC", None, None),      # ذ
        "\u0631": ("\uFEAD", "\uFEAE", None, None),      # ر
        "\u0632": ("\uFEAF", "\uFEB0", None, None),      # ز
        "\u0633": ("\uFEB1", "\uFEB2", "\uFEB3", "\uFEB4"),  # س
        "\u0634": ("\uFEB5", "\uFEB6", "\uFEB7", "\uFEB8"),  # ش
        "\u0635": ("\uFEB9", "\uFEBA", "\uFEBB", "\uFEBC"),  # ص
        "\u0636": ("\uFEBD", "\uFEBE", "\uFEBF", "\uFEC0"),  # ض
        "\u0637": ("\uFEC1", "\uFEC2", "\uFEC3", "\uFEC4"),  # ط
        "\u0638": ("\uFEC5", "\uFEC6", "\uFEC7", "\uFEC8"),  # ظ
        "\u0639": ("\uFEC9", "\uFECA", "\uFECB", "\uFECC"),  # ع
        "\u063A": ("\uFECD", "\uFECE", "\uFECF", "\uFED0"),  # غ
        "\u0640": ("\u0640", "\u0640", "\u0640", "\u0640"),  # ـ تطويل
        "\u0641": ("\uFED1", "\uFED2", "\uFED3", "\uFED4"),  # ف
        "\u0642": ("\uFED5", "\uFED6", "\uFED7", "\uFED8"),  # ق
        "\u0643": ("\uFED9", "\uFEDA", "\uFEDB", "\uFEDC"),  # ك
        "\u0644": ("\uFEDD", "\uFEDE", "\uFEDF", "\uFEE0"),  # ل
        "\u0645": ("\uFEE1", "\uFEE2", "\uFEE3", "\uFEE4"),  # م
        "\u0646": ("\uFEE5", "\uFEE6", "\uFEE7", "\uFEE8"),  # ن
        "\u0647": ("\uFEE9", "\uFEEA", "\uFEEB", "\uFEEC"),  # ه
        "\u0648": ("\uFEED", "\uFEEE", None, None),      # و
        "\u0649": ("\uFEEF", "\uFEF0", None, None),      # ى
        "\u064A": ("\uFEF1", "\uFEF2", "\uFEF3", "\uFEF4"),  # ي
    }

    LAM_ALEF_LIGATURES: dict[str, tuple[str, str]] = {
        "\u0622": ("\uFEF5", "\uFEF6"),  # لآ
        "\u0623": ("\uFEF7", "\uFEF8"),  # لأ
        "\u0625": ("\uFEF9", "\uFEFA"),  # لإ
        "\u0627": ("\uFEFB", "\uFEFC"),  # لا
    }

    MIRROR_PAIRS: dict[str, str] = {
        "(": ")",
        ")": "(",
        "[": "]",
        "]": "[",
        "{": "}",
        "}": "{",
        "<": ">",
        ">": "<",
        "«": "»",
        "»": "«",
    }

    def __init__(self, force_reshape: Optional[bool] = None) -> None:
        if force_reshape is not None:
            self.needs_reshaping = force_reshape
        else:
            # Windows و macOS يشكلان العربية تلقائياً؛ Linux Xft يحتاج للمعالجة غالباً
            self.needs_reshaping = sys.platform.startswith("linux")

        self._ext_reshaper = None
        self._ext_bidi = None
        if self.needs_reshaping:
            try:
                import arabic_reshaper  # type: ignore
                from bidi.algorithm import get_display  # type: ignore

                self._ext_reshaper = arabic_reshaper
                self._ext_bidi = get_display
            except Exception:
                pass

    @staticmethod
    def _is_transparent(ch: str) -> bool:
        code = ord(ch)
        return (0x064B <= code <= 0x065F) or code == 0x0670

    @classmethod
    def _connects_next(cls, ch: str) -> bool:
        forms = cls.ARABIC_FORMS.get(ch)
        return forms is not None and forms[2] is not None

    @classmethod
    def _connects_prev(cls, ch: str) -> bool:
        forms = cls.ARABIC_FORMS.get(ch)
        return forms is not None and forms[1] is not None

    @staticmethod
    def _is_arabic_char(ch: str) -> bool:
        code = ord(ch)
        return (
            (0x0600 <= code <= 0x06FF)
            or (0x0750 <= code <= 0x077F)
            or (0xFB50 <= code <= 0xFDFF)
            or (0xFE70 <= code <= 0xFEFF)
        )

    @staticmethod
    def _is_ltr_strong(ch: str) -> bool:
        return ("A" <= ch <= "Z") or ("a" <= ch <= "z")

    @classmethod
    def reshape_arabic(cls, text: str) -> str:
        """تحويل الحروف العربية إلى أشكالها السياقية المتصلة مع دعم اللام ألف."""
        if not text:
            return text

        # استخلاص الحروف الأساسية (تجاهل التشكيل مؤقتاً أثناء تحديد الربط)
        chars = list(text)
        base_indices = [i for i, ch in enumerate(chars) if not cls._is_transparent(ch)]
        result: list[str] = []

        idx_pos = 0
        while idx_pos < len(base_indices):
            i = base_indices[idx_pos]
            ch = chars[i]

            # فحص وجود حركات بين الحرف الحالي والتالي
            prev_ch = chars[base_indices[idx_pos - 1]] if idx_pos > 0 else ""
            next_ch = chars[base_indices[idx_pos + 1]] if idx_pos + 1 < len(base_indices) else ""

            # معالجة لا / لأ / لإ / لآ
            if ch == "\u0644" and next_ch in cls.LAM_ALEF_LIGATURES:
                iso, fin = cls.LAM_ALEF_LIGATURES[next_ch]
                has_prev = cls._connects_next(prev_ch)
                result.append(fin if has_prev else iso)
                # إضافة أي تشكيل فوق الألف إن وجد
                next_i = base_indices[idx_pos + 1]
                j = next_i + 1
                while j < len(chars) and cls._is_transparent(chars[j]):
                    result.append(chars[j])
                    j += 1
                idx_pos += 2
                continue

            forms = cls.ARABIC_FORMS.get(ch)
            if forms is None:
                result.append(ch)
            else:
                iso, fin, ini, med = forms
                prev_joins = cls._connects_next(prev_ch) and (fin is not None)
                next_joins = cls._connects_prev(next_ch) and (ini is not None)

                if prev_joins and next_joins and med is not None:
                    result.append(med)
                elif prev_joins and fin is not None:
                    result.append(fin)
                elif next_joins and ini is not None:
                    result.append(ini)
                else:
                    result.append(iso)

            # إلحاق الحركات التابعة للحرف إن وجدت
            j = i + 1
            while j < len(chars) and cls._is_transparent(chars[j]):
                result.append(chars[j])
                j += 1

            idx_pos += 1

        return "".join(result)

    @classmethod
    def to_visual_rtl(cls, text: str) -> str:
        """
        تحويل السطر الذي يحتوي على عربية إلى الترتيب البصري (من اليسار لليمين للرسم)
        مع إبقاء الأرقام والكلمات الإنجليزية بترتيبها الصحيح.
        """
        if not text:
            return text

        lines = text.split("\n")
        out_lines: list[str] = []

        for line in lines:
            if not any(cls._is_arabic_char(c) for c in line):
                out_lines.append(line)
                continue

            # تقسيم السطر إلى مقاطع: LTR (أرقام/لاتيني) و RTL (عربي ومسافات وعلامات)
            runs: list[tuple[str, str]] = []
            i = 0
            n = len(line)
            while i < n:
                ch = line[i]
                # علامة + أو - أو # متبوعة برقم تعامل كجزء من مقطع الرقم
                is_signed_digit = (
                    ch in "+-#"
                    and i + 1 < n
                    and line[i + 1].isdigit()
                )
                if ch.isdigit() or cls._is_ltr_strong(ch) or is_signed_digit:
                    start = i
                    i += 1
                    while i < n:
                        c = line[i]
                        if c.isdigit() or cls._is_ltr_strong(c):
                            i += 1
                        elif (
                            c in ".:/-,"
                            and i + 1 < n
                            and (line[i + 1].isdigit() or cls._is_ltr_strong(line[i + 1]))
                        ):
                            i += 1
                        elif c == " " and i + 1 < n and cls._is_ltr_strong(line[i + 1]):
                            i += 1
                        else:
                            break
                    runs.append(("LTR", line[start:i]))
                else:
                    start = i
                    i += 1
                    while i < n:
                        c = line[i]
                        is_sd = c in "+-#" and i + 1 < n and line[i + 1].isdigit()
                        if c.isdigit() or cls._is_ltr_strong(c) or is_sd:
                            break
                        i += 1
                    runs.append(("RTL", line[start:i]))

            # في سطر RTL: الترتيب البصري يعكس ترتيب المقاطع؛
            # المقاطع RTL تُعكس حروفها (مع عكس الأقواس)، بينما المقاطع LTR تبقى كما هي
            visual_parts: list[str] = []
            for rtype, seg in reversed(runs):
                if rtype == "LTR":
                    visual_parts.append(seg)
                else:
                    # الحفاظ على الحركات ملاصقة لحرفها عند العكس
                    clusters: list[str] = []
                    for c in seg:
                        if cls._is_transparent(c) and clusters:
                            clusters[-1] += c
                        else:
                            clusters.append(cls.MIRROR_PAIRS.get(c, c))
                    visual_parts.append("".join(reversed(clusters)))
            out_lines.append("".join(visual_parts))

        return "\n".join(out_lines)

    def format(self, text: str) -> str:
        """تهيئة النص العربي للعرض الصحيح حسب نظام التشغيل."""
        if not text or not self.needs_reshaping:
            return text
        if not any(self._is_arabic_char(c) for c in text):
            return text
        if self._ext_reshaper is not None and self._ext_bidi is not None:
            try:
                reshaped = self._ext_reshaper.reshape(text)
                return self._ext_bidi(reshaped)
            except Exception:
                pass
        return self.to_visual_rtl(self.reshape_arabic(text))


# =============================================================================
# 2. محرك الصوت وتوليد نغمة التنبيه برمجياً (WAV)
# =============================================================================

def generate_chime_wav(filepath: Path) -> Path:
    """
    توليد ملف صوتي لنغمة جرس لطيفة ومتناغمة (C5 - E5 - G5 - C6)
    باستخدام مكتبة Python القياسية فقط (wave, struct, math).
    """
    sample_rate = 44100
    notes = [
        (523.25, 0.00, 0.35),  # C5
        (659.25, 0.14, 0.38),  # E5
        (783.99, 0.28, 0.42),  # G5
        (1046.50, 0.42, 0.75), # C6
    ]
    total_duration = 1.35
    total_samples = int(sample_rate * total_duration)
    buffer = [0.0] * total_samples

    for freq, start_t, dur_t in notes:
        start_idx = int(start_t * sample_rate)
        count = int(dur_t * sample_rate)
        for i in range(count):
            idx = start_idx + i
            if idx >= total_samples:
                break
            t = i / sample_rate
            # غلاف صوتي ناعم (هجوم سريع + تلاشي أسي)
            attack = min(1.0, t / 0.015)
            decay = math.exp(-4.5 * t / dur_t)
            # موجة أساسية + توافقيات خفيفة لصوت جرس دافئ
            wave_val = (
                0.70 * math.sin(2.0 * math.pi * freq * t)
                + 0.22 * math.sin(2.0 * math.pi * (freq * 2.0) * t)
                + 0.08 * math.sin(2.0 * math.pi * (freq * 3.0) * t)
            )
            buffer[idx] += 0.35 * attack * decay * wave_val

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(filepath), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(sample_rate)
        frames = bytearray()
        for sample in buffer:
            clamped = max(-0.98, min(0.98, sample))
            frames.extend(struct.pack("<h", int(clamped * 32767)))
        wf.writeframes(bytes(frames))
    return filepath


class SoundPlayer:
    """مشغل تنبيهات صوتية متوافق مع Windows و macOS و Linux بدون مكتبات خارجية."""

    def __init__(self, bell_callback: Optional[Callable[[], None]] = None) -> None:
        self._bell_callback = bell_callback
        self._wav_path = Path(tempfile.gettempdir()) / "arabic_timer_chime_v1.wav"
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self.muted = False

    def ensure_wav(self) -> Optional[Path]:
        try:
            if not self._wav_path.exists() or self._wav_path.stat().st_size < 100:
                generate_chime_wav(self._wav_path)
            return self._wav_path
        except Exception:
            return None

    def _play_once_blocking(self) -> None:
        wav_file = self.ensure_wav()
        played = False

        if sys.platform == "win32":
            try:
                import winsound  # type: ignore

                if wav_file and wav_file.exists():
                    winsound.PlaySound(str(wav_file), winsound.SND_FILENAME)
                    played = True
                else:
                    winsound.Beep(880, 350)
                    played = True
            except Exception:
                pass

        elif sys.platform == "darwin":
            afplay = shutil.which("afplay")
            if afplay and wav_file and wav_file.exists():
                proc: Optional[subprocess.Popen] = None
                try:
                    proc = subprocess.Popen(
                        [afplay, str(wav_file)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    with self._lock:
                        self._proc = proc
                    proc.wait()
                    played = (proc.returncode == 0)
                except Exception:
                    pass
                finally:
                    with self._lock:
                        if self._proc is proc:
                            self._proc = None

        else:
            # Linux / BSD
            if wav_file and wav_file.exists():
                for cmd_name, args in [
                    ("paplay", [str(wav_file)]),
                    ("pw-play", [str(wav_file)]),
                    ("aplay", ["-q", str(wav_file)]),
                    ("ffplay", ["-nodisp", "-autoexit", "-loglevel", "quiet", str(wav_file)]),
                ]:
                    cmd_path = shutil.which(cmd_name)
                    if cmd_path:
                        proc_lin: Optional[subprocess.Popen] = None
                        try:
                            proc_lin = subprocess.Popen(
                                [cmd_path] + args,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                            with self._lock:
                                self._proc = proc_lin
                            proc_lin.wait()
                            if proc_lin.returncode == 0:
                                played = True
                                break
                        except Exception:
                            pass
                        finally:
                            with self._lock:
                                if self._proc is proc_lin:
                                    self._proc = None

        if not played and self._bell_callback is not None:
            try:
                self._bell_callback()
            except Exception:
                pass

    def play(self, repeat: bool = False) -> None:
        """تشغيل نغمة التنبيه مرة واحدة أو بشكل متكرر في خيط خلفي."""
        if self.muted:
            return
        self.stop()
        self._stop_event.clear()

        def _worker() -> None:
            if not repeat:
                self._play_once_blocking()
                return
            while not self._stop_event.is_set():
                self._play_once_blocking()
                if self._stop_event.wait(0.65):
                    break

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """إيقاف أي صوت تنبيه يعمل حالياً."""
        self._stop_event.set()
        if sys.platform == "win32":
            try:
                import winsound  # type: ignore

                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                try:
                    self._proc.terminate()
                except Exception:
                    pass
                self._proc = None


# =============================================================================
# 3. محركات التوقيت الدقيقة (منفصلة عن الواجهة وسهلة الاختبار)
# =============================================================================

@dataclass
class LapRecord:
    index: int
    lap_seconds: float
    total_seconds: float


class StopwatchEngine:
    """محرك ساعة الإيقاف (العداد التصاعدي) بدون انحراف زمني."""

    def __init__(self, time_fn: Callable[[], float] = time.perf_counter) -> None:
        self._time_fn = time_fn
        self.running: bool = False
        self._accumulated: float = 0.0
        self._start_perf: Optional[float] = None
        self.laps: list[LapRecord] = []
        self._last_lap_total: float = 0.0

    def elapsed(self, now: Optional[float] = None) -> float:
        if not self.running or self._start_perf is None:
            return max(0.0, self._accumulated)
        current = self._time_fn() if now is None else now
        return max(0.0, self._accumulated + (current - self._start_perf))

    def current_lap_elapsed(self, now: Optional[float] = None) -> float:
        return max(0.0, self.elapsed(now) - self._last_lap_total)

    def start(self, now: Optional[float] = None) -> None:
        if not self.running:
            self._start_perf = self._time_fn() if now is None else now
            self.running = True

    def pause(self, now: Optional[float] = None) -> None:
        if self.running:
            self._accumulated = self.elapsed(now)
            self._start_perf = None
            self.running = False

    def toggle(self, now: Optional[float] = None) -> None:
        if self.running:
            self.pause(now)
        else:
            self.start(now)

    def reset(self) -> None:
        self.running = False
        self._accumulated = 0.0
        self._start_perf = None
        self.laps.clear()
        self._last_lap_total = 0.0

    def record_lap(self, now: Optional[float] = None) -> Optional[LapRecord]:
        total = self.elapsed(now)
        if total <= 0.0 and not self.running:
            return None
        lap_dur = max(0.0, total - self._last_lap_total)
        record = LapRecord(
            index=len(self.laps) + 1,
            lap_seconds=lap_dur,
            total_seconds=total,
        )
        self.laps.append(record)
        self._last_lap_total = total
        return record

    def fastest_and_slowest_indices(self) -> tuple[Optional[int], Optional[int]]:
        """تحديد رقم أسرع وأبطأ لفة عند وجود لفتين فأكثر."""
        if len(self.laps) < 2:
            return None, None
        fastest = min(self.laps, key=lambda r: r.lap_seconds).index
        slowest = max(self.laps, key=lambda r: r.lap_seconds).index
        if fastest == slowest:
            return None, None
        return fastest, slowest

    def average_lap(self) -> Optional[float]:
        if not self.laps:
            return None
        return sum(r.lap_seconds for r in self.laps) / len(self.laps)


class CountdownEngine:
    """محرك المؤقت التنازلي بدقة time.perf_counter() مع دعم التكرار وتعديل الوقت."""

    def __init__(
        self,
        initial_seconds: float = 300.0,
        time_fn: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._time_fn = time_fn
        self.total_seconds: float = max(1.0, float(initial_seconds))
        self._remaining_paused: float = self.total_seconds
        self._end_perf: Optional[float] = None
        self.running: bool = False
        self.finished: bool = False
        self.auto_repeat: bool = False
        self.cycles_completed: int = 0
        self.label: str = ""

    def set_duration(self, hours: int, minutes: int, seconds: int) -> float:
        total = max(0, int(hours)) * 3600 + max(0, int(minutes)) * 60 + max(0, int(seconds))
        total = min(total, 99 * 3600 + 59 * 60 + 59)
        self.total_seconds = float(max(1, total))
        self.reset()
        return self.total_seconds

    def set_total_seconds(self, total_seconds: float) -> float:
        clamped = max(1.0, min(float(total_seconds), float(99 * 3600 + 59 * 60 + 59)))
        self.total_seconds = clamped
        self.reset()
        return self.total_seconds

    def remaining(self, now: Optional[float] = None) -> float:
        if self.finished:
            return 0.0
        if not self.running or self._end_perf is None:
            return max(0.0, self._remaining_paused)
        current = self._time_fn() if now is None else now
        return max(0.0, self._end_perf - current)

    def progress(self, now: Optional[float] = None) -> float:
        """النسبة المتبقية من 1.0 (ممتلئ) إلى 0.0 (منتهي)."""
        if self.total_seconds <= 0:
            return 0.0
        return max(0.0, min(1.0, self.remaining(now) / self.total_seconds))

    def start(self, now: Optional[float] = None) -> None:
        if self.running:
            return
        current = self._time_fn() if now is None else now
        if self.finished or self._remaining_paused <= 0.0:
            self._remaining_paused = self.total_seconds
            self.finished = False
        self._end_perf = current + self._remaining_paused
        self.running = True

    def pause(self, now: Optional[float] = None) -> None:
        if self.running:
            self._remaining_paused = self.remaining(now)
            self._end_perf = None
            self.running = False

    def toggle(self, now: Optional[float] = None) -> None:
        if self.running:
            self.pause(now)
        else:
            self.start(now)

    def reset(self) -> None:
        self.running = False
        self.finished = False
        self._end_perf = None
        self._remaining_paused = self.total_seconds

    def add_seconds(self, delta: float, now: Optional[float] = None) -> None:
        """إضافة أو إنقاص ثوانٍ أثناء التوقف أو التشغيل."""
        if self.finished:
            if delta <= 0:
                return
            self.finished = False
            self._remaining_paused = min(float(delta), float(99 * 3600 + 59 * 60 + 59))
            self.total_seconds = max(self.total_seconds, self._remaining_paused)
            return

        current = self._time_fn() if now is None else now
        if self.running and self._end_perf is not None:
            rem = max(0.0, self._end_perf - current)
            new_rem = max(1.0, min(rem + delta, float(99 * 3600 + 59 * 60 + 59)))
            self._end_perf = current + new_rem
            if new_rem > self.total_seconds:
                self.total_seconds = new_rem
        else:
            new_rem = max(1.0, min(self._remaining_paused + delta, float(99 * 3600 + 59 * 60 + 59)))
            self._remaining_paused = new_rem
            if new_rem > self.total_seconds:
                self.total_seconds = new_rem

    def tick(self, now: Optional[float] = None) -> bool:
        """
        فحص تقدم المؤقت التنازلي.
        يعيد True في اللحظة التي يكتمل فيها العد إلى الصفر.
        """
        if not self.running or self._end_perf is None:
            return False
        current = self._time_fn() if now is None else now
        if current < self._end_perf:
            return False

        # انتهت الدورة!
        self.cycles_completed += 1
        if self.auto_repeat:
            self._end_perf = current + self.total_seconds
            self._remaining_paused = self.total_seconds
            self.finished = False
            self.running = True
        else:
            self._remaining_paused = 0.0
            self._end_perf = None
            self.running = False
            self.finished = True
        return True


def split_hms(total_seconds: float, ceil_mode: bool = False) -> tuple[int, int, int]:
    """تحويل الثواني إلى (ساعات، دقائق، ثوانٍ)."""
    secs = max(0.0, float(total_seconds))
    whole = int(math.ceil(secs)) if ceil_mode else int(secs)
    hours = whole // 3600
    minutes = (whole % 3600) // 60
    seconds = whole % 60
    return hours, minutes, seconds


def format_hms(total_seconds: float, ceil_mode: bool = False) -> str:
    h, m, s = split_hms(total_seconds, ceil_mode=ceil_mode)
    return f"{h:02d}:{m:02d}:{s:02d}"


def format_stopwatch(total_seconds: float) -> tuple[str, str]:
    """إرجاع (HH:MM:SS, .cc) لساعة الإيقاف."""
    secs = max(0.0, float(total_seconds))
    total_centis = int(secs * 100.0 + 1e-6)
    centis = total_centis % 100
    whole = total_centis // 100
    h = whole // 3600
    m = (whole % 3600) // 60
    s = whole % 60
    return f"{h:02d}:{m:02d}:{s:02d}", f".{centis:02d}"


# =============================================================================
# 4. السمات والألوان والعناصر الرسومية المخصصة (Canvas Widgets)
# =============================================================================

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "bg": "#0B1120",
        "surface": "#131C31",
        "surface_alt": "#1A2540",
        "surface_hover": "#233254",
        "border": "#263554",
        "text": "#F8FAFC",
        "text_muted": "#94A3B8",
        "text_dim": "#64748B",
        "track": "#1E293B",
        "primary": "#10B981",
        "primary_hover": "#059669",
        "primary_text": "#FFFFFF",
        "sky": "#38BDF8",
        "sky_hover": "#0EA5E9",
        "amber": "#F59E0B",
        "amber_hover": "#D97706",
        "danger": "#EF4444",
        "danger_hover": "#DC2626",
        "secondary": "#1E293B",
        "secondary_hover": "#2B3B55",
        "secondary_text": "#E2E8F0",
        "fastest_bg": "#064E3B",
        "fastest_fg": "#6EE7B7",
        "slowest_bg": "#4C1D24",
        "slowest_fg": "#FCA5A5",
        "entry_bg": "#0F172A",
    },
    "light": {
        "bg": "#F1F5F9",
        "surface": "#FFFFFF",
        "surface_alt": "#F8FAFC",
        "surface_hover": "#E2E8F0",
        "border": "#CBD5E1",
        "text": "#0F172A",
        "text_muted": "#475569",
        "text_dim": "#64748B",
        "track": "#E2E8F0",
        "primary": "#059669",
        "primary_hover": "#047857",
        "primary_text": "#FFFFFF",
        "sky": "#0284C7",
        "sky_hover": "#0369A1",
        "amber": "#D97706",
        "amber_hover": "#B45309",
        "danger": "#DC2626",
        "danger_hover": "#B91C1C",
        "secondary": "#E2E8F0",
        "secondary_hover": "#CBD5E1",
        "secondary_text": "#1E293B",
        "fastest_bg": "#D1FAE5",
        "fastest_fg": "#065F46",
        "slowest_bg": "#FEE2E2",
        "slowest_fg": "#991B1B",
        "entry_bg": "#F8FAFC",
    },
}


def draw_rounded_rect(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
    fill: str = "",
    outline: str = "",
    outline_width: float = 1.0,
) -> None:
    """رسم مستطيل بزوايا دائرية بدقة هندسية كاملة على Canvas."""
    w = max(1.0, x2 - x1)
    h = max(1.0, y2 - y1)
    r = max(0.0, min(radius, w / 2.0, h / 2.0))

    if fill:
        if r <= 0.5:
            canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline="")
        else:
            d = 2.0 * r
            canvas.create_oval(x1, y1, x1 + d, y1 + d, fill=fill, outline="")
            canvas.create_oval(x2 - d, y1, x2, y1 + d, fill=fill, outline="")
            canvas.create_oval(x2 - d, y2 - d, x2, y2, fill=fill, outline="")
            canvas.create_oval(x1, y2 - d, x1 + d, y2, fill=fill, outline="")
            canvas.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline="")
            canvas.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline="")

    if outline and outline_width > 0:
        if r <= 0.5:
            canvas.create_rectangle(x1, y1, x2, y2, fill="", outline=outline, width=outline_width)
        else:
            d = 2.0 * r
            canvas.create_arc(
                x1, y1, x1 + d, y1 + d,
                start=90, extent=90, style=tk.ARC, outline=outline, width=outline_width
            )
            canvas.create_arc(
                x2 - d, y1, x2, y1 + d,
                start=0, extent=90, style=tk.ARC, outline=outline, width=outline_width
            )
            canvas.create_arc(
                x2 - d, y2 - d, x2, y2,
                start=270, extent=90, style=tk.ARC, outline=outline, width=outline_width
            )
            canvas.create_arc(
                x1, y2 - d, x1 + d, y2,
                start=180, extent=90, style=tk.ARC, outline=outline, width=outline_width
            )
            canvas.create_line(x1 + r, y1, x2 - r, y1, fill=outline, width=outline_width)
            canvas.create_line(x1 + r, y2, x2 - r, y2, fill=outline, width=outline_width)
            canvas.create_line(x1, y1 + r, x1, y2 - r, fill=outline, width=outline_width)
            canvas.create_line(x2, y1 + r, x2, y2 - r, fill=outline, width=outline_width)


class RoundedButton(tk.Canvas):
    """زر حديث بزوايا دائرية يعمل بتناسق لوني تام على Windows و macOS و Linux."""

    def __init__(
        self,
        parent: tk.Widget,
        text: str,
        command: Optional[Callable[[], None]] = None,
        ar_helper: Optional[ArabicTextHelper] = None,
        width: int = 120,
        height: int = 40,
        radius: int = 12,
        bg_color: str = "#10B981",
        hover_color: str = "#059669",
        fg_color: str = "#FFFFFF",
        border_color: str = "",
        parent_bg: str = "#0B1120",
        font: tuple = ("TkDefaultFont", 11, "bold"),
        enabled: bool = True,
    ) -> None:
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent_bg,
            highlightthickness=0,
            bd=0,
            cursor="hand2" if enabled else "arrow",
        )
        self._raw_text = text
        self._ar = ar_helper
        self._command = command
        self._w = width
        self._h = height
        self._radius = radius
        self._bg_color = bg_color
        self._hover_color = hover_color
        self._fg_color = fg_color
        self._border_color = border_color
        self._parent_bg = parent_bg
        self._font = font
        self._enabled = enabled
        self._hovered = False
        self._pressed = False

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._redraw()

    def set_text(self, text: str) -> None:
        if text != self._raw_text:
            self._raw_text = text
            self._redraw()

    def set_colors(
        self,
        bg_color: Optional[str] = None,
        hover_color: Optional[str] = None,
        fg_color: Optional[str] = None,
        border_color: Optional[str] = None,
        parent_bg: Optional[str] = None,
    ) -> None:
        changed = False
        if bg_color is not None and bg_color != self._bg_color:
            self._bg_color = bg_color
            changed = True
        if hover_color is not None and hover_color != self._hover_color:
            self._hover_color = hover_color
            changed = True
        if fg_color is not None and fg_color != self._fg_color:
            self._fg_color = fg_color
            changed = True
        if border_color is not None and border_color != self._border_color:
            self._border_color = border_color
            changed = True
        if parent_bg is not None and parent_bg != self._parent_bg:
            self._parent_bg = parent_bg
            self.configure(bg=parent_bg)
            changed = True
        if changed:
            self._redraw()

    def set_enabled(self, enabled: bool) -> None:
        if self._enabled != enabled:
            self._enabled = enabled
            self.configure(cursor="hand2" if enabled else "arrow")
            self._redraw()

    def _on_enter(self, _event: tk.Event) -> None:
        if self._enabled:
            self._hovered = True
            self._redraw()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        self._pressed = False
        self._redraw()

    def _on_press(self, _event: tk.Event) -> None:
        if self._enabled:
            try:
                self.focus_set()
            except Exception:
                pass
            self._pressed = True
            self._redraw()

    def _on_release(self, event: tk.Event) -> None:
        was_pressed = self._pressed
        self._pressed = False
        self._redraw()
        if (
            self._enabled
            and was_pressed
            and self._command is not None
            and 0 <= event.x <= self._w
            and 0 <= event.y <= self._h
        ):
            self._command()

    def _redraw(self) -> None:
        self.delete("all")
        fill = self._bg_color
        fg = self._fg_color
        if not self._enabled:
            fill = self._bg_color
            fg = "#64748B"
        elif self._pressed or self._hovered:
            fill = self._hover_color

        pad = 2 if self._pressed else 1
        draw_rounded_rect(
            self,
            pad,
            pad,
            self._w - pad,
            self._h - pad,
            self._radius,
            fill=fill,
            outline=self._border_color,
            outline_width=1.0 if self._border_color else 0.0,
        )

        display_text = self._ar.format(self._raw_text) if self._ar else self._raw_text
        self.create_text(
            self._w / 2.0,
            self._h / 2.0 + (1 if self._pressed else 0),
            text=display_text,
            fill=fg,
            font=self._font,
        )


class SegmentedModeSwitch(tk.Canvas):
    """مفتاح تبديل أنيق بين وضع المؤقت التنازلي ووضع ساعة الإيقاف."""

    def __init__(
        self,
        parent: tk.Widget,
        ar_helper: ArabicTextHelper,
        on_change: Callable[[str], None],
        width: int = 380,
        height: int = 44,
        font: tuple = ("TkDefaultFont", 11, "bold"),
    ) -> None:
        super().__init__(parent, width=width, height=height, highlightthickness=0, bd=0, cursor="hand2")
        self._ar = ar_helper
        self._on_change = on_change
        self._w = width
        self._h = height
        self._font = font
        self.active_mode = "countdown"  # "countdown" | "stopwatch"
        self._countdown_active_dot = False
        self._stopwatch_active_dot = False
        self._theme = THEMES["dark"]
        self.bind("<Button-1>", self._on_click)
        self.redraw()

    def set_theme(self, theme: dict[str, str], parent_bg: str) -> None:
        self._theme = theme
        self.configure(bg=parent_bg)
        self.redraw()

    def set_mode(self, mode: str) -> None:
        if mode in ("countdown", "stopwatch") and mode != self.active_mode:
            self.active_mode = mode
            self.redraw()

    def set_running_indicators(self, countdown_running: bool, stopwatch_running: bool) -> None:
        if (
            countdown_running != self._countdown_active_dot
            or stopwatch_running != self._stopwatch_active_dot
        ):
            self._countdown_active_dot = countdown_running
            self._stopwatch_active_dot = stopwatch_running
            self.redraw()

    def _on_click(self, event: tk.Event) -> None:
        # الجانب الأيمن: المؤقت التنازلي | الجانب الأيسر: ساعة الإيقاف (ترتيب عربي طبيعي)
        chosen = "countdown" if event.x >= self._w / 2.0 else "stopwatch"
        if chosen != self.active_mode:
            self.active_mode = chosen
            self.redraw()
            self._on_change(chosen)

    def redraw(self) -> None:
        self.delete("all")
        t = self._theme
        draw_rounded_rect(
            self, 1, 1, self._w - 1, self._h - 1, 14,
            fill=t["surface_alt"], outline=t["border"], outline_width=1.0
        )

        half = self._w / 2.0
        pad = 4
        if self.active_mode == "countdown":
            x1, x2 = half + 2, self._w - pad
            pill_color = t["primary"]
        else:
            x1, x2 = pad, half - 2
            pill_color = t["sky"]

        draw_rounded_rect(self, x1, pad, x2, self._h - pad, 11, fill=pill_color)

        # نصوص التبويبين
        sw_fg = "#FFFFFF" if self.active_mode == "stopwatch" else t["text_muted"]
        cd_fg = "#FFFFFF" if self.active_mode == "countdown" else t["text_muted"]

        self.create_text(
            half * 0.5, self._h / 2.0,
            text=self._ar.format("ساعة الإيقاف (تصاعدي)"),
            fill=sw_fg,
            font=self._font,
        )
        self.create_text(
            half * 1.5, self._h / 2.0,
            text=self._ar.format("المؤقت التنازلي"),
            fill=cd_fg,
            font=self._font,
        )

        # نقطة تنبيه صغيرة عندما يعمل العداد غير الظاهر في الخلفية
        if self._stopwatch_active_dot and self.active_mode != "stopwatch":
            self.create_oval(14, self._h / 2.0 - 4, 22, self._h / 2.0 + 4, fill=t["sky"], outline="")
        if self._countdown_active_dot and self.active_mode != "countdown":
            self.create_oval(
                self._w - 22, self._h / 2.0 - 4, self._w - 14, self._h / 2.0 + 4,
                fill=t["primary"], outline=""
            )


class CircularGauge(tk.Canvas):
    """عداد دائري احترافي لعرض التقدم والوقت بدقة بصرية عالية."""

    def __init__(
        self,
        parent: tk.Widget,
        ar_helper: ArabicTextHelper,
        size: int = 264,
        ui_font: str = "TkDefaultFont",
        mono_font: str = "TkFixedFont",
    ) -> None:
        super().__init__(parent, width=size, height=size, highlightthickness=0, bd=0)
        self._ar = ar_helper
        self._size = size
        self._ui_font = ui_font
        self._mono_font = mono_font
        self._theme = THEMES["dark"]
        self._last_render_key: Optional[tuple] = None

    def set_theme(self, theme: dict[str, str], parent_bg: str) -> None:
        self._theme = theme
        self._last_render_key = None
        self.configure(bg=parent_bg)

    def render(
        self,
        progress: float,
        accent_color: str,
        status_text: str,
        main_time: str,
        sub_text: str = "",
        centis_text: str = "",
        show_ticks: bool = False,
        alert_pulse: bool = False,
    ) -> None:
        clamped = max(0.0, min(1.0, progress))
        render_key = (
            round(clamped, 3),
            accent_color,
            status_text,
            main_time,
            sub_text,
            centis_text,
            show_ticks,
            alert_pulse,
            id(self._theme),
        )
        if render_key == self._last_render_key:
            return
        self._last_render_key = render_key

        self.delete("all")
        t = self._theme
        s = self._size
        cx = cy = s / 2.0
        margin = 20
        r = (s / 2.0) - margin

        # هالة نبض عند انتهاء المؤقت
        if alert_pulse:
            self.create_oval(
                cx - r - 9, cy - r - 9, cx + r + 9, cy + r + 9,
                outline=accent_color, width=3
            )

        # خلفية القرص الداخلي
        self.create_oval(
            cx - r + 6, cy - r + 6, cx + r - 6, cy + r - 6,
            fill=t["surface_alt"], outline=""
        )

        # علامات الثواني (60 شرطة) لساعة الإيقاف
        if show_ticks:
            for tick_i in range(60):
                angle = math.radians(tick_i * 6 - 90)
                is_major = (tick_i % 5 == 0)
                r_out = r - 11
                r_in = r - (19 if is_major else 15)
                self.create_line(
                    cx + r_in * math.cos(angle),
                    cy + r_in * math.sin(angle),
                    cx + r_out * math.cos(angle),
                    cy + r_out * math.sin(angle),
                    fill=t["border"] if not is_major else t["text_dim"],
                    width=2 if is_major else 1,
                )

        # المسار الخلفي للحلقة
        self.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            outline=t["track"], width=10
        )

        # القوس النشط
        if clamped > 0.001:
            if clamped >= 0.999:
                self.create_oval(
                    cx - r, cy - r, cx + r, cy + r,
                    outline=accent_color, width=10
                )
            else:
                extent = -360.0 * clamped
                self.create_arc(
                    cx - r, cy - r, cx + r, cy + r,
                    start=90, extent=extent, style=tk.ARC,
                    outline=accent_color, width=10
                )
            # نقطة مضيئة في رأس القوس
            tip_angle = math.radians(90.0 - 360.0 * clamped)
            tip_x = cx + r * math.cos(tip_angle)
            tip_y = cy - r * math.sin(tip_angle)
            self.create_oval(
                tip_x - 6, tip_y - 6, tip_x + 6, tip_y + 6,
                fill=accent_color, outline=t["surface"], width=2
            )

        # شارة الحالة
        self.create_text(
            cx, cy - 54,
            text=self._ar.format(status_text),
            fill=accent_color,
            font=(self._ui_font, 11, "bold"),
        )

        # الأرقام الرئيسية
        self.create_text(
            cx, cy - 4 if centis_text else cy + 2,
            text=main_time,
            fill=t["text"],
            font=(self._mono_font, 30, "bold"),
        )

        # أجزاء الثانية أو النص السفلي
        if centis_text:
            self.create_text(
                cx, cy + 32,
                text=centis_text,
                fill=accent_color,
                font=(self._mono_font, 18, "bold"),
            )
            if sub_text:
                self.create_text(
                    cx, cy + 62,
                    text=self._ar.format(sub_text),
                    fill=t["text_muted"],
                    font=(self._ui_font, 10),
                )
        elif sub_text:
            self.create_text(
                cx, cy + 44,
                text=self._ar.format(sub_text),
                fill=t["text_muted"],
                font=(self._ui_font, 10),
            )


# =============================================================================
# 5. التطبيق الرئيسي (واجهة المستخدم والتفاعل الكامل)
# =============================================================================

class TimerDesktopApp:
    """واجهة تطبيق المؤقت التنازلي وساعة الإيقاف."""

    PRESETS_MINUTES = [1, 3, 5, 10, 15, 25, 45, 60]
    MAX_CUSTOM_PRESETS = 12

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.ar = ArabicTextHelper()
        self.sound = SoundPlayer(bell_callback=self._ring_tk_bell)
        self.countdown = CountdownEngine(initial_seconds=300)
        self.stopwatch = StopwatchEngine()

        self.theme_name = "dark"
        self.always_on_top = False
        self.continuous_alarm = False
        self.active_mode = "countdown"  # "countdown" | "stopwatch"
        self.alarm_ringing = False
        self._pulse_phase = 0
        self._after_id: Optional[str] = None
        self._last_laps_signature: tuple = ()
        self.custom_presets: list[dict] = []
        self.custom_preset_widgets: list[tuple[str, tk.Widget]] = []

        self._load_settings()
        self._detect_fonts()
        self._configure_window()
        self._build_ui()
        self._apply_theme()
        self._sync_inputs_from_countdown()
        self._bind_shortcuts()
        self._schedule_tick()

    def _ring_tk_bell(self) -> None:
        try:
            self.root.after(0, self.root.bell)
        except Exception:
            pass

    def _detect_fonts(self) -> None:
        available = set(tkfont.families())
        ui_candidates = [
            "Segoe UI", "SF Pro Display", "Helvetica Neue", "Geeza Pro",
            "Noto Sans Arabic", "Cairo", "Tahoma", "DejaVu Sans", "Arial"
        ]
        mono_candidates = [
            "Cascadia Mono", "Consolas", "SF Mono", "Menlo",
            "DejaVu Sans Mono", "Ubuntu Mono", "Courier New"
        ]
        self.ui_font = next((f for f in ui_candidates if f in available), "TkDefaultFont")
        self.mono_font = next((f for f in mono_candidates if f in available), "TkFixedFont")

    def _configure_window(self) -> None:
        self.root.title(APP_TITLE_NATIVE)
        w, h = 560, 800
        self.root.minsize(500, 740)
        try:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            self.root.geometry(f"{w}x{h}")

        self._set_window_icon()
        self.root.attributes("-topmost", self.always_on_top)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_window_icon(self) -> None:
        """رسم أيقونة عصرية للتطبيق برمجياً بدون الحاجة لملف صور خارجي."""
        try:
            size = 32
            img = tk.PhotoImage(width=size, height=size)
            cx = cy = (size - 1) / 2.0
            for y in range(size):
                row_colors: list[str] = []
                for x in range(size):
                    dist = math.hypot(x - cx, y - cy)
                    if 11.5 <= dist <= 14.5:
                        row_colors.append("#38BDF8")
                    elif dist < 11.5:
                        # عقرب الساعة
                        if (abs(x - cx) < 1.2 and 5 <= y <= cy) or (
                            abs(y - cy) < 1.2 and cx <= x <= 23
                        ):
                            row_colors.append("#10B981")
                        else:
                            row_colors.append("#0F172A")
                    else:
                        row_colors.append("")
                for x, col in enumerate(row_colors):
                    if col:
                        img.put(col, (x, y))
            self._icon_img = img
            self.root.iconphoto(True, self._icon_img)
        except Exception:
            pass

    def _load_settings(self) -> None:
        try:
            if SETTINGS_FILE.exists():
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                if data.get("theme") in THEMES:
                    self.theme_name = data["theme"]
                self.sound.muted = bool(data.get("muted", False))
                self.always_on_top = bool(data.get("always_on_top", False))
                self.continuous_alarm = bool(data.get("continuous_alarm", False))
                self.countdown.auto_repeat = bool(data.get("auto_repeat", False))
                if data.get("active_mode") in ("countdown", "stopwatch"):
                    self.active_mode = data["active_mode"]
                last_secs = float(data.get("last_duration", 300))
                self.countdown.set_total_seconds(last_secs)
                self.custom_presets = self._sanitize_presets(data.get("custom_presets", []))
        except Exception:
            pass

    def _save_settings(self) -> None:
        try:
            data = {
                "theme": self.theme_name,
                "muted": self.sound.muted,
                "always_on_top": self.always_on_top,
                "continuous_alarm": self.continuous_alarm,
                "auto_repeat": self.countdown.auto_repeat,
                "active_mode": self.active_mode,
                "last_duration": self.countdown.total_seconds,
                "custom_presets": self.custom_presets,
            }
            SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # بناء عناصر الواجهة
    # -------------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.main_frame = tk.Frame(self.root, padx=18, pady=14)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 1) الشريط العلوي (العنوان + أزرار الصوت/التثبيت/المظهر)
        self.header_frame = tk.Frame(self.main_frame)
        self.header_frame.pack(fill=tk.X, pady=(0, 10))

        self.header_actions = tk.Frame(self.header_frame)
        self.header_actions.pack(side=tk.LEFT)

        self.btn_theme = RoundedButton(
            self.header_actions, text="المظهر", command=self._toggle_theme,
            ar_helper=self.ar, width=78, height=32, radius=10,
            font=(self.ui_font, 9, "bold")
        )
        self.btn_theme.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_pin = RoundedButton(
            self.header_actions, text="تثبيت", command=self._toggle_topmost,
            ar_helper=self.ar, width=70, height=32, radius=10,
            font=(self.ui_font, 9, "bold")
        )
        self.btn_pin.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_mute = RoundedButton(
            self.header_actions, text="الصوت", command=self._toggle_mute,
            ar_helper=self.ar, width=78, height=32, radius=10,
            font=(self.ui_font, 9, "bold")
        )
        self.btn_mute.pack(side=tk.LEFT)

        self.title_box = tk.Frame(self.header_frame)
        self.title_box.pack(side=tk.RIGHT)
        self.lbl_title = tk.Label(
            self.title_box,
            text=self.ar.format("المؤقت الزمني"),
            font=(self.ui_font, 15, "bold"),
        )
        self.lbl_title.pack(anchor="e")
        self.lbl_subtitle = tk.Label(
            self.title_box,
            text=self.ar.format("عداد تصاعدي وتنازلي بدقة عالية"),
            font=(self.ui_font, 9),
        )
        self.lbl_subtitle.pack(anchor="e")

        # 2) مفتاح التبديل بين المؤقت التنازلي وساعة الإيقاف
        self.mode_switch = SegmentedModeSwitch(
            self.main_frame,
            ar_helper=self.ar,
            on_change=self._on_mode_change,
            width=400,
            height=44,
            font=(self.ui_font, 10, "bold"),
        )
        self.mode_switch.set_mode(self.active_mode)
        self.mode_switch.pack(pady=(0, 10))

        # 3) حاوية المحتوى المتبدل
        self.content_holder = tk.Frame(self.main_frame)
        self.content_holder.pack(fill=tk.BOTH, expand=True)

        self._build_countdown_view()
        self._build_stopwatch_view()
        self._show_active_view()

        # 4) شريط الاختصارات السفلي
        self.footer_frame = tk.Frame(self.main_frame, pady=6)
        self.footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.shortcut_labels: list[tk.Label] = []
        shortcuts = [
            ("Space", "تشغيل/إيقاف"),
            ("R", "إعادة"),
            ("L", "لفة"),
            ("M", "كتم"),
            ("1 / 2", "الوضع"),
        ]
        for idx, (key_txt, desc_txt) in enumerate(shortcuts):
            chip = tk.Frame(self.footer_frame, padx=6, pady=2)
            chip.pack(side=tk.RIGHT, padx=(0 if idx == 0 else 4, 0))
            k_lbl = tk.Label(chip, text=key_txt, font=(self.mono_font, 8, "bold"), padx=4, pady=1)
            k_lbl.pack(side=tk.LEFT, padx=(0, 4))
            d_lbl = tk.Label(chip, text=self.ar.format(desc_txt), font=(self.ui_font, 8))
            d_lbl.pack(side=tk.LEFT)
            self.shortcut_labels.extend([chip, k_lbl, d_lbl])

    def _build_countdown_view(self) -> None:
        self.cd_frame = tk.Frame(self.content_holder)

        # شريط عنوان الجلسة الاختياري
        self.cd_label_row = tk.Frame(self.cd_frame)
        self.cd_label_row.pack(pady=(0, 6))
        self.cd_note_var = tk.StringVar(value="")
        self.entry_cd_note = tk.Entry(
            self.cd_label_row,
            textvariable=self.cd_note_var,
            width=22,
            justify="center",
            relief=tk.FLAT,
            font=(self.ui_font, 10),
            bd=4,
        )
        self.entry_cd_note.pack(side=tk.LEFT, padx=(0, 6))
        self.lbl_note_hint = tk.Label(
            self.cd_label_row,
            text=self.ar.format("اسم الجلسة (اختياري):"),
            font=(self.ui_font, 9),
        )
        self.lbl_note_hint.pack(side=tk.LEFT)

        # القرص الدائري
        self.cd_gauge = CircularGauge(
            self.cd_frame,
            ar_helper=self.ar,
            size=246,
            ui_font=self.ui_font,
            mono_font=self.mono_font,
        )
        self.cd_gauge.pack(pady=(2, 10))

        # أزرار التحكم الرئيسية للمؤقت
        self.cd_controls = tk.Frame(self.cd_frame)
        self.cd_controls.pack(pady=(0, 10))

        self.btn_cd_plus_min = RoundedButton(
            self.cd_controls, text="+1 دقيقة", command=self._cd_add_minute,
            ar_helper=self.ar, width=96, height=40, radius=12,
            font=(self.ui_font, 10, "bold")
        )
        self.btn_cd_plus_min.pack(side=tk.LEFT, padx=5)

        self.btn_cd_reset = RoundedButton(
            self.cd_controls, text="إعادة تعيين", command=self._cd_reset,
            ar_helper=self.ar, width=108, height=40, radius=12,
            font=(self.ui_font, 10, "bold")
        )
        self.btn_cd_reset.pack(side=tk.LEFT, padx=5)

        self.btn_cd_start = RoundedButton(
            self.cd_controls, text="ابدأ", command=self._cd_primary_action,
            ar_helper=self.ar, width=148, height=42, radius=12,
            font=(self.ui_font, 11, "bold")
        )
        self.btn_cd_start.pack(side=tk.LEFT, padx=5)

        # بطاقة ضبط الوقت والأوقات الجاهزة
        self.cd_setup_card = tk.Frame(self.cd_frame, padx=14, pady=12)
        self.cd_setup_card.pack(fill=tk.X, pady=(0, 8))

        self.lbl_presets_title = tk.Label(
            self.cd_setup_card,
            text=self.ar.format("أوقات جاهزة سريعة"),
            font=(self.ui_font, 9, "bold"),
        )
        self.lbl_presets_title.pack(anchor="e", pady=(0, 6))

        self.presets_row = tk.Frame(self.cd_setup_card)
        self.presets_row.pack(fill=tk.X, pady=(0, 10))
        self.preset_buttons: list[RoundedButton] = []
        for mins in self.PRESETS_MINUTES:
            btn = RoundedButton(
                self.presets_row,
                text=f"{mins} د",
                command=lambda m=mins: self._cd_apply_preset(m),
                ar_helper=self.ar,
                width=52,
                height=30,
                radius=9,
                font=(self.ui_font, 9, "bold"),
            )
            btn.pack(side=tk.RIGHT, padx=2, expand=True)
            self.preset_buttons.append(btn)

        self.lbl_custom_presets_title = tk.Label(
            self.cd_setup_card,
            text=self.ar.format("المؤقتات المحفوظة"),
            font=(self.ui_font, 9, "bold"),
        )
        self.lbl_custom_presets_title.pack(anchor="e", pady=(4, 4))

        self.custom_presets_row = tk.Frame(self.cd_setup_card)
        self.custom_presets_row.pack(fill=tk.X, pady=(0, 8))
        self._rebuild_custom_presets_row()

        # منتقي الساعات : الدقائق : الثواني
        self.picker_row = tk.Frame(self.cd_setup_card)
        self.picker_row.pack(pady=(2, 6))

        self.var_hours = tk.StringVar(value="00")
        self.var_minutes = tk.StringVar(value="05")
        self.var_seconds = tk.StringVar(value="00")

        self.picker_widgets: list[tuple[tk.Label, RoundedButton, tk.Entry, RoundedButton, str]] = []
        specs = [
            ("ساعات", self.var_hours, "h", 99),
            ("دقائق", self.var_minutes, "m", 59),
            ("ثواني", self.var_seconds, "s", 59),
        ]
        for idx, (lbl_txt, var, unit_key, max_val) in enumerate(specs):
            col = tk.Frame(self.picker_row)
            col.pack(side=tk.LEFT, padx=8)
            lbl = tk.Label(col, text=self.ar.format(lbl_txt), font=(self.ui_font, 9))
            lbl.pack(pady=(0, 3))

            btn_up = RoundedButton(
                col, text="+", command=lambda u=unit_key, d=1: self._cd_step_unit(u, d),
                ar_helper=None, width=68, height=26, radius=8,
                font=(self.mono_font, 11, "bold")
            )
            btn_up.pack()

            entry = tk.Entry(
                col,
                textvariable=var,
                width=4,
                justify="center",
                relief=tk.FLAT,
                font=(self.mono_font, 16, "bold"),
                bd=4,
            )
            entry.pack(pady=4)
            entry.bind("<FocusOut>", lambda _e: self._cd_commit_entries())
            entry.bind("<Return>", lambda _e: self._cd_commit_entries())
            entry.bind(
                "<MouseWheel>",
                lambda e, u=unit_key: self._cd_step_unit(u, 1 if e.delta > 0 else -1),
            )
            entry.bind("<Button-4>", lambda _e, u=unit_key: self._cd_step_unit(u, 1))
            entry.bind("<Button-5>", lambda _e, u=unit_key: self._cd_step_unit(u, -1))

            btn_dn = RoundedButton(
                col, text="-", command=lambda u=unit_key, d=-1: self._cd_step_unit(u, d),
                ar_helper=None, width=68, height=26, radius=8,
                font=(self.mono_font, 11, "bold")
            )
            btn_dn.pack()

            self.picker_widgets.append((lbl, btn_up, entry, btn_dn, str(max_val)))
            if idx < len(specs) - 1:
                sep = tk.Label(self.picker_row, text=":", font=(self.mono_font, 18, "bold"))
                sep.pack(side=tk.LEFT, pady=(16, 0))
                if not hasattr(self, "picker_colons"):
                    self.picker_colons: list[tk.Label] = []
                self.picker_colons.append(sep)

        # خيارات إضافية (تكرار تلقائي، صوت متكرر، اختبار الصوت)
        self.cd_options_row = tk.Frame(self.cd_frame)
        self.cd_options_row.pack(fill=tk.X, pady=(2, 0))

        self.var_auto_repeat = tk.BooleanVar(value=self.countdown.auto_repeat)
        self.var_continuous_alarm = tk.BooleanVar(value=self.continuous_alarm)

        self.btn_test_sound = RoundedButton(
            self.cd_options_row, text="اختبار الصوت", command=self._test_sound,
            ar_helper=self.ar, width=106, height=30, radius=9,
            font=(self.ui_font, 9, "bold")
        )
        self.btn_test_sound.pack(side=tk.LEFT)

        self.chk_continuous = tk.Checkbutton(
            self.cd_options_row,
            text=self.ar.format("تنبيه متكرر حتى الإيقاف"),
            variable=self.var_continuous_alarm,
            command=self._on_option_toggle,
            font=(self.ui_font, 9),
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.chk_continuous.pack(side=tk.RIGHT, padx=(8, 0))

        self.chk_repeat = tk.Checkbutton(
            self.cd_options_row,
            text=self.ar.format("تكرار المؤقت تلقائياً"),
            variable=self.var_auto_repeat,
            command=self._on_option_toggle,
            font=(self.ui_font, 9),
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.chk_repeat.pack(side=tk.RIGHT, padx=(0, 8))

    def _build_stopwatch_view(self) -> None:
        self.sw_frame = tk.Frame(self.content_holder)

        self.sw_gauge = CircularGauge(
            self.sw_frame,
            ar_helper=self.ar,
            size=246,
            ui_font=self.ui_font,
            mono_font=self.mono_font,
        )
        self.sw_gauge.pack(pady=(4, 10))

        self.sw_controls = tk.Frame(self.sw_frame)
        self.sw_controls.pack(pady=(0, 10))

        self.btn_sw_reset = RoundedButton(
            self.sw_controls, text="إعادة تعيين", command=self._sw_reset,
            ar_helper=self.ar, width=108, height=40, radius=12,
            font=(self.ui_font, 10, "bold")
        )
        self.btn_sw_reset.pack(side=tk.LEFT, padx=5)

        self.btn_sw_lap = RoundedButton(
            self.sw_controls, text="تسجيل لفة", command=self._sw_record_lap,
            ar_helper=self.ar, width=108, height=40, radius=12,
            font=(self.ui_font, 10, "bold")
        )
        self.btn_sw_lap.pack(side=tk.LEFT, padx=5)

        self.btn_sw_start = RoundedButton(
            self.sw_controls, text="ابدأ", command=self._sw_toggle,
            ar_helper=self.ar, width=148, height=42, radius=12,
            font=(self.ui_font, 11, "bold")
        )
        self.btn_sw_start.pack(side=tk.LEFT, padx=5)

        # بطاقة سجل اللفات
        self.laps_card = tk.Frame(self.sw_frame, padx=12, pady=10)
        self.laps_card.pack(fill=tk.BOTH, expand=True)

        self.laps_header = tk.Frame(self.laps_card)
        self.laps_header.pack(fill=tk.X, pady=(0, 6))

        self.btn_export_laps = RoundedButton(
            self.laps_header, text="تصدير CSV", command=self._sw_export_csv,
            ar_helper=self.ar, width=90, height=28, radius=8,
            font=(self.ui_font, 9, "bold")
        )
        self.btn_export_laps.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_copy_laps = RoundedButton(
            self.laps_header, text="نسخ", command=self._sw_copy_laps,
            ar_helper=self.ar, width=64, height=28, radius=8,
            font=(self.ui_font, 9, "bold")
        )
        self.btn_copy_laps.pack(side=tk.LEFT)

        self.lbl_laps_summary = tk.Label(
            self.laps_header,
            text=self.ar.format("سجل الجولات واللفات (0)"),
            font=(self.ui_font, 10, "bold"),
        )
        self.lbl_laps_summary.pack(side=tk.RIGHT)

        # عناوين الأعمدة
        self.laps_cols = tk.Frame(self.laps_card, pady=4, padx=6)
        self.laps_cols.pack(fill=tk.X)
        self.lap_col_labels: list[tk.Label] = []
        col_specs = [
            ("الحالة", 10, tk.LEFT),
            ("الوقت الإجمالي", 12, tk.LEFT),
            ("مدة اللفة", 12, tk.LEFT),
            ("اللفة", 6, tk.RIGHT),
        ]
        for txt, w_ch, side in col_specs:
            lbl = tk.Label(
                self.laps_cols, text=self.ar.format(txt),
                width=w_ch, font=(self.ui_font, 9, "bold"),
                anchor="center" if side == tk.LEFT else "e",
            )
            lbl.pack(side=side, padx=4)
            self.lap_col_labels.append(lbl)

        # قائمة اللفات القابلة للتمرير
        self.laps_scroll_wrap = tk.Frame(self.laps_card)
        self.laps_scroll_wrap.pack(fill=tk.BOTH, expand=True)

        self.laps_canvas = tk.Canvas(self.laps_scroll_wrap, highlightthickness=0, bd=0, height=160)
        self.laps_scrollbar = tk.Scrollbar(
            self.laps_scroll_wrap, orient=tk.VERTICAL, command=self.laps_canvas.yview
        )
        self.laps_list_inner = tk.Frame(self.laps_canvas)
        self.laps_list_inner.bind(
            "<Configure>",
            lambda _e: self.laps_canvas.configure(scrollregion=self.laps_canvas.bbox("all")),
        )
        self._laps_window_id = self.laps_canvas.create_window(
            (0, 0), window=self.laps_list_inner, anchor="nw"
        )
        self.laps_canvas.bind(
            "<Configure>",
            lambda e: self.laps_canvas.itemconfigure(self._laps_window_id, width=e.width),
        )
        self.laps_canvas.configure(yscrollcommand=self.laps_scrollbar.set)
        self.laps_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.laps_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._bind_laps_scroll(self.laps_canvas)
        self._bind_laps_scroll(self.laps_list_inner)

    def _bind_laps_scroll(self, widget: tk.Widget) -> None:
        widget.bind("<MouseWheel>", self._on_laps_mousewheel)
        widget.bind("<Button-4>", lambda _e: self._scroll_laps(-1))
        widget.bind("<Button-5>", lambda _e: self._scroll_laps(1))

    def _on_laps_mousewheel(self, event: tk.Event) -> None:
        units = -1 if event.delta > 0 else 1
        self._scroll_laps(units)

    def _scroll_laps(self, units: int) -> None:
        if len(self.stopwatch.laps) > 4:
            self.laps_canvas.yview_scroll(units, "units")

    # -------------------------------------------------------------------------
    # تطبيق الألوان والمظهر (Theme)
    # -------------------------------------------------------------------------

    def _apply_theme(self) -> None:
        t = THEMES[self.theme_name]
        self.root.configure(bg=t["bg"])
        self.main_frame.configure(bg=t["bg"])
        self.header_frame.configure(bg=t["bg"])
        self.header_actions.configure(bg=t["bg"])
        self.title_box.configure(bg=t["bg"])
        self.lbl_title.configure(bg=t["bg"], fg=t["text"])
        self.lbl_subtitle.configure(bg=t["bg"], fg=t["text_muted"])

        self.btn_theme.set_text("وضع فاتح" if self.theme_name == "dark" else "وضع داكن")
        self.btn_theme.set_colors(
            bg_color=t["secondary"], hover_color=t["secondary_hover"],
            fg_color=t["secondary_text"], border_color=t["border"], parent_bg=t["bg"]
        )
        self.btn_pin.set_text("مثبت ✓" if self.always_on_top else "تثبيت")
        self.btn_pin.set_colors(
            bg_color=t["sky"] if self.always_on_top else t["secondary"],
            hover_color=t["sky_hover"] if self.always_on_top else t["secondary_hover"],
            fg_color="#FFFFFF" if self.always_on_top else t["secondary_text"],
            border_color="" if self.always_on_top else t["border"],
            parent_bg=t["bg"],
        )
        self.btn_mute.set_text("صامت" if self.sound.muted else "الصوت ✓")
        self.btn_mute.set_colors(
            bg_color=t["danger"] if self.sound.muted else t["secondary"],
            hover_color=t["danger_hover"] if self.sound.muted else t["secondary_hover"],
            fg_color="#FFFFFF" if self.sound.muted else t["secondary_text"],
            border_color="" if self.sound.muted else t["border"],
            parent_bg=t["bg"],
        )

        self.mode_switch.set_theme(t, t["bg"])
        self.content_holder.configure(bg=t["bg"])
        self.footer_frame.configure(bg=t["bg"])
        for i in range(0, len(self.shortcut_labels), 3):
            chip, k_lbl, d_lbl = self.shortcut_labels[i:i + 3]
            chip.configure(bg=t["surface"])
            k_lbl.configure(bg=t["surface_alt"], fg=t["sky"])
            d_lbl.configure(bg=t["surface"], fg=t["text_muted"])

        # تبويب المؤقت التنازلي
        self.cd_frame.configure(bg=t["bg"])
        self.cd_label_row.configure(bg=t["bg"])
        self.lbl_note_hint.configure(bg=t["bg"], fg=t["text_muted"])
        self.entry_cd_note.configure(
            bg=t["surface"], fg=t["text"], insertbackground=t["text"],
            highlightthickness=1, highlightbackground=t["border"], highlightcolor=t["primary"]
        )
        self.cd_gauge.set_theme(t, t["bg"])
        self.cd_controls.configure(bg=t["bg"])
        self.btn_cd_plus_min.set_colors(
            bg_color=t["secondary"], hover_color=t["secondary_hover"],
            fg_color=t["secondary_text"], border_color=t["border"], parent_bg=t["bg"]
        )
        self.btn_cd_reset.set_colors(
            bg_color=t["secondary"], hover_color=t["secondary_hover"],
            fg_color=t["secondary_text"], border_color=t["border"], parent_bg=t["bg"]
        )
        self.btn_cd_start.set_colors(parent_bg=t["bg"])

        self.cd_setup_card.configure(
            bg=t["surface"], highlightthickness=1, highlightbackground=t["border"]
        )
        self.lbl_presets_title.configure(bg=t["surface"], fg=t["text_muted"])
        self.presets_row.configure(bg=t["surface"])
        for btn in self.preset_buttons:
            btn.set_colors(
                bg_color=t["surface_alt"], hover_color=t["surface_hover"],
                fg_color=t["text"], border_color=t["border"], parent_bg=t["surface"]
            )

        self.lbl_custom_presets_title.configure(bg=t["surface"], fg=t["text_muted"])
        self.custom_presets_row.configure(bg=t["surface"])
        for kind, widget in self.custom_preset_widgets:
            if kind == "chip":
                widget.set_colors(
                    bg_color=t["surface_alt"], hover_color=t["surface_hover"],
                    fg_color=t["text"], border_color=t["border"], parent_bg=t["surface"]
                )
            elif kind == "delete":
                widget.set_colors(
                    bg_color=t["danger"], hover_color=t["danger_hover"],
                    fg_color="#FFFFFF", border_color="", parent_bg=t["surface"]
                )
            elif kind == "save":
                widget.set_colors(
                    bg_color=t["sky"], hover_color=t["sky_hover"],
                    fg_color="#FFFFFF", border_color="", parent_bg=t["surface"]
                )
            else:
                widget.configure(bg=t["surface"], fg=t["text_dim"])

        self.picker_row.configure(bg=t["surface"])
        for col_lbl, btn_up, entry, btn_dn, _ in self.picker_widgets:
            col = col_lbl.master
            col.configure(bg=t["surface"])
            col_lbl.configure(bg=t["surface"], fg=t["text_muted"])
            btn_up.set_colors(
                bg_color=t["surface_alt"], hover_color=t["surface_hover"],
                fg_color=t["text"], border_color=t["border"], parent_bg=t["surface"]
            )
            btn_dn.set_colors(
                bg_color=t["surface_alt"], hover_color=t["surface_hover"],
                fg_color=t["text"], border_color=t["border"], parent_bg=t["surface"]
            )
            entry.configure(
                bg=t["entry_bg"], fg=t["text"], insertbackground=t["text"],
                highlightthickness=1, highlightbackground=t["border"], highlightcolor=t["primary"]
            )
        for sep in getattr(self, "picker_colons", []):
            sep.configure(bg=t["surface"], fg=t["text_dim"])

        self.cd_options_row.configure(bg=t["bg"])
        self.btn_test_sound.set_colors(
            bg_color=t["secondary"], hover_color=t["secondary_hover"],
            fg_color=t["secondary_text"], border_color=t["border"], parent_bg=t["bg"]
        )
        for chk in (self.chk_repeat, self.chk_continuous):
            chk.configure(
                bg=t["bg"], fg=t["text_muted"],
                activebackground=t["bg"], activeforeground=t["text"],
                selectcolor=t["surface_alt"],
            )

        # تبويب ساعة الإيقاف
        self.sw_frame.configure(bg=t["bg"])
        self.sw_gauge.set_theme(t, t["bg"])
        self.sw_controls.configure(bg=t["bg"])
        self.btn_sw_reset.set_colors(
            bg_color=t["secondary"], hover_color=t["secondary_hover"],
            fg_color=t["secondary_text"], border_color=t["border"], parent_bg=t["bg"]
        )
        self.btn_sw_lap.set_colors(
            bg_color=t["secondary"], hover_color=t["secondary_hover"],
            fg_color=t["secondary_text"], border_color=t["border"], parent_bg=t["bg"]
        )
        self.btn_sw_start.set_colors(parent_bg=t["bg"])
        self.laps_card.configure(
            bg=t["surface"], highlightthickness=1, highlightbackground=t["border"]
        )
        self.laps_header.configure(bg=t["surface"])
        self.lbl_laps_summary.configure(bg=t["surface"], fg=t["text"])
        self.btn_export_laps.set_colors(
            bg_color=t["surface_alt"], hover_color=t["surface_hover"],
            fg_color=t["text"], border_color=t["border"], parent_bg=t["surface"]
        )
        self.btn_copy_laps.set_colors(
            bg_color=t["surface_alt"], hover_color=t["surface_hover"],
            fg_color=t["text"], border_color=t["border"], parent_bg=t["surface"]
        )
        self.laps_cols.configure(bg=t["surface_alt"])
        for lbl in self.lap_col_labels:
            lbl.configure(bg=t["surface_alt"], fg=t["text_muted"])
        self.laps_scroll_wrap.configure(bg=t["surface"])
        self.laps_canvas.configure(bg=t["surface"])
        self.laps_list_inner.configure(bg=t["surface"])

        self._last_laps_signature = ()
        self._refresh_ui()

    # -------------------------------------------------------------------------
    # معالجات الأحداث والتفاعل
    # -------------------------------------------------------------------------

    def _on_mode_change(self, mode: str) -> None:
        self.active_mode = mode
        self._show_active_view()
        self._save_settings()
        self._refresh_ui()

    def _show_active_view(self) -> None:
        if self.active_mode == "countdown":
            self.sw_frame.pack_forget()
            self.cd_frame.pack(fill=tk.BOTH, expand=True)
        else:
            self.cd_frame.pack_forget()
            self.sw_frame.pack(fill=tk.BOTH, expand=True)

    def _toggle_theme(self) -> None:
        self.theme_name = "light" if self.theme_name == "dark" else "dark"
        self._apply_theme()
        self._save_settings()

    def _toggle_topmost(self) -> None:
        self.always_on_top = not self.always_on_top
        self.root.attributes("-topmost", self.always_on_top)
        self._apply_theme()
        self._save_settings()

    def _toggle_mute(self) -> None:
        self.sound.muted = not self.sound.muted
        if self.sound.muted:
            self._dismiss_alarm()
        self._apply_theme()
        self._save_settings()

    def _on_option_toggle(self) -> None:
        self.countdown.auto_repeat = self.var_auto_repeat.get()
        self.continuous_alarm = self.var_continuous_alarm.get()
        self._save_settings()

    def _test_sound(self) -> None:
        if self.sound.muted:
            messagebox.showinfo(
                APP_TITLE_NATIVE,
                "الصوت مكتوم حالياً. اضغط على زر «صامت» في الأعلى لتفعيل الصوت.",
            )
            return
        self.sound.play(repeat=False)

    def _dismiss_alarm(self) -> None:
        self.alarm_ringing = False
        self.sound.stop()

    # --- أحداث المؤقت التنازلي ---

    def _sync_inputs_from_countdown(self) -> None:
        h, m, s = split_hms(self.countdown.total_seconds, ceil_mode=False)
        self.var_hours.set(f"{h:02d}")
        self.var_minutes.set(f"{m:02d}")
        self.var_seconds.set(f"{s:02d}")

    def _parse_int(self, text: str, max_val: int) -> int:
        digits = "".join(ch for ch in text if ch.isdigit())
        val = int(digits) if digits else 0
        return max(0, min(val, max_val))

    def _cd_commit_entries(self) -> None:
        if self.countdown.running:
            return
        h = self._parse_int(self.var_hours.get(), 99)
        m = self._parse_int(self.var_minutes.get(), 59)
        s = self._parse_int(self.var_seconds.get(), 59)
        if h == 0 and m == 0 and s == 0:
            s = 1
        self.countdown.set_duration(h, m, s)
        self._dismiss_alarm()
        self._sync_inputs_from_countdown()
        self._save_settings()
        self._refresh_ui()

    def _cd_step_unit(self, unit: str, delta: int) -> None:
        if self.countdown.running:
            return
        h = self._parse_int(self.var_hours.get(), 99)
        m = self._parse_int(self.var_minutes.get(), 59)
        s = self._parse_int(self.var_seconds.get(), 59)
        if unit == "h":
            h = (h + delta) % 100
        elif unit == "m":
            m = (m + delta) % 60
        else:
            if h == 0 and m == 0 and s == 1 and delta < 0:
                s = 59
            else:
                s = (s + delta) % 60
        if h == 0 and m == 0 and s == 0:
            s = 1
        self.countdown.set_duration(h, m, s)
        self._dismiss_alarm()
        self._sync_inputs_from_countdown()
        self._save_settings()
        self._refresh_ui()

    def _cd_apply_preset(self, minutes: int) -> None:
        self._dismiss_alarm()
        self.countdown.set_total_seconds(minutes * 60)
        self._sync_inputs_from_countdown()
        self._save_settings()
        self._refresh_ui()

    # --- المؤقتات المخصصة المحفوظة ---

    def _format_duration_short(self, total_seconds: float) -> str:
        secs = max(1, int(round(float(total_seconds))))
        h, m, s = split_hms(secs)
        parts: list[str] = []
        if h:
            parts.append(f"{h} س")
        if m:
            parts.append(f"{m} د")
        if s or not parts:
            parts.append(f"{s} ث")
        return " و".join(parts)

    def _sanitize_presets(self, raw) -> list[dict]:
        presets: list[dict] = []
        if not isinstance(raw, list):
            return presets
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
            seconds = max(1, min(seconds, 99 * 3600 + 59 * 60 + 59))
            presets.append({"name": name, "seconds": seconds})
            if len(presets) >= self.MAX_CUSTOM_PRESETS:
                break
        return presets

    def _rebuild_custom_presets_row(self) -> None:
        for child in self.custom_presets_row.winfo_children():
            child.destroy()
        self.custom_preset_widgets = []

        save_btn = RoundedButton(
            self.custom_presets_row, text="حفظ", command=self._cd_save_preset,
            ar_helper=self.ar, width=64, height=30, radius=9,
            font=(self.ui_font, 9, "bold"),
        )
        save_btn.pack(side=tk.RIGHT, padx=2)
        self.custom_preset_widgets.append(("save", save_btn))

        for idx, preset in enumerate(self.custom_presets):
            duration = self._format_duration_short(preset["seconds"])
            chip_text = f"{preset['name']} ({duration})"
            chip_w = min(170, 34 + max(len(chip_text) * 7, 52))
            chip = RoundedButton(
                self.custom_presets_row, text=chip_text,
                command=lambda i=idx: self._cd_apply_custom_preset(i),
                ar_helper=self.ar, width=chip_w, height=30, radius=9,
                font=(self.ui_font, 9, "bold"),
            )
            chip.pack(side=tk.RIGHT, padx=2)
            self.custom_preset_widgets.append(("chip", chip))

            delete_btn = RoundedButton(
                self.custom_presets_row, text="✕",
                command=lambda i=idx: self._cd_delete_custom_preset(i),
                ar_helper=None, width=26, height=30, radius=9,
                bg_color="#EF4444", hover_color="#DC2626", fg_color="#FFFFFF",
                font=(self.ui_font, 9, "bold"),
            )
            delete_btn.pack(side=tk.RIGHT)
            self.custom_preset_widgets.append(("delete", delete_btn))

        if not self.custom_presets:
            hint = tk.Label(
                self.custom_presets_row,
                text=self.ar.format("اضبط الوقت ثم اضغط + حفظ لتخزينه بالاسم"),
                font=(self.ui_font, 8),
            )
            hint.pack(side=tk.RIGHT)
            self.custom_preset_widgets.append(("hint", hint))

    def _cd_save_custom_preset_value(self, name: str, seconds: int) -> tuple[bool, str]:
        name = name.strip()[:40]
        if not name:
            return False, "يرجى إدخال اسم للمؤقت."
        for preset in self.custom_presets:
            if preset["name"] == name:
                preset["seconds"] = seconds
                return True, "updated"
        if len(self.custom_presets) >= self.MAX_CUSTOM_PRESETS:
            return False, "الحد الأقصى 12 مؤقتاً محفوظاً. احذف مؤقتاً أولاً."
        self.custom_presets.append({"name": name, "seconds": seconds})
        return True, "added"

    def _cd_save_preset(self) -> None:
        seconds = int(round(self.countdown.total_seconds))
        if seconds <= 0:
            return
        default_name = self.cd_note_var.get().strip() or self._format_duration_short(seconds)
        name = simpledialog.askstring(
            APP_TITLE_NATIVE,
            "اسم المؤقت:",
            initialvalue=default_name,
            parent=self.root,
        )
        if name is None:
            return
        name = name.strip()[:40]
        if not name:
            messagebox.showinfo(APP_TITLE_NATIVE, "يرجى إدخال اسم للمؤقت.")
            return
        existing = next((p for p in self.custom_presets if p["name"] == name), None)
        if existing is not None and existing["seconds"] != seconds:
            replace = messagebox.askyesno(
                APP_TITLE_NATIVE,
                f"يوجد مؤقت باسم «{name}» بمدة مختلفة. استبداله؟",
            )
            if not replace:
                return
            existing["seconds"] = seconds
        else:
            ok, message = self._cd_save_custom_preset_value(name, seconds)
            if not ok:
                messagebox.showinfo(APP_TITLE_NATIVE, message)
                return
        self._save_settings()
        self._rebuild_custom_presets_row()

    def _cd_apply_custom_preset(self, index: int) -> None:
        if not (0 <= index < len(self.custom_presets)):
            return
        self._dismiss_alarm()
        self.countdown.set_total_seconds(float(self.custom_presets[index]["seconds"]))
        self._sync_inputs_from_countdown()
        self._save_settings()
        self._refresh_ui()

    def _cd_delete_custom_preset(self, index: int) -> None:
        if not (0 <= index < len(self.custom_presets)):
            return
        name = self.custom_presets[index]["name"]
        if not messagebox.askyesno(APP_TITLE_NATIVE, f"حذف المؤقت «{name}»؟"):
            return
        del self.custom_presets[index]
        self._save_settings()
        self._rebuild_custom_presets_row()

    def _cd_add_minute(self) -> None:
        self._dismiss_alarm()
        self.countdown.add_seconds(60)
        if not self.countdown.running:
            self._sync_inputs_from_countdown()
        self._refresh_ui()

    def _cd_primary_action(self) -> None:
        if self.alarm_ringing:
            self._dismiss_alarm()
            self._refresh_ui()
            return
        if not self.countdown.running:
            # التأكد من اعتماد أي رقم أدخله المستخدم يدوياً قبل الضغط على ابدأ
            h = self._parse_int(self.var_hours.get(), 99)
            m = self._parse_int(self.var_minutes.get(), 59)
            s = self._parse_int(self.var_seconds.get(), 59)
            entered = h * 3600 + m * 60 + s
            if entered > 0 and abs(entered - self.countdown.total_seconds) >= 1:
                self.countdown.set_duration(h, m, s)
                self._sync_inputs_from_countdown()
            self.countdown.start()
        else:
            self.countdown.pause()
        self._refresh_ui()

    def _cd_reset(self) -> None:
        self._dismiss_alarm()
        self.countdown.reset()
        self._sync_inputs_from_countdown()
        self._refresh_ui()

    # --- أحداث ساعة الإيقاف ---

    def _sw_toggle(self) -> None:
        self.stopwatch.toggle()
        self._refresh_ui()

    def _sw_reset(self) -> None:
        self.stopwatch.reset()
        self._refresh_ui()

    def _sw_record_lap(self) -> None:
        if self.stopwatch.record_lap() is not None:
            self._refresh_ui()

    def _sw_copy_laps(self) -> None:
        if not self.stopwatch.laps:
            return
        lines = ["اللفة\tمدة اللفة\tالوقت الإجمالي"]
        for r in self.stopwatch.laps:
            l_main, l_c = format_stopwatch(r.lap_seconds)
            t_main, t_c = format_stopwatch(r.total_seconds)
            lines.append(f"#{r.index}\t{l_main}{l_c}\t{t_main}{t_c}")
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(lines))
        self.btn_copy_laps.set_text("تم النسخ ✓")
        self.root.after(1400, lambda: self.btn_copy_laps.set_text("نسخ"))

    def _sw_export_csv(self) -> None:
        if not self.stopwatch.laps:
            messagebox.showinfo(APP_TITLE_NATIVE, "لا توجد لفات مسجلة للتصدير بعد.")
            return
        path = filedialog.asksaveasfilename(
            title="حفظ سجل اللفات",
            defaultextension=".csv",
            initialfile="stopwatch_laps.csv",
            filetypes=[("ملف CSV", "*.csv"), ("جميع الملفات", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["رقم اللفة", "مدة اللفة", "الوقت الإجمالي", "مدة اللفة (ثوانٍ)"])
                for r in self.stopwatch.laps:
                    l_main, l_c = format_stopwatch(r.lap_seconds)
                    t_main, t_c = format_stopwatch(r.total_seconds)
                    writer.writerow([r.index, f"{l_main}{l_c}", f"{t_main}{t_c}", f"{r.lap_seconds:.3f}"])
        except Exception as exc:
            messagebox.showerror(APP_TITLE_NATIVE, f"تعذر حفظ الملف:\n{exc}")

    # -------------------------------------------------------------------------
    # اختصارات لوحة المفاتيح
    # -------------------------------------------------------------------------

    def _bind_shortcuts(self) -> None:
        self.root.bind("<KeyPress>", self._on_keypress)

    def _on_keypress(self, event: tk.Event) -> None:
        # عدم اعتراض الكتابة داخل حقول الإدخال
        if isinstance(event.widget, tk.Entry):
            return

        sym = event.keysym.lower()
        if sym == "space":
            if self.active_mode == "countdown":
                self._cd_primary_action()
            else:
                self._sw_toggle()
        elif sym in ("r", "arabic_reh"):
            if self.active_mode == "countdown":
                self._cd_reset()
            else:
                self._sw_reset()
        elif sym in ("l", "arabic_meem") and self.active_mode == "stopwatch":
            self._sw_record_lap()
        elif sym == "1":
            self.mode_switch.set_mode("countdown")
            self._on_mode_change("countdown")
        elif sym == "2":
            self.mode_switch.set_mode("stopwatch")
            self._on_mode_change("stopwatch")
        elif sym == "m":
            self._toggle_mute()
        elif sym == "t":
            self._toggle_theme()

    # -------------------------------------------------------------------------
    # حلقة التحديث الدورية وتحديث الواجهة
    # -------------------------------------------------------------------------

    def _schedule_tick(self) -> None:
        self._on_tick()

    def _on_tick(self) -> None:
        completed_now = self.countdown.tick()
        if completed_now:
            self.alarm_ringing = not self.countdown.auto_repeat
            self.sound.play(repeat=(self.continuous_alarm and not self.countdown.auto_repeat))
            try:
                self.root.deiconify()
                self.root.lift()
            except Exception:
                pass

        if self.alarm_ringing:
            self._pulse_phase = (self._pulse_phase + 1) % 20
        else:
            self._pulse_phase = 0

        self._refresh_ui()
        self._after_id = self.root.after(40, self._on_tick)

    def _refresh_ui(self) -> None:
        t = THEMES[self.theme_name]
        self.mode_switch.set_running_indicators(
            countdown_running=self.countdown.running,
            stopwatch_running=self.stopwatch.running,
        )

        if self.active_mode == "countdown":
            self._refresh_countdown_ui(t)
        else:
            self._refresh_stopwatch_ui(t)

    def _refresh_countdown_ui(self, t: dict[str, str]) -> None:
        rem = self.countdown.remaining()
        prog = self.countdown.progress()
        note = self.cd_note_var.get().strip()

        if self.countdown.finished:
            accent = t["danger"]
            status = "انتهى الوقت!"
            main_time = "00:00:00"
            sub_text = note if note else "اضغط إعادة تعيين أو إيقاف التنبيه"
        elif self.countdown.running:
            if prog <= 0.20:
                accent = t["danger"]
            elif prog <= 0.50:
                accent = t["amber"]
            else:
                accent = t["primary"]
            status = "جاري العد التنازلي"
            main_time = format_hms(rem, ceil_mode=True)
            eta_ts = time.localtime(time.time() + rem)
            eta_str = time.strftime("%H:%M:%S", eta_ts)
            sub_text = f"{note} • ينتهي {eta_str}" if note else f"ينتهي عند {eta_str}"
            if self.countdown.auto_repeat and self.countdown.cycles_completed > 0:
                sub_text = f"الدورة #{self.countdown.cycles_completed + 1} • ينتهي {eta_str}"
        else:
            accent = t["amber"] if rem < self.countdown.total_seconds else t["sky"]
            status = "متوقف مؤقتاً" if rem < self.countdown.total_seconds else "جاهز للبدء"
            main_time = format_hms(rem, ceil_mode=True)
            total_str = format_hms(self.countdown.total_seconds, ceil_mode=False)
            sub_text = f"{note} ({total_str})" if note else f"المدة المحددة: {total_str}"

        pulse_on = self.alarm_ringing and (self._pulse_phase < 10)
        self.cd_gauge.render(
            progress=prog,
            accent_color=accent,
            status_text=status,
            main_time=main_time,
            sub_text=sub_text,
            show_ticks=False,
            alert_pulse=pulse_on,
        )

        # زر التشغيل الرئيسي
        if self.alarm_ringing:
            self.btn_cd_start.set_text("إيقاف التنبيه")
            self.btn_cd_start.set_colors(
                bg_color=t["danger"], hover_color=t["danger_hover"], fg_color="#FFFFFF"
            )
        elif self.countdown.running:
            self.btn_cd_start.set_text("إيقاف مؤقت")
            self.btn_cd_start.set_colors(
                bg_color=t["amber"], hover_color=t["amber_hover"], fg_color="#FFFFFF"
            )
        elif rem < self.countdown.total_seconds and not self.countdown.finished:
            self.btn_cd_start.set_text("استئناف")
            self.btn_cd_start.set_colors(
                bg_color=t["primary"], hover_color=t["primary_hover"], fg_color="#FFFFFF"
            )
        else:
            self.btn_cd_start.set_text("ابدأ")
            self.btn_cd_start.set_colors(
                bg_color=t["primary"], hover_color=t["primary_hover"], fg_color="#FFFFFF"
            )

        # تمكين/تعطيل مدخلات ضبط الوقت أثناء التشغيل
        inputs_enabled = not self.countdown.running
        state = tk.NORMAL if inputs_enabled else tk.DISABLED
        for _, btn_up, entry, btn_dn, _ in self.picker_widgets:
            btn_up.set_enabled(inputs_enabled)
            btn_dn.set_enabled(inputs_enabled)
            if str(entry.cget("state")) != state:
                entry.configure(state=state)
        for pbtn in self.preset_buttons:
            pbtn.set_enabled(inputs_enabled)

    def _refresh_stopwatch_ui(self, t: dict[str, str]) -> None:
        elapsed = self.stopwatch.elapsed()
        main_time, centis = format_stopwatch(elapsed)
        # قوس يدور دورة كاملة كل 60 ثانية
        prog = (elapsed % 60.0) / 60.0 if elapsed > 0 else 0.0

        if self.stopwatch.running:
            status = "جاري العد التصاعدي"
            accent = t["sky"]
        elif elapsed > 0:
            status = "متوقف مؤقتاً"
            accent = t["amber"]
        else:
            status = "جاهز للبدء"
            accent = t["sky"]

        sub_text = ""
        if self.stopwatch.laps:
            cur_main, cur_c = format_stopwatch(self.stopwatch.current_lap_elapsed())
            sub_text = f"اللفة الحالية: {cur_main}{cur_c}"

        self.sw_gauge.render(
            progress=prog,
            accent_color=accent,
            status_text=status,
            main_time=main_time,
            centis_text=centis,
            sub_text=sub_text,
            show_ticks=True,
        )

        if self.stopwatch.running:
            self.btn_sw_start.set_text("إيقاف مؤقت")
            self.btn_sw_start.set_colors(
                bg_color=t["amber"], hover_color=t["amber_hover"], fg_color="#FFFFFF"
            )
        elif elapsed > 0:
            self.btn_sw_start.set_text("استئناف")
            self.btn_sw_start.set_colors(
                bg_color=t["sky"], hover_color=t["sky_hover"], fg_color="#FFFFFF"
            )
        else:
            self.btn_sw_start.set_text("ابدأ")
            self.btn_sw_start.set_colors(
                bg_color=t["sky"], hover_color=t["sky_hover"], fg_color="#FFFFFF"
            )

        self.btn_sw_lap.set_enabled(self.stopwatch.running or elapsed > 0)
        self.btn_sw_reset.set_enabled(elapsed > 0 or len(self.stopwatch.laps) > 0)

        # تحديث جدول اللفات فقط عند تغير البيانات
        sig = (len(self.stopwatch.laps), self.theme_name)
        if sig != self._last_laps_signature:
            self._last_laps_signature = sig
            self._rebuild_laps_list(t)

    def _rebuild_laps_list(self, t: dict[str, str]) -> None:
        for child in self.laps_list_inner.winfo_children():
            child.destroy()

        laps = self.stopwatch.laps
        avg = self.stopwatch.average_lap()
        if avg is not None:
            a_main, a_c = format_stopwatch(avg)
            summary = f"الجولات ({len(laps)}) • المتوسط: {a_main}{a_c}"
        else:
            summary = "سجل الجولات واللفات (0)"
        self.lbl_laps_summary.configure(text=self.ar.format(summary))

        if not laps:
            empty_lbl = tk.Label(
                self.laps_list_inner,
                text=self.ar.format("اضغط «تسجيل لفة» أثناء التشغيل لتسجيل الجولات هنا"),
                bg=t["surface"],
                fg=t["text_dim"],
                font=(self.ui_font, 9),
                pady=24,
            )
            empty_lbl.pack(fill=tk.X)
            return

        fastest_idx, slowest_idx = self.stopwatch.fastest_and_slowest_indices()
        for record in reversed(laps):
            row_bg = t["surface"]
            badge_bg = t["surface"]
            badge_fg = t["text_muted"]
            badge_txt = "—"

            if record.index == fastest_idx:
                row_bg = t["fastest_bg"]
                badge_bg = t["fastest_bg"]
                badge_fg = t["fastest_fg"]
                badge_txt = "الأسرع"
            elif record.index == slowest_idx:
                row_bg = t["slowest_bg"]
                badge_bg = t["slowest_bg"]
                badge_fg = t["slowest_fg"]
                badge_txt = "الأبطأ"

            row = tk.Frame(self.laps_list_inner, bg=row_bg, pady=4, padx=6)
            row.pack(fill=tk.X, pady=1)
            self._bind_laps_scroll(row)

            l_main, l_c = format_stopwatch(record.lap_seconds)
            t_main, t_c = format_stopwatch(record.total_seconds)

            lbl_badge = tk.Label(
                row, text=self.ar.format(badge_txt), width=10,
                bg=badge_bg, fg=badge_fg, font=(self.ui_font, 9, "bold"), anchor="center"
            )
            lbl_badge.pack(side=tk.LEFT, padx=4)

            lbl_total = tk.Label(
                row, text=f"{t_main}{t_c}", width=12,
                bg=row_bg, fg=t["text_muted"], font=(self.mono_font, 9), anchor="center"
            )
            lbl_total.pack(side=tk.LEFT, padx=4)

            lbl_lap = tk.Label(
                row, text=f"{l_main}{l_c}", width=12,
                bg=row_bg, fg=t["text"], font=(self.mono_font, 9, "bold"), anchor="center"
            )
            lbl_lap.pack(side=tk.LEFT, padx=4)

            lbl_idx = tk.Label(
                row, text=f"#{record.index}", width=6,
                bg=row_bg, fg=t["text"], font=(self.mono_font, 9, "bold"), anchor="e"
            )
            lbl_idx.pack(side=tk.RIGHT, padx=4)

            for child_lbl in (lbl_badge, lbl_total, lbl_lap, lbl_idx):
                self._bind_laps_scroll(child_lbl)

    def _on_close(self) -> None:
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
        self._dismiss_alarm()
        self._save_settings()
        self.root.destroy()


def main() -> None:
    enable_windows_dpi_awareness()
    root = tk.Tk()
    TimerDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
