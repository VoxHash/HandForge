"""Proton Drive backup helpers for HandForge.

Uses the real **proton-drive** CLI already installed on the machine
(``proton-drive filesystem upload|list|create-folder``). No API keys or
tokens are stored in HandForge — auth lives in the Proton Drive CLI
session (``proton-drive auth login``).

Optional companion: **proton-drive-desktop** (local GUI / sync worker)
is detected for status only; uploads always go through ``proton-drive``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

# Settings keys (merged in core.settings defaults).
SETTING_PROTON_BACKUP_ENABLED = "proton_drive_backup_enabled"
SETTING_PROTON_REMOTE_FOLDER = "proton_drive_remote_folder"
SETTING_PROTON_BINARY = "proton_drive_binary"
SETTING_PROTON_BACKUP_CONFIG = "proton_drive_backup_config"
SETTING_PROTON_AFTER_CONVERT = "proton_drive_after_convert"

DEFAULT_REMOTE_FOLDER = "/my-files/HandForge"

_AUTH_HINT = (
    "Run `proton-drive auth login` (or use proton-drive-desktop) so the "
    "CLI has an active session. Install from "
    "https://proton.me/download/drive/cli/index.html"
)


@dataclass(frozen=True)
class ProtonDriveStatus:
    """Snapshot of CLI availability and auth for UI / list-cloud."""

    binary: Optional[str]
    available: bool
    authenticated: bool
    remote_folder: str
    backup_enabled: bool
    message: str
    desktop_running: bool = False


def find_proton_drive(binary: Optional[str] = None) -> Optional[str]:
    """Return path to proton-drive executable, or None if unavailable."""
    if binary:
        candidate = os.path.expanduser(str(binary).strip())
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        which = shutil.which(candidate)
        if which:
            return which
    return shutil.which("proton-drive")


def proton_drive_available(settings: Optional[Dict[str, Any]] = None) -> bool:
    """True when the proton-drive CLI can be invoked."""
    binary = None
    if settings:
        binary = settings.get(SETTING_PROTON_BINARY) or None
    return find_proton_drive(binary) is not None


def normalize_remote_folder(path: Optional[str]) -> str:
    """Normalize a Proton Drive remote path (always under /my-files when relative)."""
    raw = (path or "").strip() or DEFAULT_REMOTE_FOLDER
    raw = raw.replace("\\", "/")
    if not raw.startswith("/"):
        raw = f"/my-files/{raw.lstrip('/')}"
    # Collapse duplicate slashes
    while "//" in raw:
        raw = raw.replace("//", "/")
    return raw.rstrip("/") or "/my-files"


def remote_folder_from_settings(settings: Optional[Dict[str, Any]] = None) -> str:
    """Remote folder from settings, or the HandForge default."""
    settings = settings or {}
    return normalize_remote_folder(settings.get(SETTING_PROTON_REMOTE_FOLDER))


def backup_enabled(settings: Optional[Dict[str, Any]] = None) -> bool:
    """True when opt-in Proton Drive backup is enabled in settings."""
    return bool((settings or {}).get(SETTING_PROTON_BACKUP_ENABLED, False))


def after_convert_enabled(settings: Optional[Dict[str, Any]] = None) -> bool:
    """True when backup should run automatically after a successful batch."""
    settings = settings or {}
    if not backup_enabled(settings):
        return False
    return bool(settings.get(SETTING_PROTON_AFTER_CONVERT, True))


def _run_proton(
    args: Sequence[str],
    *,
    binary: Optional[str] = None,
    timeout: Optional[float] = 120,
    check: bool = True,
) -> subprocess.CompletedProcess:
    exe = find_proton_drive(binary)
    if not exe:
        raise FileNotFoundError(
            "proton-drive is not installed or not on PATH. "
            + _AUTH_HINT
        )
    cmd = [exe, *args]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip() or f"exit {result.returncode}"
        raise RuntimeError(f"proton-drive {' '.join(args[:3])} failed: {err}")
    return result


def check_authenticated(
    settings: Optional[Dict[str, Any]] = None,
    *,
    binary: Optional[str] = None,
) -> bool:
    """Probe auth by listing ``/my-files`` (JSON). False if CLI missing or auth fails."""
    bin_override = binary
    if bin_override is None and settings:
        bin_override = settings.get(SETTING_PROTON_BINARY) or None
    if not find_proton_drive(bin_override):
        return False
    try:
        result = _run_proton(
            ["filesystem", "list", "/my-files", "-j"],
            binary=bin_override,
            timeout=45,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False
    if result.returncode != 0:
        return False
    out = (result.stdout or "").strip()
    if not out:
        return False
    # Auth errors usually print non-JSON help or "not authenticated"
    lower = out.lower()
    if "not authenticated" in lower or "auth login" in lower:
        return False
    try:
        json.loads(out)
        return True
    except json.JSONDecodeError:
        # Some CLI versions may emit multi-line JSON arrays; accept leading [
        return out.lstrip().startswith("[") or out.lstrip().startswith("{")


def detect_desktop_running() -> bool:
    """Best-effort: proton-drive-desktop process present (status only)."""
    desktop = shutil.which("proton-drive-desktop")
    if not desktop:
        return False
    try:
        result = subprocess.run(
            ["pgrep", "-f", "proton-drive-desktop"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0 and bool((result.stdout or "").strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def get_status(settings: Optional[Dict[str, Any]] = None) -> ProtonDriveStatus:
    """Build a status snapshot for Preferences / ``list-cloud``."""
    settings = settings or {}
    binary = find_proton_drive(settings.get(SETTING_PROTON_BINARY) or None)
    remote = remote_folder_from_settings(settings)
    enabled = backup_enabled(settings)
    desktop = detect_desktop_running()
    if not binary:
        return ProtonDriveStatus(
            binary=None,
            available=False,
            authenticated=False,
            remote_folder=remote,
            backup_enabled=enabled,
            message=(
                "proton-drive not found — install Proton Drive CLI and ensure "
                "it is on PATH (or set Preferences → Cloud → proton-drive binary)."
            ),
            desktop_running=desktop,
        )
    authed = check_authenticated(settings, binary=binary)
    if authed:
        msg = f"proton-drive available ({binary}); authenticated"
        if desktop:
            msg += "; proton-drive-desktop running"
        if enabled:
            msg += f"; backup ON → {remote}"
        else:
            msg += "; backup OFF (opt-in in Preferences → Cloud)"
        return ProtonDriveStatus(
            binary=binary,
            available=True,
            authenticated=True,
            remote_folder=remote,
            backup_enabled=enabled,
            message=msg,
            desktop_running=desktop,
        )
    return ProtonDriveStatus(
        binary=binary,
        available=True,
        authenticated=False,
        remote_folder=remote,
        backup_enabled=enabled,
        message=(
            f"proton-drive found ({binary}) but not authenticated. {_AUTH_HINT}"
        ),
        desktop_running=desktop,
    )


def format_proton_status(settings: Optional[Dict[str, Any]] = None) -> str:
    """Multi-line status block for ``list-cloud`` / CLI."""
    st = get_status(settings)
    lines = [
        f"proton-drive: {st.message}",
        f"proton-drive remote folder: {st.remote_folder}",
    ]
    if st.backup_enabled:
        after = after_convert_enabled(settings)
        lines.append(
            f"proton-drive after-convert: {'yes' if after else 'no (use backup-proton)'}"
        )
        if (settings or {}).get(SETTING_PROTON_BACKUP_CONFIG):
            lines.append("proton-drive also backs up ~/.handforge config when uploading")
    return "\n".join(lines)


def _folder_exists(remote_path: str, *, binary: Optional[str] = None) -> bool:
    result = _run_proton(
        ["filesystem", "list", remote_path, "-j"],
        binary=binary,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        return False
    out = (result.stdout or "").strip()
    return bool(out) and (
        out.lstrip().startswith("[") or out.lstrip().startswith("{")
    )


def ensure_remote_folder(
    remote_path: str,
    *,
    settings: Optional[Dict[str, Any]] = None,
) -> str:
    """Create ``remote_path`` under Proton Drive if missing (parent chain)."""
    binary = (settings or {}).get(SETTING_PROTON_BINARY) if settings else None
    path = normalize_remote_folder(remote_path)
    if _folder_exists(path, binary=binary):
        return path

    parts = [p for p in path.split("/") if p]
    # Always start from absolute root segments: my-files / …
    built = ""
    for part in parts:
        parent = built or "/"
        built = f"{built}/{part}" if built else f"/{part}"
        if _folder_exists(built, binary=binary):
            continue
        # create-folder parent name
        parent_path = parent if parent != "/" else "/"
        # Proton CLI wants parentPath + name; root listing uses /my-files as parent
        if parent_path == "/":
            # Creating top-level under account root is unusual; require /my-files
            raise RuntimeError(
                f"Cannot create {built!r}: refuse to create under account root. "
                f"Use a path under /my-files (default {DEFAULT_REMOTE_FOLDER})."
            )
        try:
            _run_proton(
                ["filesystem", "create-folder", parent_path, part],
                binary=binary,
                timeout=60,
                check=True,
            )
        except RuntimeError as exc:
            # Race / already exists
            if _folder_exists(built, binary=binary):
                continue
            raise RuntimeError(
                f"Could not create Proton Drive folder {built}: {exc}"
            ) from exc
    return path


def upload_paths(
    local_paths: Sequence[str],
    remote_folder: Optional[str] = None,
    *,
    settings: Optional[Dict[str, Any]] = None,
    file_conflict: str = "create-new-revision",
    folder_conflict: str = "merge",
    skip_thumbnails: bool = True,
    timeout: Optional[float] = None,
) -> str:
    """Upload local files/dirs to ``remote_folder``. Returns the remote parent path."""
    settings = settings or {}
    binary = settings.get(SETTING_PROTON_BINARY) or None
    if not find_proton_drive(binary):
        raise FileNotFoundError(
            "proton-drive is not installed or not on PATH. " + _AUTH_HINT
        )
    if not check_authenticated(settings, binary=binary):
        raise RuntimeError(
            "Proton Drive CLI is not authenticated. " + _AUTH_HINT
        )

    remote = normalize_remote_folder(
        remote_folder or remote_folder_from_settings(settings)
    )
    ensure_remote_folder(remote, settings=settings)

    paths: List[str] = []
    for raw in local_paths:
        if not raw:
            continue
        expanded = os.path.expanduser(os.path.expandvars(str(raw).strip()))
        if not os.path.exists(expanded):
            raise FileNotFoundError(f"Local path not found for Proton upload: {expanded}")
        paths.append(expanded)
    if not paths:
        raise ValueError("No local paths to upload to Proton Drive")

    args: List[str] = [
        "filesystem",
        "upload",
        "-f",
        file_conflict,
        "-d",
        folder_conflict,
    ]
    if skip_thumbnails:
        args.append("-t")
    args.extend(paths)
    args.append(remote)

    # Large media: generous timeout (None = no limit via subprocess default)
    _run_proton(
        args,
        binary=binary,
        timeout=timeout if timeout is not None else 3600,
        check=True,
    )
    return remote


def collect_successful_outputs(output_paths: Iterable[str]) -> List[str]:
    """Filter to existing files suitable for backup upload."""
    found: List[str] = []
    seen = set()
    for raw in output_paths:
        if not raw:
            continue
        path = os.path.expanduser(str(raw))
        try:
            key = str(Path(path).resolve())
        except OSError:
            key = path
        if key in seen:
            continue
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            seen.add(key)
            found.append(path)
    return found


def backup_outputs(
    output_paths: Sequence[str],
    *,
    settings: Optional[Dict[str, Any]] = None,
    remote_folder: Optional[str] = None,
    include_config: Optional[bool] = None,
) -> Dict[str, Any]:
    """Upload conversion outputs (and optionally config) to Proton Drive.

    Returns a small result dict: ``remote``, ``uploaded`` (count), ``paths``.
    """
    settings = settings or {}
    paths = collect_successful_outputs(output_paths)
    do_config = (
        include_config
        if include_config is not None
        else bool(settings.get(SETTING_PROTON_BACKUP_CONFIG, False))
    )
    if do_config:
        cfg = Path.home() / ".handforge"
        # Prefer settings.json only — avoid uploading analytics/queue secrets bulk
        settings_file = cfg / "settings.json"
        presets_file = cfg / "presets.json"
        for candidate in (settings_file, presets_file):
            if candidate.is_file():
                paths.append(str(candidate))

    if not paths:
        raise ValueError("No successful output files to back up to Proton Drive")

    remote = upload_paths(paths, remote_folder, settings=settings)
    return {"remote": remote, "uploaded": len(paths), "paths": paths}


def backup_directory(
    local_dir: str,
    *,
    settings: Optional[Dict[str, Any]] = None,
    remote_folder: Optional[str] = None,
) -> Dict[str, Any]:
    """Upload an entire local directory (folder merge) to Proton Drive."""
    expanded = os.path.expanduser(os.path.expandvars(str(local_dir).strip()))
    if not os.path.isdir(expanded):
        raise FileNotFoundError(f"Not a directory: {expanded}")
    remote = upload_paths([expanded], remote_folder, settings=settings)
    return {"remote": remote, "uploaded": 1, "paths": [expanded]}
