"""Real FFmpeg preview clips and thumbnails for the companion UI.

Generates short media previews from host paths (same files the Orchestrator
would convert). No fake progress — FFmpeg must succeed or the call fails.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..core.settings import get_config_dir
from ..util.ffmpeg import find_ffmpeg, is_audio_file, is_video_file

PREVIEW_DIRNAME = "companion-previews"
DEFAULT_SECONDS = 3.0
MAX_SECONDS = 15.0
MAX_CACHE = 32

_lock = threading.RLock()
_registry: Dict[str, Dict[str, Any]] = {}


def preview_dir(config_dir: Optional[Path] = None) -> Path:
    root = Path(config_dir) if config_dir is not None else get_config_dir()
    path = root / PREVIEW_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ffmpeg_bin() -> str:
    bin_path = find_ffmpeg()
    if not bin_path:
        raise RuntimeError("ffmpeg_not_found")
    return bin_path


def _cache_key(src: str, seconds: float, kind: str) -> str:
    digest = hashlib.sha256(f"{src}|{seconds:.2f}|{kind}".encode("utf-8")).hexdigest()
    return digest[:20]


def _trim_registry() -> None:
    if len(_registry) <= MAX_CACHE:
        return
    ordered = sorted(_registry.items(), key=lambda kv: float(kv[1].get("created_at") or 0))
    for pid, meta in ordered[: max(0, len(_registry) - MAX_CACHE)]:
        path = Path(str(meta.get("path") or ""))
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass
        _registry.pop(pid, None)


def get_preview(preview_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        meta = _registry.get(preview_id)
        if not meta:
            return None
        path = Path(str(meta.get("path") or ""))
        if not path.is_file():
            _registry.pop(preview_id, None)
            return None
        return dict(meta)


def generate_preview(
    src: str,
    *,
    seconds: float = DEFAULT_SECONDS,
    config_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run FFmpeg to produce a short preview for ``src``.

    Video → JPEG thumbnail (frame at 1s) + short muted MP4 snippet.
    Audio → short AAC/M4A clip from the start.
    """
    path = Path(src).expanduser()
    if not path.is_file():
        return {"ok": False, "error": "not_a_file", "path": str(path)}

    src_s = str(path.resolve())
    try:
        secs = float(seconds)
    except (TypeError, ValueError):
        secs = DEFAULT_SECONDS
    secs = max(0.5, min(MAX_SECONDS, secs))

    if is_video_file(src_s):
        kind = "video"
    elif is_audio_file(src_s):
        kind = "audio"
    else:
        return {"ok": False, "error": "unsupported_media", "path": src_s}

    key = _cache_key(src_s, secs, kind)
    with _lock:
        for pid, meta in _registry.items():
            if meta.get("cache_key") == key and Path(str(meta.get("path") or "")).is_file():
                return {
                    "ok": True,
                    "cached": True,
                    "preview_id": pid,
                    "kind": meta["kind"],
                    "mime": meta["mime"],
                    "seconds": meta.get("seconds"),
                    "file": os.path.basename(src_s),
                    "url": f"/api/preview/{pid}",
                    "thumb_url": meta.get("thumb_url"),
                }

    out_root = preview_dir(config_dir)
    preview_id = uuid.uuid4().hex[:12]
    ffmpeg = _ffmpeg_bin()

    try:
        if kind == "video":
            result = _make_video_preview(
                ffmpeg, src_s, out_root, preview_id, secs, key
            )
        else:
            result = _make_audio_preview(
                ffmpeg, src_s, out_root, preview_id, secs, key
            )
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc), "file": os.path.basename(src_s)}

    with _lock:
        _registry[preview_id] = result
        _trim_registry()

    payload = {
        "ok": True,
        "cached": False,
        "preview_id": preview_id,
        "kind": result["kind"],
        "mime": result["mime"],
        "seconds": result.get("seconds"),
        "file": os.path.basename(src_s),
        "url": f"/api/preview/{preview_id}",
    }
    if result.get("thumb_url"):
        payload["thumb_url"] = result["thumb_url"]
    return payload


def _run_ffmpeg(cmd: list, *, timeout: float = 60.0) -> None:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg_not_found") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("preview_timeout") from exc
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", errors="replace")[-400:]
        raise RuntimeError(f"ffmpeg_failed: {err.strip() or proc.returncode}")


def _make_video_preview(
    ffmpeg: str,
    src: str,
    out_root: Path,
    preview_id: str,
    seconds: float,
    cache_key: str,
) -> Dict[str, Any]:
    clip = out_root / f"{preview_id}.mp4"
    thumb = out_root / f"{preview_id}.jpg"
    thumb_id = f"{preview_id}-thumb"

    _run_ffmpeg(
        [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-ss",
            "1",
            "-i",
            src,
            "-frames:v",
            "1",
            "-q:v",
            "4",
            str(thumb),
        ],
        timeout=45.0,
    )
    _run_ffmpeg(
        [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-ss",
            "0",
            "-i",
            src,
            "-t",
            f"{seconds:.2f}",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "28",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(clip),
        ],
        timeout=90.0,
    )
    if not clip.is_file() or clip.stat().st_size < 64:
        raise RuntimeError("preview_empty")

    created = time.time()
    with _lock:
        _registry[thumb_id] = {
            "path": str(thumb),
            "mime": "image/jpeg",
            "kind": "thumb",
            "created_at": created,
            "cache_key": cache_key + "-thumb",
            "seconds": None,
            "src": src,
            "thumb_url": None,
        }

    return {
        "path": str(clip),
        "mime": "video/mp4",
        "kind": "video",
        "created_at": created,
        "cache_key": cache_key,
        "seconds": seconds,
        "src": src,
        "thumb_url": f"/api/preview/{thumb_id}",
    }


def _make_audio_preview(
    ffmpeg: str,
    src: str,
    out_root: Path,
    preview_id: str,
    seconds: float,
    cache_key: str,
) -> Dict[str, Any]:
    clip = out_root / f"{preview_id}.m4a"
    _run_ffmpeg(
        [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-ss",
            "0",
            "-i",
            src,
            "-t",
            f"{seconds:.2f}",
            "-vn",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(clip),
        ],
        timeout=60.0,
    )
    if not clip.is_file() or clip.stat().st_size < 32:
        raise RuntimeError("preview_empty")
    return {
        "path": str(clip),
        "mime": "audio/mp4",
        "kind": "audio",
        "created_at": time.time(),
        "cache_key": cache_key,
        "seconds": seconds,
        "src": src,
        "thumb_url": None,
    }


def resolve_preview_source(
    *,
    path: Optional[str] = None,
    wid: Optional[int] = None,
    hub: Any = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve a host media path from an explicit path or active worker id.

    Returns ``(src_path, error)``.
    """
    if path:
        return str(Path(path).expanduser()), None
    if wid is None or hub is None:
        return None, "path_or_wid_required"

    # Prefer full path from hub active state (set in on_started).
    active = getattr(hub, "_active", None) or {}
    state = active.get(int(wid))
    if state is not None and getattr(state, "src", None):
        return str(state.src), None

    orch = getattr(hub, "_orchestrator", None)
    workers = getattr(orch, "workers", None) or {}
    worker = workers.get(int(wid))
    if worker is None:
        return None, "worker_not_found"
    job = getattr(worker, "job", None)
    src = getattr(job, "src", None) if job is not None else None
    if not src:
        return None, "no_source"
    return str(src), None
