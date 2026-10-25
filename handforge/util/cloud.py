"""Cloud storage helpers for HandForge.

Two real backends (no fake API keys):

1. **Local sync mounts / cloud roots** — Dropbox, Google Drive, OneDrive,
   Nextcloud (and user-configured folders). FFmpeg reads/writes these paths
   like any other directory; the sync client uploads in the background.

2. **Optional rclone** — when ``rclone`` is on PATH (or ``rclone_binary`` is
   set), HandForge can ``listremotes``, ``copy`` / ``copyto`` to and from
   ``remote:path`` locations. Missing rclone is a graceful no-op for list /
   status; convert fails clearly if a remote path is requested without rclone.

Remote path syntax matches rclone: ``remote:path/to/dir``. A ``rclone:``
prefix is also accepted (``rclone:remote:path``) and stripped.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# Settings keys (merged in core.settings defaults).
SETTING_CLOUD_ROOTS = "cloud_roots"
SETTING_CLOUD_INPUT_ROOT = "cloud_input_root"
SETTING_RCLONE_REMOTE = "rclone_remote"
SETTING_RCLONE_BINARY = "rclone_binary"
SETTING_RCLONE_ENABLED = "rclone_enabled"

_RCLONE_PREFIX = "rclone:"
_REMOTE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


@dataclass(frozen=True)
class CloudRoot:
    """A discovered or configured local folder backed by a sync client."""

    label: str
    path: str
    kind: str  # dropbox | gdrive | onedrive | nextcloud | custom | detected


@dataclass
class ResolvedOutput:
    """Local encode destination plus optional rclone upload target."""

    local_dir: str
    rclone_dest: Optional[str] = None  # e.g. "gdrive:HandForge/Out"
    staging: bool = False


@dataclass
class ResolvedInputs:
    """Local media paths ready for FFmpeg (possibly staged from rclone)."""

    paths: List[str]
    staging_dirs: List[str]


def find_rclone(binary: Optional[str] = None) -> Optional[str]:
    """Return path to rclone executable, or None if unavailable."""
    if binary:
        candidate = os.path.expanduser(str(binary).strip())
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        which = shutil.which(candidate)
        if which:
            return which
    return shutil.which("rclone")


def rclone_available(settings: Optional[Dict[str, Any]] = None) -> bool:
    """True when rclone can be invoked (respects settings binary override)."""
    binary = None
    if settings:
        binary = settings.get(SETTING_RCLONE_BINARY) or None
    return find_rclone(binary) is not None


def _run_rclone(
    args: Sequence[str],
    *,
    binary: Optional[str] = None,
    timeout: Optional[float] = 120,
    check: bool = True,
) -> subprocess.CompletedProcess:
    rclone = find_rclone(binary)
    if not rclone:
        raise FileNotFoundError(
            "rclone is not installed or not on PATH. "
            "Install rclone (https://rclone.org/install/) or use a local "
            "cloud sync folder under Preferences → Cloud."
        )
    cmd = [rclone, *args]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip() or f"exit {result.returncode}"
        raise RuntimeError(f"rclone {' '.join(args[:2])} failed: {err}")
    return result


def parse_listremotes_output(stdout: str) -> List[str]:
    """Parse ``rclone listremotes`` text into remote names (with trailing colon)."""
    remotes: List[str] = []
    for line in (stdout or "").splitlines():
        name = line.strip()
        if not name or name.startswith("#"):
            continue
        if not name.endswith(":"):
            name = name + ":"
        # Drop junk lines that are not remote names
        bare = name[:-1]
        if not _REMOTE_NAME_RE.match(bare):
            continue
        remotes.append(name)
    return remotes


def list_rclone_remotes(
    settings: Optional[Dict[str, Any]] = None,
    *,
    binary: Optional[str] = None,
) -> List[str]:
    """List configured rclone remotes. Empty list if rclone is missing."""
    bin_override = binary
    if bin_override is None and settings:
        bin_override = settings.get(SETTING_RCLONE_BINARY) or None
    if not find_rclone(bin_override):
        return []
    try:
        result = _run_rclone(
            ["listremotes"],
            binary=bin_override,
            timeout=30,
            check=True,
        )
    except (FileNotFoundError, RuntimeError, subprocess.TimeoutExpired, OSError):
        return []
    return parse_listremotes_output(result.stdout or "")


def is_windows_drive_path(path: str) -> bool:
    """True for Windows drive roots / paths like ``C:\\foo`` or ``D:/bar``."""
    if len(path) < 2 or path[1] != ":":
        return False
    if not path[0].isalpha():
        return False
    if len(path) == 2:
        return True
    return path[2] in "/\\"


def strip_rclone_prefix(path: str) -> str:
    """Remove optional ``rclone:`` wrapper; return ``remote:path`` or local path."""
    raw = str(path).strip()
    if raw.lower().startswith(_RCLONE_PREFIX):
        return raw[len(_RCLONE_PREFIX) :]
    return raw


def is_rclone_path(path: str) -> bool:
    """Detect rclone-style ``remote:path`` (not a local Windows drive)."""
    raw = strip_rclone_prefix(path)
    if not raw or is_windows_drive_path(raw):
        return False
    if raw.startswith("/") or raw.startswith("\\"):
        return False
    if ":" not in raw:
        return False
    remote, rest = raw.split(":", 1)
    if not remote or "/" in remote or "\\" in remote:
        return False
    # Exclude URL schemes (http://..., file://...)
    if rest.startswith("//"):
        return False
    if remote.lower() in {"http", "https", "ftp", "ftps", "file"}:
        return False
    return bool(_REMOTE_NAME_RE.match(remote))


def parse_rclone_path(path: str) -> Tuple[str, str]:
    """Split ``remote:path`` into ``(remote_name_with_colon, remote_path)``."""
    raw = strip_rclone_prefix(path)
    if not is_rclone_path(raw):
        raise ValueError(f"Not an rclone remote path: {path!r}")
    remote, rest = raw.split(":", 1)
    return f"{remote}:", rest.lstrip("/")


def join_rclone_path(remote: str, remote_path: str = "") -> str:
    """Build ``remote:path`` from a remote name and optional subpath."""
    name = str(remote).strip()
    if not name.endswith(":"):
        name = name + ":"
    sub = str(remote_path or "").lstrip("/")
    return f"{name}{sub}" if sub else name


def expand_local_path(path: str) -> str:
    """Expand ``~`` and environment variables for a filesystem path."""
    return os.path.expandvars(os.path.expanduser(str(path).strip()))


def _candidate_sync_dirs() -> List[Tuple[str, str, str]]:
    """Return (label, kind, path) candidates for common sync clients."""
    home = Path.home()
    candidates: List[Tuple[str, str, str]] = [
        ("Dropbox", "dropbox", str(home / "Dropbox")),
        ("Google Drive", "gdrive", str(home / "Google Drive")),
        ("GoogleDrive", "gdrive", str(home / "GoogleDrive")),
        ("OneDrive", "onedrive", str(home / "OneDrive")),
        ("Nextcloud", "nextcloud", str(home / "Nextcloud")),
        ("pCloud Drive", "custom", str(home / "pCloudDrive")),
        ("Mega", "custom", str(home / "MEGA")),
    ]
    # macOS CloudStorage layout
    cloud_storage = home / "Library" / "CloudStorage"
    if cloud_storage.is_dir():
        try:
            for child in sorted(cloud_storage.iterdir()):
                name = child.name
                if not child.is_dir():
                    continue
                lower = name.lower()
                if "google" in lower or "drive" in lower:
                    candidates.append((f"Google Drive ({name})", "gdrive", str(child)))
                elif "onedrive" in lower:
                    candidates.append((f"OneDrive ({name})", "onedrive", str(child)))
                elif "dropbox" in lower:
                    candidates.append((f"Dropbox ({name})", "dropbox", str(child)))
                else:
                    candidates.append((name, "detected", str(child)))
        except OSError:
            pass
    # Linux: common XDG locations for Nextcloud / ownCloud clients
    xdg = os.environ.get("XDG_DATA_HOME", str(home / ".local" / "share"))
    for name, kind in (
        ("Nextcloud", "nextcloud"),
        ("ownCloud", "nextcloud"),
    ):
        candidates.append((name, kind, str(Path(xdg) / name)))
    if os.name == "nt":
        userprofile = os.environ.get("USERPROFILE") or str(home)
        for label, kind, leaf in (
            ("Dropbox", "dropbox", "Dropbox"),
            ("OneDrive", "onedrive", "OneDrive"),
            ("Google Drive", "gdrive", "Google Drive"),
        ):
            candidates.append((label, kind, os.path.join(userprofile, leaf)))
    return candidates


def detect_sync_mounts() -> List[CloudRoot]:
    """Discover existing local folders typically used by cloud sync clients."""
    found: List[CloudRoot] = []
    seen = set()
    for label, kind, path in _candidate_sync_dirs():
        expanded = expand_local_path(path)
        try:
            resolved = str(Path(expanded).resolve())
        except OSError:
            resolved = expanded
        if resolved in seen:
            continue
        if os.path.isdir(expanded):
            seen.add(resolved)
            found.append(CloudRoot(label=label, path=expanded, kind=kind))
    return found


def configured_cloud_roots(settings: Optional[Dict[str, Any]] = None) -> List[str]:
    """User-configured cloud root paths from settings (expanded, existing only)."""
    roots: List[str] = []
    raw = (settings or {}).get(SETTING_CLOUD_ROOTS) or []
    if not isinstance(raw, (list, tuple)):
        return roots
    for item in raw:
        if not item:
            continue
        path = expand_local_path(str(item))
        if os.path.isdir(path):
            roots.append(path)
    return roots


def all_cloud_roots(settings: Optional[Dict[str, Any]] = None) -> List[CloudRoot]:
    """Merge detected mounts with user-configured roots (unique by resolved path)."""
    by_path: Dict[str, CloudRoot] = {}
    for root in detect_sync_mounts():
        try:
            key = str(Path(root.path).resolve())
        except OSError:
            key = root.path
        by_path[key] = root
    for path in configured_cloud_roots(settings):
        try:
            key = str(Path(path).resolve())
        except OSError:
            key = path
        if key not in by_path:
            by_path[key] = CloudRoot(label=os.path.basename(path) or path, path=path, kind="custom")
    return list(by_path.values())


def default_browse_dir(settings: Optional[Dict[str, Any]] = None) -> str:
    """Preferred starting directory for file/folder pickers (cloud input or first root)."""
    settings = settings or {}
    preferred = settings.get(SETTING_CLOUD_INPUT_ROOT)
    if preferred:
        path = expand_local_path(str(preferred))
        if os.path.isdir(path):
            return path
    roots = all_cloud_roots(settings)
    if roots:
        return roots[0].path
    return str(Path.home())


def resolve_output_dir_setting(
    settings: Optional[Dict[str, Any]] = None,
    *,
    fallback: Optional[str] = None,
) -> str:
    """Expand settings ``output_dir`` or return fallback / ~/HandForge_Output."""
    settings = settings or {}
    out = settings.get("output_dir")
    if out:
        expanded = expand_local_path(str(out))
        if is_rclone_path(expanded):
            return expanded
        return expanded
    if fallback:
        return expand_local_path(fallback)
    if os.name == "nt":
        return os.path.join(os.environ.get("USERPROFILE", ""), "HandForge_Output")
    return os.path.expanduser("~/HandForge_Output")


def rclone_copy(
    source: str,
    dest: str,
    *,
    settings: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
) -> None:
    """Copy source → dest via rclone (file or directory)."""
    binary = (settings or {}).get(SETTING_RCLONE_BINARY) if settings else None
    # Prefer copyto for single-file destinations that already include a filename
    src_is_file = (not is_rclone_path(source)) and os.path.isfile(expand_local_path(source))
    if src_is_file and (is_rclone_path(dest) or dest.rstrip("/\\").endswith(os.path.basename(source))):
        _run_rclone(
            ["copyto", expand_local_path(source) if not is_rclone_path(source) else source, dest],
            binary=binary,
            timeout=timeout or 600,
            check=True,
        )
        return
    src = expand_local_path(source) if not is_rclone_path(source) else source
    dst = expand_local_path(dest) if not is_rclone_path(dest) else dest
    _run_rclone(
        ["copy", src, dst],
        binary=binary,
        timeout=timeout or 600,
        check=True,
    )


def stage_rclone_path(
    remote_path: str,
    staging_parent: str,
    *,
    settings: Optional[Dict[str, Any]] = None,
) -> str:
    """Download ``remote:path`` into a local staging directory; return local path."""
    remote, sub = parse_rclone_path(remote_path)
    full = join_rclone_path(remote, sub)
    os.makedirs(staging_parent, exist_ok=True)
    # Use a unique subdir so parallel jobs do not clash
    local_dir = tempfile.mkdtemp(prefix="hf_rclone_in_", dir=staging_parent)
    rclone_copy(full, local_dir, settings=settings)
    # If a single file was copied, prefer returning that file path
    entries = list(Path(local_dir).iterdir())
    if len(entries) == 1 and entries[0].is_file():
        return str(entries[0])
    return local_dir


def prepare_inputs(
    paths: Sequence[str],
    *,
    settings: Optional[Dict[str, Any]] = None,
    staging_parent: Optional[str] = None,
) -> ResolvedInputs:
    """Resolve CLI/GUI input paths; stage rclone remotes to local dirs when needed."""
    settings = settings or {}
    staging_dirs: List[str] = []
    resolved: List[str] = []
    parent = staging_parent or tempfile.mkdtemp(prefix="hf_cloud_stage_")
    if staging_parent is None:
        staging_dirs.append(parent)

    rclone_on = bool(settings.get(SETTING_RCLONE_ENABLED, True))
    default_remote = (settings.get(SETTING_RCLONE_REMOTE) or "").strip()

    for raw in paths:
        text = str(raw).strip()
        if not text:
            continue
        # Bare remote name + path via default remote: "HandForge/In/file.wav"
        # when --cloud-remote is set and path has no colon — stay local/expand.
        if is_rclone_path(text):
            if not rclone_on:
                raise RuntimeError(
                    f"rclone path {text!r} requested but rclone_enabled is false"
                )
            if not rclone_available(settings):
                raise FileNotFoundError(
                    f"Cannot fetch {text!r}: rclone is not installed. "
                    "Install rclone or use a synced local cloud folder."
                )
            local = stage_rclone_path(text, parent, settings=settings)
            # Track the unique staging subdir created inside parent
            staging_dirs.append(
                local if os.path.isdir(local) else os.path.dirname(local)
            )
            resolved.append(local)
            continue

        expanded = expand_local_path(text)
        if not os.path.exists(expanded) and default_remote and ":" not in text:
            # Optional: treat as path under default rclone remote
            if rclone_on and rclone_available(settings):
                remote_full = join_rclone_path(default_remote, text)
                local = stage_rclone_path(remote_full, parent, settings=settings)
                staging_dirs.append(
                    local if os.path.isdir(local) else os.path.dirname(local)
                )
                resolved.append(local)
                continue
        resolved.append(expanded)

    return ResolvedInputs(paths=resolved, staging_dirs=list(dict.fromkeys(staging_dirs)))


def prepare_output(
    output_spec: Optional[str],
    *,
    settings: Optional[Dict[str, Any]] = None,
    staging_parent: Optional[str] = None,
) -> ResolvedOutput:
    """Resolve output directory; stage locally when target is an rclone remote."""
    settings = settings or {}
    spec = (output_spec or "").strip() or resolve_output_dir_setting(settings)
    if is_rclone_path(spec):
        if not settings.get(SETTING_RCLONE_ENABLED, True):
            raise RuntimeError(
                f"rclone output {spec!r} requested but rclone_enabled is false"
            )
        if not rclone_available(settings):
            raise FileNotFoundError(
                f"Cannot write to {spec!r}: rclone is not installed. "
                "Install rclone or set output_dir to a local sync folder."
            )
        parent = staging_parent or tempfile.mkdtemp(prefix="hf_cloud_out_")
        local = tempfile.mkdtemp(prefix="hf_rclone_out_", dir=parent)
        return ResolvedOutput(local_dir=local, rclone_dest=strip_rclone_prefix(spec), staging=True)

    local = expand_local_path(spec)
    os.makedirs(local, mode=0o755, exist_ok=True)
    return ResolvedOutput(local_dir=local, rclone_dest=None, staging=False)


def push_output(resolved: ResolvedOutput, *, settings: Optional[Dict[str, Any]] = None) -> None:
    """Upload staged local output directory to rclone dest when applicable."""
    if not resolved.rclone_dest:
        return
    rclone_copy(resolved.local_dir, resolved.rclone_dest, settings=settings)


def cleanup_staging(paths: Iterable[str]) -> None:
    """Best-effort removal of temporary staging directories."""
    for path in paths:
        if not path:
            continue
        try:
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
        except OSError:
            pass


def format_cloud_status(settings: Optional[Dict[str, Any]] = None) -> str:
    """Human-readable cloud / rclone status for CLI ``list-cloud``."""
    settings = settings or {}
    lines: List[str] = []
    binary = find_rclone(settings.get(SETTING_RCLONE_BINARY) or None)
    if binary:
        lines.append(f"rclone: available ({binary})")
        remotes = list_rclone_remotes(settings)
        if remotes:
            lines.append("rclone remotes:")
            for name in remotes:
                lines.append(f"  - {name}")
        else:
            lines.append("rclone remotes: (none configured — run `rclone config`)")
        default = (settings.get(SETTING_RCLONE_REMOTE) or "").strip()
        if default:
            lines.append(f"default rclone remote: {default}")
    else:
        lines.append(
            "rclone: not found — install from https://rclone.org/install/ "
            "or use local sync folders (Dropbox / Google Drive / OneDrive / Nextcloud)."
        )
        lines.append(
            "Local-only workflows are unchanged; cloud roots below still work without rclone."
        )

    roots = all_cloud_roots(settings)
    if roots:
        lines.append("cloud roots (local sync / configured):")
        for root in roots:
            lines.append(f"  - [{root.kind}] {root.label}: {root.path}")
    else:
        lines.append(
            "cloud roots: none detected — add folders in Preferences → Cloud "
            "or set cloud_roots in settings.json"
        )

    out = settings.get("output_dir")
    if out:
        lines.append(f"settings output_dir: {out}")
    input_root = settings.get(SETTING_CLOUD_INPUT_ROOT)
    if input_root:
        lines.append(f"settings cloud_input_root: {input_root}")
    return "\n".join(lines)
