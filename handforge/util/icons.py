"""Application and system-tray icons for the HandForge GUI.

Loads multi-size PNGs shipped under ``handforge/resources/``. If those files
are missing (broken install), paints a minimal forge/waveform icon so
``QSystemTrayIcon.show()`` never runs without a ``QIcon`` (avoids Qt's
``QSystemTrayIcon::setVisible: No Icon set`` warning).
"""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap


_ICON_FILES = (
    "app_icon_16.png",
    "app_icon_32.png",
    "app_icon_64.png",
    "app_icon_128.png",
    "app_icon.png",
)


def _resources_dir() -> Optional[Path]:
    try:
        root = resources.files("handforge").joinpath("resources")
    except (ModuleNotFoundError, TypeError, AttributeError):
        return None
    # importlib.resources may return a Traversable; resolve to Path when on disk
    try:
        with resources.as_file(root) as path:
            return Path(path)
    except (FileNotFoundError, OSError, TypeError):
        return None


def _paint_fallback_icon(size: int = 64) -> QIcon:
    """Draw a simple amber-on-slate icon when packaged PNGs are unavailable."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    bg = QColor(28, 32, 40)
    ring = QColor(232, 148, 48)
    wave = QColor(255, 214, 140)
    m = max(1, size // 16)
    painter.setBrush(bg)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(m, m, size - 2 * m, size - 2 * m, size // 5, size // 5)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    pen = painter.pen()
    pen.setColor(ring)
    pen.setWidth(max(2, size // 16))
    painter.setPen(pen)
    pad = size // 5
    painter.drawEllipse(pad, pad, size - 2 * pad, size - 2 * pad)
    # Five waveform bars
    cx, cy = size // 2, size // 2
    bw = max(1, size // 14)
    gap = max(1, size // 20)
    heights = (0.35, 0.7, 1.0, 0.55, 0.4)
    total_w = len(heights) * bw + (len(heights) - 1) * gap
    x0 = cx - total_w // 2
    painter.setPen(Qt.PenStyle.NoPen)
    for i, h in enumerate(heights):
        bh = int(size * 0.28 * h)
        x = x0 + i * (bw + gap)
        painter.setBrush(wave if i == 2 else ring)
        painter.drawRoundedRect(x, cy - bh // 2, bw, bh, max(1, bw // 3), max(1, bw // 3))
    painter.end()
    icon = QIcon()
    icon.addPixmap(pix)
    return icon


def _load_png_paths() -> List[Path]:
    base = _resources_dir()
    if base is None or not base.is_dir():
        return []
    found: List[Path] = []
    for name in _ICON_FILES:
        path = base / name
        if path.is_file() and path.stat().st_size > 0:
            found.append(path)
    return found


@lru_cache(maxsize=1)
def app_icon() -> QIcon:
    """Return the HandForge application / tray ``QIcon`` (never null)."""
    paths = _load_png_paths()
    if not paths:
        return _paint_fallback_icon(64)

    icon = QIcon()
    for path in paths:
        pix = QPixmap(str(path))
        if pix.isNull():
            continue
        icon.addPixmap(pix)
    if icon.isNull():
        return _paint_fallback_icon(64)
    return icon


def ensure_tray_icon(tray) -> bool:
    """Assign ``app_icon()`` to a ``QSystemTrayIcon`` before ``show()``.

    Returns True if the tray now has a non-null icon.
    """
    icon = app_icon()
    if icon.isNull():
        return False
    tray.setIcon(icon)
    return not tray.icon().isNull()


def clear_icon_cache() -> None:
    """Drop the cached icon (tests / icon regeneration)."""
    app_icon.cache_clear()
