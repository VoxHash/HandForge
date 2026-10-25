"""Shared-workstation control over a live Orchestrator session.

Mutations are opt-in (caller must attach a SessionController to CompanionServer)
and are intended to be gated by a shared token at the HTTP layer. Paths accepted
for ``add_paths`` must exist as media files on this host — anyone with the token
can enqueue readable media; keep the token private and prefer localhost or a
firewall when binding to the LAN.
"""

from __future__ import annotations

import os
import threading
from typing import Any, Callable, Dict, List, Optional, Sequence

from ..core.models import Job
from ..core.presets import all_presets, get_preset
from ..util.ffmpeg import is_audio_file, is_video_file


def _basename(path: str) -> str:
    return os.path.basename(path or "") if path else ""


class SessionController:
    """Thread-safe control surface for pending jobs + Orchestrator start/stop."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._orchestrator: Any = None
        self._settings: Dict[str, Any] = {}
        self._pending: List[Job] = []
        self._preset_name: str = "MP3 192k"
        self._format: str = "mp3"
        self._mode: str = "CBR"
        self._bitrate: Optional[str] = "192"
        self._output_dir: str = ""
        # Optional GUI / host hooks (run on whatever thread the hook chooses)
        self._start_handler: Optional[Callable[[], Any]] = None
        self._stop_handler: Optional[Callable[[], Any]] = None
        self._add_paths_handler: Optional[Callable[[Sequence[str]], Dict[str, Any]]] = None
        self._remove_pending_handler: Optional[Callable[[int], Dict[str, Any]]] = None
        self._options_handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None
        self._pending_provider: Optional[Callable[[], Sequence[Job]]] = None
        self._notify: Optional[Callable[[], None]] = None

    def attach(
        self,
        orchestrator: Any,
        settings: Optional[Dict[str, Any]] = None,
        *,
        pending: Optional[List[Job]] = None,
        pending_provider: Optional[Callable[[], Sequence[Job]]] = None,
        preset_name: Optional[str] = None,
        start_handler: Optional[Callable[[], Any]] = None,
        stop_handler: Optional[Callable[[], Any]] = None,
        add_paths_handler: Optional[Callable[[Sequence[str]], Dict[str, Any]]] = None,
        remove_pending_handler: Optional[Callable[[int], Dict[str, Any]]] = None,
        options_handler: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
        notify: Optional[Callable[[], None]] = None,
    ) -> None:
        with self._lock:
            self._orchestrator = orchestrator
            self._settings = dict(settings or getattr(orchestrator, "settings", {}) or {})
            if pending is not None:
                self._pending = pending
            self._pending_provider = pending_provider
            out = self._settings.get("output_dir") or ""
            self._output_dir = str(out) if out else os.path.join(
                os.path.expanduser("~"), "HandForge"
            )
            if preset_name:
                self._preset_name = preset_name
                self._apply_preset_locked(preset_name)
            self._start_handler = start_handler
            self._stop_handler = stop_handler
            self._add_paths_handler = add_paths_handler
            self._remove_pending_handler = remove_pending_handler
            self._options_handler = options_handler
            self._notify = notify

    def detach(self) -> None:
        with self._lock:
            self._orchestrator = None
            self._pending = []
            self._pending_provider = None
            self._start_handler = None
            self._stop_handler = None
            self._add_paths_handler = None
            self._remove_pending_handler = None
            self._options_handler = None
            self._notify = None

    def _fire_notify(self) -> None:
        cb = self._notify
        if cb is not None:
            try:
                cb()
            except Exception:  # noqa: BLE001
                pass

    def _pending_jobs(self) -> List[Job]:
        if self._pending_provider is not None:
            try:
                return list(self._pending_provider() or [])
            except Exception:  # noqa: BLE001
                return []
        return list(self._pending)

    def _apply_preset_locked(self, name: str) -> None:
        try:
            opts = get_preset(name)
        except KeyError:
            return
        self._preset_name = name
        self._format = str(opts.get("format") or self._format or "mp3")
        self._mode = str(opts.get("mode") or self._mode or "CBR")
        if "bitrate" in opts:
            self._bitrate = opts.get("bitrate")
        if "vbrq" in opts:
            # keep bitrate for CBR; vbrq stored via format options on start
            pass

    def control_snapshot(self) -> Dict[str, Any]:
        """JSON-serializable control panel state (presets, output, format)."""
        with self._lock:
            presets = sorted(all_presets().keys())
            out = self._output_dir
            preset = self._preset_name
            fmt = self._format
            mode = self._mode
            bitrate = self._bitrate
            pending_count = len(self._pending_jobs())
            orch = self._orchestrator
        queued = 0
        active = 0
        if orch is not None:
            queued = len(list(getattr(orch, "job_queue", []) or []))
            active = len(dict(getattr(orch, "workers", {}) or {}))
        return {
            "control": True,
            "output_dir": out,
            "output_name": _basename(out) or out,
            "preset": preset,
            "format": fmt,
            "mode": mode,
            "bitrate": bitrate,
            "presets": presets,
            "pending_count": pending_count,
            "queued_count": queued,
            "active_count": active,
            "writes_require_token": True,
            "risks": (
                "Anyone with the companion token can start/stop encodes and enqueue "
                "existing media files on this host. Prefer localhost, a firewall, "
                "and a strong token on LAN binds."
            ),
        }

    def set_options(
        self,
        *,
        output_dir: Optional[str] = None,
        preset: Optional[str] = None,
        format: Optional[str] = None,
        mode: Optional[str] = None,
        bitrate: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {
            k: v
            for k, v in {
                "output_dir": output_dir,
                "preset": preset,
                "format": format,
                "mode": mode,
                "bitrate": bitrate,
            }.items()
            if v is not None
        }

        with self._lock:
            if output_dir is not None:
                path = os.path.expanduser(str(output_dir).strip())
                if not path:
                    return {"ok": False, "error": "empty_output_dir"}
                try:
                    os.makedirs(path, exist_ok=True)
                except OSError as exc:
                    return {"ok": False, "error": "output_dir_unusable", "detail": str(exc)}
                if not os.path.isdir(path) or not os.access(path, os.W_OK):
                    return {"ok": False, "error": "output_dir_not_writable"}
                self._output_dir = os.path.realpath(path)
                self._settings["output_dir"] = self._output_dir
                orch = self._orchestrator
                if orch is not None:
                    settings = getattr(orch, "settings", None)
                    if isinstance(settings, dict):
                        settings["output_dir"] = self._output_dir
                    for job in self._pending:
                        job.dst_dir = self._output_dir
            if preset is not None:
                name = str(preset).strip()
                try:
                    get_preset(name)
                except KeyError:
                    return {"ok": False, "error": "unknown_preset", "preset": name}
                self._apply_preset_locked(name)
            if format is not None:
                self._format = str(format).strip().lstrip(".") or self._format
            if mode is not None:
                self._mode = str(mode).strip() or self._mode
            if bitrate is not None:
                self._bitrate = str(bitrate).strip() or None
            snap = {
                "ok": True,
                "output_dir": self._output_dir,
                "preset": self._preset_name,
                "format": self._format,
                "mode": self._mode,
                "bitrate": self._bitrate,
            }
            handler = self._options_handler

        if handler is not None:
            try:
                host_result = handler(payload)
                if isinstance(host_result, dict) and host_result.get("ok") is False:
                    self._fire_notify()
                    return host_result
            except Exception as exc:  # noqa: BLE001
                self._fire_notify()
                return {"ok": False, "error": "options_handler_failed", "detail": str(exc)}

        self._fire_notify()
        return snap

    def add_paths(self, paths: Sequence[str]) -> Dict[str, Any]:
        handler = None
        with self._lock:
            handler = self._add_paths_handler
        if handler is not None:
            result = handler(list(paths)) or {"ok": True}
            self._fire_notify()
            return result if isinstance(result, dict) else {"ok": True}

        added: List[str] = []
        skipped: List[Dict[str, str]] = []
        with self._lock:
            out = self._output_dir or str(self._settings.get("output_dir") or "")
            if not out:
                out = os.path.join(os.path.expanduser("~"), "HandForge")
                try:
                    os.makedirs(out, exist_ok=True)
                except OSError:
                    pass
                self._output_dir = out
            fmt = self._format or "mp3"
            mode = self._mode or "CBR"
            bitrate = self._bitrate
            for raw in paths:
                src = os.path.expanduser(str(raw or "").strip())
                if not src:
                    skipped.append({"path": "", "reason": "empty"})
                    continue
                real = os.path.realpath(src)
                if not os.path.isfile(real):
                    skipped.append({"path": _basename(src) or src, "reason": "not_a_file"})
                    continue
                if not (is_audio_file(real) or is_video_file(real)):
                    skipped.append({"path": _basename(real), "reason": "unsupported_media"})
                    continue
                if any(j.src == real for j in self._pending):
                    skipped.append({"path": _basename(real), "reason": "duplicate"})
                    continue
                default_fmt = "mp4" if is_video_file(real) else fmt
                job = Job(
                    src=real,
                    dst_dir=out,
                    format=default_fmt if is_video_file(real) else fmt,
                    mode=mode,
                    bitrate=bitrate,
                )
                self._pending.append(job)
                added.append(_basename(real))
        self._fire_notify()
        return {
            "ok": True,
            "added": added,
            "skipped": skipped,
            "pending_count": len(self._pending_jobs()),
        }

    def remove_pending(self, index: int) -> Dict[str, Any]:
        """Remove a pending job by 0-based index."""
        handler = None
        with self._lock:
            handler = self._remove_pending_handler
        if handler is not None:
            result = handler(int(index)) or {"ok": True}
            self._fire_notify()
            return result if isinstance(result, dict) else {"ok": True}

        with self._lock:
            if self._pending_provider is not None and self._remove_pending_handler is None:
                # GUI should supply a handler when using an external pending list
                return {"ok": False, "error": "pending_not_mutable"}
            idx = int(index)
            if idx < 0 or idx >= len(self._pending):
                return {"ok": False, "error": "index_out_of_range"}
            job = self._pending.pop(idx)
            removed = _basename(job.src)
        self._fire_notify()
        return {"ok": True, "removed": removed, "scope": "pending"}

    def remove_queued(self, index: int) -> Dict[str, Any]:
        """Remove a not-yet-started Orchestrator queue job by 0-based index."""
        with self._lock:
            orch = self._orchestrator
        if orch is None:
            return {"ok": False, "error": "no_orchestrator"}
        q = getattr(orch, "job_queue", None)
        if q is None:
            return {"ok": False, "error": "no_queue"}
        idx = int(index)
        if idx < 0 or idx >= len(q):
            return {"ok": False, "error": "index_out_of_range"}
        job = q.pop(idx)
        self._fire_notify()
        return {"ok": True, "removed": _basename(job.src), "scope": "queued"}

    def clear_pending(self) -> Dict[str, Any]:
        with self._lock:
            if self._remove_pending_handler is not None and self._pending_provider is not None:
                # Clear via repeated remove is awkward; mutate provider list if shared
                jobs = self._pending_jobs()
                n = len(jobs)
            else:
                n = len(self._pending)
                self._pending.clear()
        if self._remove_pending_handler is not None and self._pending_provider is not None:
            # Remove from end to start so indices stay valid
            for i in range(n - 1, -1, -1):
                self._remove_pending_handler(i)
        self._fire_notify()
        return {"ok": True, "cleared": n, "scope": "pending"}

    def start(self) -> Dict[str, Any]:
        handler = None
        with self._lock:
            handler = self._start_handler
            orch = self._orchestrator
            pending = list(self._pending)
            fmt = self._format
            mode = self._mode
            bitrate = self._bitrate
            preset = self._preset_name
            out = self._output_dir
        if handler is not None:
            handler()
            self._fire_notify()
            return {"ok": True, "mode": "delegated"}
        if orch is None:
            return {"ok": False, "error": "no_orchestrator"}
        if not pending:
            return {"ok": False, "error": "no_pending_jobs"}
        try:
            opts = get_preset(preset)
        except KeyError:
            opts = {
                "format": fmt,
                "mode": mode,
                "bitrate": bitrate,
            }
        jobs: List[Job] = []
        for job in pending:
            job.dst_dir = out or job.dst_dir
            job.format = str(opts.get("format") or fmt or job.format)
            job.mode = str(opts.get("mode") or mode or job.mode)
            if "bitrate" in opts:
                job.bitrate = opts.get("bitrate")
            elif bitrate:
                job.bitrate = bitrate
            if "vbrq" in opts:
                job.vbrq = opts.get("vbrq")
            if is_video_file(job.src) and is_video_file(f"dummy.{job.format}"):
                job.video_codec = opts.get("video_codec")
                job.video_bitrate = opts.get("video_bitrate")
                job.video_quality = opts.get("video_quality")
            elif is_video_file(job.src) and not is_video_file(f"dummy.{job.format}"):
                job.extract_audio_only = True
            jobs.append(job)
        with self._lock:
            self._pending.clear()
        orch.enqueue(jobs)
        self._fire_notify()
        return {"ok": True, "mode": "orchestrator", "enqueued": len(jobs)}

    def stop(self) -> Dict[str, Any]:
        handler = None
        with self._lock:
            handler = self._stop_handler
            orch = self._orchestrator
        if handler is not None:
            handler()
            self._fire_notify()
            return {"ok": True, "mode": "delegated"}
        if orch is None:
            return {"ok": False, "error": "no_orchestrator"}
        orch.stop_all()
        self._fire_notify()
        return {"ok": True, "mode": "orchestrator"}
