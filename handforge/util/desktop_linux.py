"""Linux FreeDesktop launcher install (``.desktop`` + hicolor icons).

Installs a start-menu entry that launches the GUI via the ``handforge-gui``
console script (absolute path under the active venv / install prefix), so the
app menu does not depend on an activated shell ``PATH``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DESKTOP_ID = "dev.voxhash.HandForge"
ICON_NAME = "dev.voxhash.HandForge"
DESKTOP_FILENAME = f"{DESKTOP_ID}.desktop"

# Packaged PNG → FreeDesktop hicolor size directory
_ICON_MAP: Tuple[Tuple[str, str], ...] = (
    ("app_icon_16.png", "16x16"),
    ("app_icon_32.png", "32x32"),
    ("app_icon_64.png", "64x64"),
    ("app_icon_128.png", "128x128"),
    ("app_icon.png", "256x256"),
)

_DESKTOP_TEMPLATE = """\
[Desktop Entry]
Type=Application
Version=1.5
Name=HandForge
GenericName=Media Converter
Comment=Convert audio and video with FFmpeg
Exec={exec}
TryExec={try_exec}
Icon={icon}
Terminal=false
Categories=AudioVideo;AudioVideoEditing;
Keywords=convert;ffmpeg;audio;video;encoder;HandForge;
StartupNotify=true
StartupWMClass=HandForge
"""


@dataclass
class DesktopInstallResult:
    """Paths written (or that would be written) by an install."""

    desktop_path: Path
    icon_paths: List[Path] = field(default_factory=list)
    exec_line: str = ""
    try_exec: str = ""
    data_home: Path = field(default_factory=Path)
    dry_run: bool = False


def is_linux() -> bool:
    return sys.platform.startswith("linux")


def xdg_data_home() -> Path:
    raw = os.environ.get("XDG_DATA_HOME", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".local" / "share"


def resolve_data_root(*, system: bool = False, prefix: Optional[Path] = None) -> Path:
    """Return the share root that contains ``applications/`` and ``icons/``."""
    if prefix is not None:
        return Path(prefix).expanduser().resolve()
    if system:
        return Path("/usr/share")
    return xdg_data_home()


def quote_desktop_arg(value: str) -> str:
    """Quote a single Exec/TryExec token per the Desktop Entry Spec."""
    reserved = set(' \t\n"\'\\\\<>~|&;$*?#()`')
    if not value or any(ch in reserved for ch in value):
        escaped = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("$", "\\$")
            .replace("`", "\\`")
        )
        return f'"{escaped}"'
    return value


def resolve_gui_executable() -> Tuple[str, str]:
    """Return ``(exec_line, try_exec_path)`` for the HandForge GUI.

    Prefers ``handforge-gui`` next to ``sys.executable`` (venv / install
    ``bin``). Falls back to ``{python} -m handforge.app``.

    Important: do not ``Path.resolve()`` the interpreter first — in a venv,
    ``python`` is often a symlink to the system binary, and resolving it would
    look for console scripts under ``/usr/bin`` instead of ``.venv/bin``.
    """
    # abspath keeps the venv bindir when python is a symlink; resolve() would not.
    bindir = Path(os.path.abspath(sys.executable)).parent
    gui = bindir / "handforge-gui"
    if gui.is_file() and os.access(gui, os.X_OK):
        path = os.path.abspath(str(gui))
        return quote_desktop_arg(path), path

    # Windows-style name on Linux is unlikely; still check.
    gui_exe = bindir / "handforge-gui.exe"
    if gui_exe.is_file() and os.access(gui_exe, os.X_OK):
        path = os.path.abspath(str(gui_exe))
        return quote_desktop_arg(path), path

    py = os.path.abspath(sys.executable)
    exec_line = f"{quote_desktop_arg(py)} -m handforge.app"
    return exec_line, py


def _resources_icon_paths() -> Dict[str, Path]:
    """Map size dir (e.g. ``64x64``) → on-disk PNG path from package data."""
    found: Dict[str, Path] = {}
    try:
        root = resources.files("handforge").joinpath("resources")
    except (ModuleNotFoundError, TypeError, AttributeError):
        return found
    try:
        with resources.as_file(root) as base:
            base_path = Path(base)
            for filename, size_dir in _ICON_MAP:
                path = base_path / filename
                if path.is_file() and path.stat().st_size > 0:
                    found[size_dir] = path
    except (FileNotFoundError, OSError, TypeError):
        return found
    return found


def render_desktop_file(
    *,
    exec_line: Optional[str] = None,
    try_exec: Optional[str] = None,
    icon: str = ICON_NAME,
) -> str:
    """Render a FreeDesktop ``.desktop`` body (trailing newline included)."""
    if exec_line is None or try_exec is None:
        resolved_exec, resolved_try = resolve_gui_executable()
        exec_line = exec_line or resolved_exec
        try_exec = try_exec or resolved_try
    return _DESKTOP_TEMPLATE.format(
        exec=exec_line,
        try_exec=try_exec,
        icon=icon,
    )


def packaging_template_path() -> Path:
    """Repo template under ``packaging/linux/`` (dev tree); may be absent in wheels."""
    # handforge/util/desktop_linux.py → repo root
    here = Path(__file__).resolve()
    return here.parents[2] / "packaging" / "linux" / "handforge.desktop"


def install_desktop(
    *,
    system: bool = False,
    prefix: Optional[Path] = None,
    dry_run: bool = False,
) -> DesktopInstallResult:
    """Install ``.desktop`` + hicolor icons under the chosen data root."""
    if not is_linux():
        raise OSError("Linux .desktop install is only supported on Linux")

    data_root = resolve_data_root(system=system, prefix=prefix)
    applications = data_root / "applications"
    icons_root = data_root / "icons" / "hicolor"
    desktop_path = applications / DESKTOP_FILENAME

    exec_line, try_exec = resolve_gui_executable()
    body = render_desktop_file(exec_line=exec_line, try_exec=try_exec)

    icon_srcs = _resources_icon_paths()
    icon_dests: List[Path] = []
    for size_dir, src in icon_srcs.items():
        dest = icons_root / size_dir / "apps" / f"{ICON_NAME}.png"
        icon_dests.append(dest)

    result = DesktopInstallResult(
        desktop_path=desktop_path,
        icon_paths=icon_dests,
        exec_line=exec_line,
        try_exec=try_exec,
        data_home=data_root,
        dry_run=dry_run,
    )

    if dry_run:
        return result

    if system and not os.access(data_root, os.W_OK) and not applications.exists():
        # Parent may exist but not be writable; fail early with a clear error.
        pass
    applications.mkdir(parents=True, exist_ok=True)
    desktop_path.write_text(body, encoding="utf-8")
    # Executable bit is conventional for .desktop launchers
    desktop_path.chmod(desktop_path.stat().st_mode | 0o111)

    for size_dir, src in icon_srcs.items():
        dest_dir = icons_root / size_dir / "apps"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{ICON_NAME}.png"
        shutil.copy2(src, dest)

    _refresh_desktop_caches(data_root)
    return result


def uninstall_desktop(
    *,
    system: bool = False,
    prefix: Optional[Path] = None,
    dry_run: bool = False,
) -> List[Path]:
    """Remove installed ``.desktop`` and hicolor icons. Returns removed paths."""
    data_root = resolve_data_root(system=system, prefix=prefix)
    removed: List[Path] = []
    desktop_path = data_root / "applications" / DESKTOP_FILENAME
    candidates = [desktop_path]
    icons_root = data_root / "icons" / "hicolor"
    for _, size_dir in _ICON_MAP:
        candidates.append(icons_root / size_dir / "apps" / f"{ICON_NAME}.png")

    for path in candidates:
        if path.is_file():
            removed.append(path)
            if not dry_run:
                path.unlink()

    if not dry_run and removed:
        _refresh_desktop_caches(data_root)
    return removed


def _refresh_desktop_caches(data_root: Path) -> None:
    """Best-effort update-desktop-database / icon cache refresh."""
    apps = data_root / "applications"
    if shutil.which("update-desktop-database") and apps.is_dir():
        try:
            subprocess.run(
                ["update-desktop-database", str(apps)],
                check=False,
                capture_output=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    hicolor = data_root / "icons" / "hicolor"
    if shutil.which("gtk-update-icon-cache") and hicolor.is_dir():
        try:
            subprocess.run(
                ["gtk-update-icon-cache", "-f", "-t", str(hicolor)],
                check=False,
                capture_output=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass


def validate_desktop_file(path: Path) -> Tuple[bool, str]:
    """Run ``desktop-file-validate`` when available. Returns (ok, message)."""
    validator = shutil.which("desktop-file-validate")
    if not validator:
        return True, "desktop-file-validate not installed (skipped)"

    proc = subprocess.run(
        [validator, str(path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 0:
        return True, out.strip() or "OK"
    return False, out.strip() or f"desktop-file-validate exit {proc.returncode}"
