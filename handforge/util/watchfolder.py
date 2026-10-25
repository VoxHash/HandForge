"""Watch-folder / hotfolder auto-convert for HandForge.

Polls one or more directories for new media files, tracks them in
``seen_files.json``, and yields paths ready for conversion. No invented
files — only real paths that exist on disk and pass audio/video checks.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from ..core.settings import load_seen_files, save_seen_files
from .ffmpeg import is_audio_file, is_video_file

SETTING_ENABLED = "watchfolder_enabled"
SETTING_DIRS = "watchfolder_dirs"
SETTING_INTERVAL = "watchfolder_interval_seconds"
SETTING_RECURSIVE = "watchfolder_recursive"

DEFAULT_INTERVAL = 5.0
MIN_INTERVAL = 1.0
MAX_INTERVAL = 3600.0


def watchfolder_enabled(settings: Optional[Dict[str, Any]] = None) -> bool:
    if not settings:
        return False
    return bool(settings.get(SETTING_ENABLED, False))


def watchfolder_dirs(settings: Optional[Dict[str, Any]] = None) -> List[str]:
    cfg = dict(settings or {})
    raw = cfg.get(SETTING_DIRS) or []
    if isinstance(raw, str):
        raw = [raw]
    out: List[str] = []
    for item in raw:
        text = str(item or "").strip()
        if text:
            out.append(str(Path(text).expanduser()))
    return out


def watchfolder_interval(settings: Optional[Dict[str, Any]] = None) -> float:
    cfg = dict(settings or {})
    try:
        val = float(cfg.get(SETTING_INTERVAL) or DEFAULT_INTERVAL)
    except (TypeError, ValueError):
        val = DEFAULT_INTERVAL
    return max(MIN_INTERVAL, min(MAX_INTERVAL, val))


def watchfolder_recursive(settings: Optional[Dict[str, Any]] = None) -> bool:
    if not settings:
        return True
    return bool(settings.get(SETTING_RECURSIVE, True))


def _file_fingerprint(path: Path) -> Dict[str, Any]:
    st = path.stat()
    return {
        "path": str(path.resolve()),
        "size": int(st.st_size),
        "mtime": float(st.st_mtime),
    }


def is_stable_media(
    path: Path,
    *,
    settle_seconds: float = 1.5,
    previous: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """Return True when the file looks finished writing (size/mtime stable)."""
    if not path.is_file():
        return False, None
    try:
        fp = _file_fingerprint(path)
    except OSError:
        return False, None
    if previous is None:
        return False, fp
    if (
        previous.get("size") == fp["size"]
        and abs(float(previous.get("mtime") or 0) - fp["mtime"]) < 0.01
    ):
        # Require a short settle so partial downloads are not converted.
        age = time.time() - fp["mtime"]
        if age >= settle_seconds:
            return True, fp
    return False, fp


def iter_media_files(roots: Sequence[str], *, recursive: bool = True) -> List[Path]:
    found: List[Path] = []
    for root in roots:
        base = Path(root).expanduser()
        if not base.is_dir():
            continue
        if recursive:
            walker: Iterable[Path] = base.rglob("*")
        else:
            walker = base.iterdir()
        for path in walker:
            try:
                if not path.is_file():
                    continue
            except OSError:
                continue
            src = str(path)
            if is_audio_file(src) or is_video_file(src):
                found.append(path)
    found.sort(key=lambda p: str(p).lower())
    return found


def seen_key(path: Path) -> str:
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def filter_new_stable_files(
    paths: Sequence[Path],
    seen: Dict[str, Any],
    *,
    pending_fps: Optional[Dict[str, Dict[str, Any]]] = None,
    settle_seconds: float = 1.5,
) -> Tuple[List[Path], Dict[str, Dict[str, Any]]]:
    """Return newly stable media paths not already recorded in ``seen``.

    ``pending_fps`` carries fingerprints between polls for settle detection.
    """
    pending = dict(pending_fps or {})
    ready: List[Path] = []
    for path in paths:
        key = seen_key(path)
        if key in seen:
            pending.pop(key, None)
            continue
        prev = pending.get(key)
        stable, fp = is_stable_media(path, settle_seconds=settle_seconds, previous=prev)
        if fp is None:
            pending.pop(key, None)
            continue
        pending[key] = fp
        if stable:
            ready.append(path)
    return ready, pending


def mark_seen(
    seen: Dict[str, Any],
    paths: Sequence[Path],
    *,
    status: str = "queued",
) -> Dict[str, Any]:
    now = time.time()
    for path in paths:
        key = seen_key(path)
        try:
            fp = _file_fingerprint(path)
        except OSError:
            fp = {"path": key, "size": None, "mtime": None}
        seen[key] = {
            **fp,
            "status": status,
            "seen_at": now,
        }
    return seen


def scan_once(
    roots: Sequence[str],
    *,
    seen: Optional[Dict[str, Any]] = None,
    recursive: bool = True,
    pending_fps: Optional[Dict[str, Dict[str, Any]]] = None,
    settle_seconds: float = 1.5,
) -> Tuple[List[Path], Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Single watch-folder scan. Returns (new_paths, updated_seen, pending_fps)."""
    cache = dict(seen if seen is not None else load_seen_files())
    media = iter_media_files(roots, recursive=recursive)
    ready, pending = filter_new_stable_files(
        media, cache, pending_fps=pending_fps, settle_seconds=settle_seconds
    )
    if ready:
        mark_seen(cache, ready, status="queued")
    return ready, cache, pending


def format_watchfolder_status(settings: Optional[Dict[str, Any]] = None) -> str:
    cfg = dict(settings or {})
    dirs = watchfolder_dirs(cfg)
    lines = [
        "Watch-folder / hotfolder auto-convert:",
        f"  enabled: {'yes' if watchfolder_enabled(cfg) else 'no (opt-in; default off)'}",
        f"  interval: {watchfolder_interval(cfg):.1f}s",
        f"  recursive: {'yes' if watchfolder_recursive(cfg) else 'no'}",
        f"  dirs: {', '.join(dirs) if dirs else '(none configured)'}",
        f"  seen cache: seen_files.json under config dir",
    ]
    return "\n".join(lines)
