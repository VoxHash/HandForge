"""Progress tracking helpers for parallel FFmpeg conversions.

Under heavy parallel load, raw FFmpeg progress lines are noisy: speed fluctuates,
time= can briefly regress, and flooding the UI with every stderr line causes
stale/jittery percentages. This module keeps progress monotonic, ETA speed-aware,
and emits throttled updates suitable for many concurrent workers.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Optional, Tuple

_TIME_RE = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
_DURATION_RE = re.compile(r"Duration:\s*(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
_SPEED_RE = re.compile(r"speed=\s*([\d.]+)x", re.IGNORECASE)


def hms_to_seconds(h: int, m: int, s: int, cs: int) -> float:
    """Convert H:M:S.centiseconds to seconds."""
    return h * 3600 + m * 60 + s + cs / 100.0


def parse_duration(line: str) -> Optional[float]:
    """Parse FFmpeg Duration: HH:MM:SS.cc from a log line."""
    match = _DURATION_RE.search(line)
    if not match:
        return None
    h, m, s, cs = map(int, match.groups())
    return hms_to_seconds(h, m, s, cs)


def parse_out_time(line: str) -> Optional[float]:
    """Parse FFmpeg time=HH:MM:SS.cc progress field."""
    match = _TIME_RE.search(line)
    if not match:
        return None
    h, m, s, cs = map(int, match.groups())
    return hms_to_seconds(h, m, s, cs)


def parse_speed(line: str) -> Optional[float]:
    """Parse FFmpeg speed=N.NNx as a float multiplier, or None if missing/N/A."""
    match = _SPEED_RE.search(line)
    if not match:
        return None
    try:
        speed = float(match.group(1))
    except ValueError:
        return None
    return speed if speed > 0 else None


def progress_percent(current_seconds: float, duration_seconds: float) -> float:
    """Media-time progress as 0..99 (leave 100 for completion)."""
    if duration_seconds <= 0:
        return 0.0
    return min(99.0, max(0.0, (current_seconds / duration_seconds) * 100.0))


def eta_from_speed(
    current_seconds: float,
    duration_seconds: float,
    speed: Optional[float],
) -> float:
    """Wall-clock ETA from remaining media time divided by encode speed.

    Falls back to remaining media seconds when speed is unknown (same as the
    old optimistic estimate, but only when we have no better signal).
    """
    if duration_seconds <= 0:
        return 0.0
    remaining = max(0.0, duration_seconds - current_seconds)
    if remaining <= 0:
        return 0.0
    if speed is not None and speed > 0:
        return remaining / speed
    return remaining


def ewma(prev: float, sample: float, alpha: float) -> float:
    """Exponentially weighted moving average; alpha in [0, 1]."""
    a = min(1.0, max(0.0, alpha))
    if a <= 0:
        return prev
    if a >= 1.0:
        return sample
    return a * sample + (1.0 - a) * prev


def batch_progress_with_eta(
    workers: dict,
    queued: int = 0,
) -> Tuple[float, float]:
    """Aggregate overall % and ETA from {wid: {progress, eta}} maps.

    Overall % weights finished+running+queued equally (queued = 0%).
    Batch ETA is the max of running worker ETAs (wall clock under parallelism),
    plus estimated queue drain using the mean of positive running ETAs when
    available.
    """
    if not workers and queued <= 0:
        return 0.0, 0.0

    progress_sum = 0.0
    etas = []
    for data in workers.values():
        progress_sum += max(0.0, min(100.0, float(data.get("progress", 0))))
        status = data.get("status", "Running")
        if status == "Running":
            eta = float(data.get("eta", 0) or 0)
            if eta > 0:
                etas.append(eta)

    n_total = len(workers) + max(0, queued)
    overall = progress_sum / n_total if n_total else 0.0

    batch_eta = max(etas) if etas else 0.0
    if queued > 0 and etas:
        # Rough remaining queue time after current parallel wave.
        mean_eta = sum(etas) / len(etas)
        # Assume concurrency ~= number of running workers with ETA.
        concurrency = max(1, len(etas))
        waves = (queued + concurrency - 1) // concurrency
        batch_eta = batch_eta + waves * mean_eta

    return overall, batch_eta


@dataclass
class ProgressSample:
    """One throttled progress emission for the UI."""

    progress: float
    elapsed: float
    eta: float
    speed_str: str
    emitted: bool = False


@dataclass
class ProgressTracker:
    """Per-worker tracker: monotonic %, EWMA ETA, emit throttle."""

    ewma_alpha: float = 0.3
    min_emit_interval: float = 0.25
    min_progress_delta: float = 0.5
    duration_seconds: Optional[float] = None
    last_raw_progress: float = 0.0
    last_display_progress: float = 0.0
    last_eta: float = 0.0
    last_speed: Optional[float] = None
    last_speed_str: str = "1.0x"
    last_emit_time: float = 0.0
    last_emitted_progress: float = -1.0
    has_real_progress: bool = False
    _eta_initialized: bool = field(default=False, repr=False)

    def note_duration(self, duration: float) -> None:
        if duration and duration > 0:
            self.duration_seconds = duration

    def update_from_line(
        self,
        line: str,
        elapsed: float,
        now: Optional[float] = None,
    ) -> ProgressSample:
        """Parse one FFmpeg stderr line; return whether to emit to the UI."""
        if self.duration_seconds is None:
            dur = parse_duration(line)
            if dur is not None:
                self.note_duration(dur)

        out_t = parse_out_time(line)
        if out_t is None or not self.duration_seconds:
            return ProgressSample(
                self.last_display_progress,
                elapsed,
                self.last_eta,
                self.last_speed_str,
                emitted=False,
            )

        speed = parse_speed(line)
        if speed is not None:
            self.last_speed = speed
            self.last_speed_str = f"{speed:.2f}x"

        raw = progress_percent(out_t, self.duration_seconds)
        # Never let display progress go backwards under parallel noise.
        raw = max(raw, self.last_raw_progress)
        self.last_raw_progress = raw
        self.has_real_progress = True

        display = ewma(self.last_display_progress, raw, self.ewma_alpha)
        # Keep display monotonic as well.
        display = max(display, self.last_display_progress)
        # Snap close to raw near completion so we don't lag forever.
        if raw >= 98.0:
            display = raw
        self.last_display_progress = display

        raw_eta = eta_from_speed(out_t, self.duration_seconds, self.last_speed)
        if not self._eta_initialized:
            self.last_eta = raw_eta
            self._eta_initialized = True
        else:
            self.last_eta = ewma(self.last_eta, raw_eta, self.ewma_alpha)

        now = time.monotonic() if now is None else now
        should_emit = self._should_emit(display, now)
        if should_emit:
            self.last_emit_time = now
            self.last_emitted_progress = display

        return ProgressSample(
            progress=display,
            elapsed=elapsed,
            eta=self.last_eta,
            speed_str=self.last_speed_str,
            emitted=should_emit,
        )

    def force_complete(self, elapsed: float, speed_str: Optional[str] = None) -> ProgressSample:
        """Mark job finished at 100% (always emit)."""
        self.last_display_progress = 100.0
        self.last_raw_progress = 100.0
        self.last_eta = 0.0
        self.has_real_progress = True
        if speed_str:
            self.last_speed_str = speed_str
        return ProgressSample(
            100.0, elapsed, 0.0, self.last_speed_str, emitted=True
        )

    def keepalive(self, elapsed: float, now: Optional[float] = None) -> ProgressSample:
        """Alive signal when FFmpeg has not yet reported real progress.

        Must never overwrite a real percentage with a synthetic 0.1% — that
        caused progress bars to jitter/reset under parallel load.
        """
        if self.has_real_progress:
            return ProgressSample(
                self.last_display_progress,
                elapsed,
                self.last_eta,
                self.last_speed_str,
                emitted=False,
            )
        now = time.monotonic() if now is None else now
        if self.last_emit_time and (now - self.last_emit_time) < 5.0:
            return ProgressSample(0.0, elapsed, 0.0, "?", emitted=False)
        self.last_emit_time = now
        self.last_emitted_progress = 0.1
        # Tiny non-zero so the bar shows activity without claiming percent done.
        return ProgressSample(0.1, elapsed, 0.0, "?", emitted=True)

    def _should_emit(self, display: float, now: float) -> bool:
        if self.last_emit_time <= 0 or self.last_emitted_progress < 0:
            return True
        elapsed_since = now - self.last_emit_time
        delta = abs(display - self.last_emitted_progress)
        if elapsed_since >= self.min_emit_interval:
            return True
        # Emit early on meaningful jumps so the UI does not feel stuck.
        if delta >= self.min_progress_delta and elapsed_since >= 0.05:
            return True
        return False
