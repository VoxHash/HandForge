"""Optional local-only performance analytics for long batch jobs.

Privacy: off by default. When enabled, metrics are derived from real job
runs (wall time, FFmpeg speed samples, throughput, peak parallel, ETA
error) and written under ``~/.handforge/analytics/``. Nothing is sent to
the network.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..core.settings import get_config_dir

SETTING_PERF_ANALYTICS = "performance_analytics"
ANALYTICS_DIRNAME = "analytics"
BATCHES_FILENAME = "batches.jsonl"
MAX_STORED_BATCHES = 200


def analytics_enabled(settings: Optional[Dict[str, Any]] = None) -> bool:
    """True when the opt-in local performance analytics flag is on."""
    if not settings:
        return False
    return bool(settings.get(SETTING_PERF_ANALYTICS, False))


def analytics_dir(config_dir: Optional[Path] = None) -> Path:
    """Return ``~/.handforge/analytics`` (created on demand)."""
    root = Path(config_dir) if config_dir is not None else get_config_dir()
    path = root / ANALYTICS_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def batches_path(config_dir: Optional[Path] = None) -> Path:
    return analytics_dir(config_dir) / BATCHES_FILENAME


def _safe_file_size(path: Optional[str]) -> Optional[int]:
    if not path:
        return None
    try:
        return int(os.path.getsize(path))
    except OSError:
        return None


def _parse_speed(speed: Any) -> Optional[float]:
    if speed is None:
        return None
    if isinstance(speed, (int, float)):
        val = float(speed)
        return val if val > 0 else None
    text = str(speed).strip().lower().rstrip("x")
    if not text or text in ("?", "n/a"):
        return None
    try:
        val = float(text)
    except ValueError:
        return None
    return val if val > 0 else None


@dataclass
class JobRecord:
    """Per-job metrics collected from a real conversion."""

    wid: int
    src: str
    success: bool = False
    message: str = ""
    output_path: str = ""
    started_at: float = 0.0
    ended_at: float = 0.0
    wall_seconds: float = 0.0
    bytes_in: Optional[int] = None
    bytes_out: Optional[int] = None
    speed_samples: List[float] = field(default_factory=list)
    # (sample_wall_time, predicted_remaining_eta_s) while running
    eta_forecasts: List[Tuple[float, float]] = field(default_factory=list)
    last_progress: float = 0.0
    last_elapsed: float = 0.0

    def mean_speed(self) -> Optional[float]:
        if not self.speed_samples:
            return None
        return sum(self.speed_samples) / len(self.speed_samples)

    def peak_speed(self) -> Optional[float]:
        return max(self.speed_samples) if self.speed_samples else None

    def throughput_bps(self) -> Optional[float]:
        """Output bytes per wall-clock second."""
        if self.bytes_out is None or self.wall_seconds <= 0:
            return None
        return float(self.bytes_out) / self.wall_seconds

    def eta_mae_seconds(self) -> Optional[float]:
        """Mean absolute error of ETA forecasts vs actual finish time."""
        if not self.eta_forecasts or self.ended_at <= 0:
            return None
        errors = [
            abs((t + eta) - self.ended_at) for t, eta in self.eta_forecasts if eta >= 0
        ]
        if not errors:
            return None
        return sum(errors) / len(errors)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wid": self.wid,
            "src": os.path.basename(self.src) if self.src else "",
            "src_path": self.src,
            "success": self.success,
            "message": (self.message or "")[:240],
            "output_path": self.output_path,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "wall_seconds": round(self.wall_seconds, 3),
            "bytes_in": self.bytes_in,
            "bytes_out": self.bytes_out,
            "mean_speed_x": (
                round(self.mean_speed(), 3) if self.mean_speed() is not None else None
            ),
            "peak_speed_x": (
                round(self.peak_speed(), 3) if self.peak_speed() is not None else None
            ),
            "throughput_bps": (
                round(self.throughput_bps(), 1)
                if self.throughput_bps() is not None
                else None
            ),
            "eta_mae_seconds": (
                round(self.eta_mae_seconds(), 3)
                if self.eta_mae_seconds() is not None
                else None
            ),
            "speed_sample_count": len(self.speed_samples),
            "eta_sample_count": len(self.eta_forecasts),
        }


@dataclass
class BatchSummary:
    """Aggregated stats for one batch run."""

    batch_id: str
    started_at: float
    ended_at: float
    job_count: int
    succeeded: int
    failed: int
    wall_seconds: float
    peak_parallel: int
    parallel_setting: int
    adaptive_parallel: bool
    total_bytes_in: int
    total_bytes_out: int
    mean_job_seconds: float
    mean_speed_x: Optional[float]
    peak_speed_x: Optional[float]
    throughput_bps: Optional[float]
    eta_mae_seconds: Optional[float]
    jobs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


class BatchAnalyticsSession:
    """Collect real per-job and batch metrics while a conversion batch runs."""

    def __init__(self, settings: Optional[Dict[str, Any]] = None):
        self.settings = dict(settings or {})
        self.batch_id = uuid.uuid4().hex[:12]
        self.started_at = time.time()
        self.ended_at: Optional[float] = None
        self.jobs: Dict[int, JobRecord] = {}
        self.peak_parallel = 0
        self._active = 0
        self._finished = False

    @classmethod
    def start(cls, settings: Optional[Dict[str, Any]] = None) -> "BatchAnalyticsSession":
        return cls(settings=settings)

    @property
    def finished(self) -> bool:
        return self._finished

    def note_parallel(self, active_count: int) -> None:
        """Record current concurrent worker count (updates peak)."""
        n = max(0, int(active_count))
        self._active = n
        if n > self.peak_parallel:
            self.peak_parallel = n

    def on_started(self, wid: int, file_path: str) -> None:
        now = time.time()
        self._active += 1
        if self._active > self.peak_parallel:
            self.peak_parallel = self._active
        self.jobs[int(wid)] = JobRecord(
            wid=int(wid),
            src=str(file_path or ""),
            started_at=now,
            bytes_in=_safe_file_size(file_path),
        )

    def on_progress(
        self,
        wid: int,
        progress: float,
        elapsed: float,
        eta: float,
        speed: Any,
    ) -> None:
        job = self.jobs.get(int(wid))
        if job is None:
            return
        job.last_progress = float(progress or 0.0)
        job.last_elapsed = float(elapsed or 0.0)
        speed_val = _parse_speed(speed)
        if speed_val is not None:
            job.speed_samples.append(speed_val)
        # ETA accuracy: only while still running with a positive forecast.
        if eta and float(eta) > 0 and float(progress or 0.0) < 99.5:
            job.eta_forecasts.append((time.time(), float(eta)))

    def on_done(
        self,
        wid: int,
        success: bool,
        message: str,
        output_path: str,
    ) -> None:
        now = time.time()
        self._active = max(0, self._active - 1)
        job = self.jobs.get(int(wid))
        if job is None:
            job = JobRecord(wid=int(wid), src="", started_at=now)
            self.jobs[int(wid)] = job
        job.success = bool(success)
        job.message = message or ""
        job.output_path = output_path or ""
        job.ended_at = now
        if job.started_at > 0:
            job.wall_seconds = max(0.0, now - job.started_at)
        elif job.last_elapsed > 0:
            job.wall_seconds = float(job.last_elapsed)
        job.bytes_out = _safe_file_size(output_path) if success else None
        if job.bytes_in is None and job.src:
            job.bytes_in = _safe_file_size(job.src)

    def finish(self, *, persist: bool = True) -> BatchSummary:
        """Close the batch, optionally append to local JSONL history."""
        self.ended_at = time.time()
        self._finished = True
        summary = self.summarize()
        if persist:
            append_batch_summary(summary)
        return summary

    def summarize(self) -> BatchSummary:
        ended = self.ended_at if self.ended_at is not None else time.time()
        job_list = [self.jobs[k] for k in sorted(self.jobs)]
        succeeded = sum(1 for j in job_list if j.success)
        failed = len(job_list) - succeeded
        walls = [j.wall_seconds for j in job_list if j.wall_seconds > 0]
        speeds: List[float] = []
        peaks: List[float] = []
        eta_errs: List[float] = []
        bytes_in = 0
        bytes_out = 0
        for j in job_list:
            if j.bytes_in:
                bytes_in += j.bytes_in
            if j.bytes_out:
                bytes_out += j.bytes_out
            ms = j.mean_speed()
            if ms is not None:
                speeds.append(ms)
            ps = j.peak_speed()
            if ps is not None:
                peaks.append(ps)
            mae = j.eta_mae_seconds()
            if mae is not None:
                eta_errs.append(mae)

        wall_total = max(0.0, ended - self.started_at)
        mean_job = (sum(walls) / len(walls)) if walls else 0.0
        throughput = (bytes_out / wall_total) if wall_total > 0 and bytes_out else None

        return BatchSummary(
            batch_id=self.batch_id,
            started_at=self.started_at,
            ended_at=ended,
            job_count=len(job_list),
            succeeded=succeeded,
            failed=failed,
            wall_seconds=round(wall_total, 3),
            peak_parallel=int(self.peak_parallel),
            parallel_setting=int(self.settings.get("parallel", 1) or 1),
            adaptive_parallel=bool(self.settings.get("adaptive_parallel", True)),
            total_bytes_in=bytes_in,
            total_bytes_out=bytes_out,
            mean_job_seconds=round(mean_job, 3),
            mean_speed_x=round(sum(speeds) / len(speeds), 3) if speeds else None,
            peak_speed_x=round(max(peaks), 3) if peaks else None,
            throughput_bps=round(throughput, 1) if throughput is not None else None,
            eta_mae_seconds=round(sum(eta_errs) / len(eta_errs), 3) if eta_errs else None,
            jobs=[j.to_dict() for j in job_list],
        )


def format_batch_summary(summary: BatchSummary, *, detailed: bool = False) -> str:
    """Human-readable multi-line summary for CLI / status bar / dialogs."""
    lines = [
        f"Performance analytics (local) — batch {summary.batch_id}",
        (
            f"  jobs={summary.job_count} ok={summary.succeeded} fail={summary.failed} "
            f"wall={summary.wall_seconds:.1f}s peak_parallel={summary.peak_parallel}"
            f"/{summary.parallel_setting}"
            + (" (adaptive)" if summary.adaptive_parallel else "")
        ),
    ]
    speed_bits = []
    if summary.mean_speed_x is not None:
        speed_bits.append(f"mean_speed={summary.mean_speed_x:.2f}x")
    if summary.peak_speed_x is not None:
        speed_bits.append(f"peak_speed={summary.peak_speed_x:.2f}x")
    if summary.mean_job_seconds:
        speed_bits.append(f"mean_job={summary.mean_job_seconds:.1f}s")
    if speed_bits:
        lines.append("  " + "  ".join(speed_bits))

    io_bits = []
    if summary.total_bytes_out:
        io_bits.append(f"out={_fmt_bytes(summary.total_bytes_out)}")
    if summary.total_bytes_in:
        io_bits.append(f"in={_fmt_bytes(summary.total_bytes_in)}")
    if summary.throughput_bps is not None:
        io_bits.append(f"throughput={_fmt_bytes(summary.throughput_bps)}/s")
    if summary.eta_mae_seconds is not None:
        io_bits.append(f"eta_mae={summary.eta_mae_seconds:.1f}s")
    if io_bits:
        lines.append("  " + "  ".join(io_bits))

    if detailed:
        for job in summary.jobs:
            name = job.get("src") or f"job-{job.get('wid')}"
            status = "ok" if job.get("success") else "FAIL"
            mean = job.get("mean_speed_x")
            mean_s = f"{mean:.2f}x" if isinstance(mean, (int, float)) else "?"
            thr = job.get("throughput_bps")
            thr_s = _fmt_bytes(thr) + "/s" if isinstance(thr, (int, float)) else "?"
            lines.append(
                f"  [{job.get('wid')}] {name}  {status}  "
                f"wall={float(job.get('wall_seconds') or 0):.1f}s  "
                f"speed={mean_s}  thr={thr_s}"
            )
    lines.append(f"  stored under {batches_path()}")
    return "\n".join(lines)


def format_summary_oneline(summary: BatchSummary) -> str:
    """Compact single-line summary for GUI status bar."""
    parts = [
        f"Analytics: {summary.succeeded}/{summary.job_count} ok",
        f"{summary.wall_seconds:.1f}s",
        f"peak∥{summary.peak_parallel}",
    ]
    if summary.mean_speed_x is not None:
        parts.append(f"{summary.mean_speed_x:.2f}x")
    if summary.throughput_bps is not None:
        parts.append(f"{_fmt_bytes(summary.throughput_bps)}/s")
    if summary.eta_mae_seconds is not None:
        parts.append(f"ETA±{summary.eta_mae_seconds:.0f}s")
    return " · ".join(parts)


def _fmt_bytes(n: float) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    val = float(n)
    for unit in units:
        if abs(val) < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(val)}{unit}"
            return f"{val:.1f}{unit}"
        val /= 1024.0
    return f"{val:.1f}TiB"


def append_batch_summary(
    summary: BatchSummary,
    *,
    config_dir: Optional[Path] = None,
    max_batches: int = MAX_STORED_BATCHES,
) -> Path:
    """Append one batch JSON object to the local JSONL history (trim to max)."""
    path = batches_path(config_dir)
    line = json.dumps(summary.to_dict(), ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line)
    _trim_batches_file(path, max_batches=max_batches)
    return path


def _trim_batches_file(path: Path, *, max_batches: int) -> None:
    if max_batches <= 0 or not path.exists():
        return
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = [ln for ln in fh if ln.strip()]
    except OSError:
        return
    if len(lines) <= max_batches:
        return
    kept = lines[-max_batches:]
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.writelines(kept if kept and kept[-1].endswith("\n") else [k if k.endswith("\n") else k + "\n" for k in kept])
    except OSError:
        return


def load_recent_batches(
    *,
    limit: int = 20,
    config_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Load the most recent stored batch summaries (local JSONL)."""
    path = batches_path(config_dir)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip()]
    except OSError:
        return []
    out: List[Dict[str, Any]] = []
    for line in lines[-max(0, int(limit)) :]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def format_analytics_status(settings: Optional[Dict[str, Any]] = None) -> str:
    """Status text for Preferences / CLI (local-only messaging)."""
    enabled = analytics_enabled(settings)
    recent = load_recent_batches(limit=1)
    lines = [
        "Performance analytics: LOCAL ONLY (never uploaded).",
        f"  Enabled: {'yes' if enabled else 'no (default)'}",
        f"  Store: {batches_path()}",
    ]
    if recent:
        last = recent[-1]
        lines.append(
            f"  Last batch: {last.get('batch_id')} "
            f"({last.get('succeeded')}/{last.get('job_count')} ok, "
            f"{last.get('wall_seconds')}s)"
        )
    else:
        lines.append("  Last batch: (none yet)")
    return "\n".join(lines)
