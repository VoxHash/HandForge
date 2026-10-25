"""GUI tray / application icon — must never show a tray without a QIcon."""

from __future__ import annotations

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QSystemTrayIcon

from handforge.util import icons as icons_mod
from handforge.util.icons import app_icon, clear_icon_cache, ensure_tray_icon
from handforge.ui.main_window import MainWindow


@pytest.fixture
def qpa_offscreen(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")


def test_app_icon_is_non_null(qapp, qpa_offscreen):
    clear_icon_cache()
    icon = app_icon()
    assert isinstance(icon, QIcon)
    assert not icon.isNull()
    # Packaged multi-size PNGs should yield at least one available size
    sizes = icon.availableSizes()
    assert len(sizes) >= 1


def test_app_icon_fallback_when_resources_missing(qapp, qpa_offscreen, monkeypatch):
    clear_icon_cache()
    monkeypatch.setattr(icons_mod, "_load_png_paths", lambda: [])
    icon = app_icon()
    assert not icon.isNull()
    clear_icon_cache()


def test_ensure_tray_icon_sets_non_null(qapp, qpa_offscreen):
    clear_icon_cache()
    tray = QSystemTrayIcon()
    assert tray.icon().isNull()
    assert ensure_tray_icon(tray) is True
    assert not tray.icon().isNull()


def test_main_window_tray_has_icon_when_available(
    qapp, isolated_config_dir, monkeypatch, qpa_offscreen
):
    clear_icon_cache()
    monkeypatch.setattr(
        "handforge.ui.main_window.QSystemTrayIcon.isSystemTrayAvailable",
        staticmethod(lambda: True),
    )
    win = MainWindow()
    try:
        assert win.windowIcon() is not None
        assert not win.windowIcon().isNull()
        assert win.tray_icon is not None
        assert not win.tray_icon.icon().isNull()
    finally:
        if win.tray_icon:
            win.tray_icon.hide()
        win.close()
