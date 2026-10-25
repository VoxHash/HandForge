"""Crash-safe conversion queue persistence under ``~/.handforge/queue.json``.

Stores pending / queued / active jobs (and light session options) so a GUI or
``handforge serve`` restart can restore unfinished work. Uses atomic JSON
replace writes; completed/empty queues clear the file.
"""

from __future__ import annotations

import os
import time
from dataclasses import fields
from typing import Any, Dict, Iterable, List, Optional, Sequence

from . import settings as _settings
from .models import Job

QUEUE_FILENAME = "queue.json"
QUEUE_VERSION = 1

_JOB_FIELD_NAMES = {f.name for f in fields(Job)}


def queue_path():
    return _settings.get_config_dir() / QUEUE_FILENAME


def job_to_dict(job: Job) -> Dict[str, Any]:
    return job.to_dict()


def job_from_dict(data: Any) -> Optional[Job]:
    """Rebuild a Job from persisted JSON; ignore unknown keys / bad rows."""
    if not isinstance(data, dict):
        return None
    filtered = {k: v for k, v in data.items() if k in _JOB_FIELD_NAMES}
    src = filtered.get("src")
    dst = filtered.get("dst_dir")
    fmt = filtered.get("format")
    if not src or not dst or not fmt:
        return None
    try:
        return Job(**filtered)
    except TypeError:
        return None


def _jobs_to_dicts(jobs: Iterable[Job]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for job in jobs:
        try:
            out.append(job_to_dict(job))
        except Exception:  # noqa: BLE001 — never break host for one bad job
            continue
    return out


def _dicts_to_jobs(rows: Any) -> List[Job]:
    if not isinstance(rows, list):
        return []
    jobs: List[Job] = []
    for row in rows:
        job = job_from_dict(row)
        if job is not None:
            jobs.append(job)
    return jobs


def _atomic_write_json(path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    import json

    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass
    os.replace(tmp, path)


def clear_queue_state() -> None:
    """Remove durable queue state (safe when queue is empty / cleared)."""
    path = queue_path()
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        if tmp.is_file():
            tmp.unlink()
    except OSError:
        pass


def save_queue_state(
    *,
    pending: Optional[Sequence[Job]] = None,
    queued: Optional[Sequence[Job]] = None,
    active: Optional[Sequence[Job]] = None,
    session: Optional[Dict[str, Any]] = None,
) -> None:
    """Persist unfinished work. Clears the file when all lists are empty."""
    pending_jobs = list(pending or [])
    queued_jobs = list(queued or [])
    active_jobs = list(active or [])
    if not pending_jobs and not queued_jobs and not active_jobs:
        clear_queue_state()
        return
    payload: Dict[str, Any] = {
        "version": QUEUE_VERSION,
        "updated_at": time.time(),
        "pending": _jobs_to_dicts(pending_jobs),
        "queued": _jobs_to_dicts(queued_jobs),
        "active": _jobs_to_dicts(active_jobs),
        "session": dict(session or {}),
    }
    _atomic_write_json(queue_path(), payload)


def load_queue_state() -> Dict[str, Any]:
    """Load durable queue state. Missing/corrupt → empty structure."""
    raw = _settings.load_json_file(QUEUE_FILENAME, default=None)
    empty: Dict[str, Any] = {
        "version": QUEUE_VERSION,
        "updated_at": None,
        "pending": [],
        "queued": [],
        "active": [],
        "session": {},
    }
    if not isinstance(raw, dict):
        return empty
    return {
        "version": int(raw.get("version") or QUEUE_VERSION),
        "updated_at": raw.get("updated_at"),
        "pending": _dicts_to_jobs(raw.get("pending")),
        "queued": _dicts_to_jobs(raw.get("queued")),
        "active": _dicts_to_jobs(raw.get("active")),
        "session": dict(raw.get("session") or {})
        if isinstance(raw.get("session"), dict)
        else {},
    }


def jobs_for_restore(
    state: Optional[Dict[str, Any]] = None,
    *,
    require_existing: bool = True,
) -> List[Job]:
    """Flatten pending + queued + active for restore (dedupe by ``src``).

    Active/queued jobs are treated as unfinished and become pending again after
    a crash. When ``require_existing`` is True, skip missing source files.
    """
    snap = state if state is not None else load_queue_state()
    seen: set = set()
    restored: List[Job] = []
    for job in list(snap.get("pending") or []) + list(snap.get("queued") or []) + list(
        snap.get("active") or []
    ):
        src = os.path.realpath(job.src) if job.src else ""
        key = src or job.src
        if not key or key in seen:
            continue
        if require_existing and (not src or not os.path.isfile(src)):
            continue
        if src:
            job.src = src
        seen.add(key)
        restored.append(job)
    return restored


def collect_active_jobs(orchestrator: Any) -> List[Job]:
    """Jobs currently owned by Orchestrator workers."""
    workers = getattr(orchestrator, "workers", None) or {}
    jobs: List[Job] = []
    for worker in list(workers.values()):
        job = getattr(worker, "job", None)
        if isinstance(job, Job):
            jobs.append(job)
    return jobs


def persist_live_queue(
    *,
    pending: Optional[Sequence[Job]] = None,
    orchestrator: Any = None,
    session: Optional[Dict[str, Any]] = None,
) -> None:
    """Snapshot GUI/session pending + Orchestrator queued/active into disk."""
    queued: List[Job] = []
    active: List[Job] = []
    if orchestrator is not None:
        queued = list(getattr(orchestrator, "job_queue", []) or [])
        active = collect_active_jobs(orchestrator)
    # While a batch is running, unfinished work lives in queued/active.
    # Idle: persist the caller's pending list (GUI queue / serve pending).
    if queued or active:
        save_queue_state(
            pending=[],
            queued=queued,
            active=active,
            session=session,
        )
    else:
        save_queue_state(
            pending=list(pending or []),
            queued=[],
            active=[],
            session=session,
        )
