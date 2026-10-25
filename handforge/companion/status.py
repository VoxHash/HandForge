"""Serialize live Orchestrator queue / active jobs for the companion API."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from ..core.models import Job

MAX_RECENT = 30


def serialize_job_summary(job: Job, *, position: Optional[int] = None) -> Dict[str, Any]:
    """Compact, phone-friendly job summary (basename only for privacy on LAN)."""
    src = job.src or ""
    data: Dict[str, Any] = {
        "file": os.path.basename(src) if src else "",
        "format": job.format or "",
        "mode": job.mode or "",
    }
    if position is not None:
        data["position"] = int(position)
    return data


@dataclass
class ActiveJobState:
    wid: int
    src: str
    format: str = ""
    mode: str = ""
    progress: float = 0.0
    elapsed: float = 0.0
    eta: float = 0.0
    speed: str = ""
    status: str = "running"
    started_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wid": self.wid,
            "file": os.path.basename(self.src) if self.src else "",
            "format": self.format,
            "mode": self.mode,
            "progress": round(float(self.progress), 2),
            "elapsed": round(float(self.elapsed), 2),
            "eta": round(float(self.eta), 2),
            "speed": self.speed or "",
            "status": self.status,
        }


@dataclass
class RecentJobState:
    wid: int
    src: str
    success: bool
    message: str
    output_path: str
    finished_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        out = self.output_path or ""
        return {
            "wid": self.wid,
            "file": os.path.basename(self.src) if self.src else "",
            "success": bool(self.success),
            "message": (self.message or "").splitlines()[0][:200] if self.message else "",
            "output": os.path.basename(out) if out else "",
            "finished_at": self.finished_at,
        }


class QueueStatusHub:
    """Thread-safe snapshot of queue + active conversions from Orchestrator signals."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._orchestrator: Any = None
        self._pending_provider: Optional[Callable[[], Sequence[Job]]] = None
        self._active: Dict[int, ActiveJobState] = {}
        self._recent: List[RecentJobState] = []
        self._batch_started_at: Optional[float] = None
        self._app_label: str = "HandForge"

    def attach(
        self,
        orchestrator: Any,
        *,
        pending_provider: Optional[Callable[[], Sequence[Job]]] = None,
        app_label: str = "HandForge",
    ) -> None:
        with self._lock:
            self._orchestrator = orchestrator
            self._pending_provider = pending_provider
            self._app_label = app_label or "HandForge"

    def detach(self) -> None:
        with self._lock:
            self._orchestrator = None
            self._pending_provider = None

    def clear(self) -> None:
        with self._lock:
            self._active.clear()
            self._recent.clear()
            self._batch_started_at = None

    def on_started(self, wid: int, file_path: str) -> None:
        fmt = ""
        mode = ""
        orch = self._orchestrator
        if orch is not None and wid in getattr(orch, "workers", {}):
            job = orch.workers[wid].job
            fmt = job.format or ""
            mode = job.mode or ""
        with self._lock:
            if self._batch_started_at is None:
                self._batch_started_at = time.time()
            self._active[int(wid)] = ActiveJobState(
                wid=int(wid),
                src=file_path or "",
                format=fmt,
                mode=mode,
            )

    def on_progress(
        self,
        wid: int,
        progress: float,
        elapsed: float,
        eta: float,
        speed: str,
        *_rest: Any,
    ) -> None:
        with self._lock:
            state = self._active.get(int(wid))
            if state is None:
                state = ActiveJobState(wid=int(wid), src="")
                self._active[int(wid)] = state
            # Keep progress monotonic for remote clients
            state.progress = max(float(state.progress), float(progress or 0.0))
            state.elapsed = float(elapsed or 0.0)
            state.eta = float(eta or 0.0)
            if speed:
                state.speed = str(speed)
            state.status = "running"

    def on_done(
        self,
        wid: int,
        success: bool,
        message: str,
        output_path: str,
    ) -> None:
        with self._lock:
            state = self._active.pop(int(wid), None)
            src = state.src if state else ""
            recent = RecentJobState(
                wid=int(wid),
                src=src,
                success=bool(success),
                message=message or "",
                output_path=output_path or "",
            )
            self._recent.insert(0, recent)
            del self._recent[MAX_RECENT:]
            if not self._active:
                orch = self._orchestrator
                queued = list(getattr(orch, "job_queue", []) or []) if orch else []
                if not queued:
                    self._batch_started_at = None

    def snapshot(self) -> Dict[str, Any]:
        """Build a JSON-serializable status dict from live Orchestrator state."""
        with self._lock:
            orch = self._orchestrator
            active_map = {k: v.to_dict() for k, v in self._active.items()}
            recent = [r.to_dict() for r in self._recent]
            batch_started = self._batch_started_at
            app_label = self._app_label
            pending_provider = self._pending_provider

        queued: List[Dict[str, Any]] = []
        active_from_orch: List[Dict[str, Any]] = []
        parallel = 0
        adaptive = True
        if orch is not None:
            settings = getattr(orch, "settings", {}) or {}
            parallel = int(settings.get("parallel", getattr(orch, "max_parallel", 2)) or 2)
            adaptive = bool(settings.get("adaptive_parallel", True))
            for i, job in enumerate(list(getattr(orch, "job_queue", []) or []), start=1):
                queued.append(serialize_job_summary(job, position=i))
            workers = getattr(orch, "workers", {}) or {}
            for wid, worker in list(workers.items()):
                job = worker.job
                base = serialize_job_summary(job)
                live = active_map.get(int(wid), {})
                active_from_orch.append(
                    {
                        "wid": int(wid),
                        "file": live.get("file") or base["file"],
                        "format": live.get("format") or base["format"],
                        "mode": live.get("mode") or base["mode"],
                        "progress": live.get("progress", 0.0),
                        "elapsed": live.get("elapsed", 0.0),
                        "eta": live.get("eta", 0.0),
                        "speed": live.get("speed", ""),
                        "status": live.get("status", "running"),
                        "paused": bool(getattr(worker, "_paused", False)),
                    }
                )
        else:
            active_from_orch = list(active_map.values())

        # GUI jobs waiting for Start (not yet enqueued to Orchestrator)
        pending: List[Dict[str, Any]] = []
        if pending_provider is not None:
            try:
                jobs = list(pending_provider() or [])
            except Exception:  # noqa: BLE001 — never break status API
                jobs = []
            for i, job in enumerate(jobs, start=1):
                pending.append(serialize_job_summary(job, position=i))

        active_count = len(active_from_orch)
        queued_count = len(queued)
        pending_count = len(pending)
        if active_count > 0 or queued_count > 0:
            state = "running"
        elif pending_count > 0:
            state = "queued"
        else:
            state = "idle"

        total_progress = 0.0
        if active_from_orch:
            total_progress = sum(float(a.get("progress") or 0) for a in active_from_orch) / len(
                active_from_orch
            )

        return {
            "app": app_label,
            "state": state,
            "updated_at": time.time(),
            "batch_started_at": batch_started,
            "parallel": parallel,
            "adaptive_parallel": adaptive,
            "counts": {
                "pending": pending_count,
                "queued": queued_count,
                "active": active_count,
                "recent": len(recent),
            },
            "aggregate_progress": round(total_progress, 2),
            "pending": pending,
            "queued": queued,
            "active": sorted(active_from_orch, key=lambda a: int(a.get("wid") or 0)),
            "recent": recent,
        }


def serialize_status(hub: QueueStatusHub) -> Dict[str, Any]:
    """Public alias used by tests and the HTTP layer."""
    return hub.snapshot()
