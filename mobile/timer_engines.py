"""محركات التوقيت المشتركة بين نسختي سطح المكتب والأندرويد (نفس الكود المُختبر)."""

import math
import time
from dataclasses import dataclass
from typing import Callable, Optional


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
