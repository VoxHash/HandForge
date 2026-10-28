"""MainWindow free-resize: min floor, unconstrained max, resizeEvent safe."""

from __future__ import annotations

import os

# Must be set before the session QApplication is created.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtCore import QEventLoop, QSize, QTimer
from PyQt6.QtWidgets import QApplication

from handforge.ui.main_window import MainWindow


# Qt's QWIDGETSIZE_MAX — unconstrained maximum size.
_QWIDGETSIZE_MAX = 16777215


def _settle(qapp: QApplication, ms: int = 30) -> None:
    """Flush deferred resize/layout events."""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()
    qapp.processEvents()


@pytest.fixture
def main_window(qapp, isolated_config_dir, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setattr(
        "handforge.ui.main_window.QSystemTrayIcon.isSystemTrayAvailable",
        staticmethod(lambda: False),
    )
    win = MainWindow()
    yield win
    if win.tray_icon:
        win.tray_icon.hide()
    win.close()


def test_minimum_size_is_compact_floor(main_window):
    mn = main_window.minimumSize()
    assert mn.width() <= 720
    assert mn.height() <= 480
    assert mn.width() >= 320
    assert mn.height() >= 240


def test_maximum_size_unconstrained(main_window):
    assert main_window.maximumWidth() >= _QWIDGETSIZE_MAX
    assert main_window.maximumHeight() >= _QWIDGETSIZE_MAX
    assert main_window.maximumSize() == QSize(_QWIDGETSIZE_MAX, _QWIDGETSIZE_MAX)


def test_no_fixed_size_lock(main_window):
    """Window must not be locked via setFixedSize (min == max)."""
    assert main_window.minimumWidth() < main_window.maximumWidth()
    assert main_window.minimumHeight() < main_window.maximumHeight()


def test_resize_smaller_and_larger(main_window, qapp):
    main_window.show()
    _settle(qapp)

    for w, h in ((720, 480), (1600, 1000), (720, 900), (1400, 480)):
        main_window.resize(w, h)
        _settle(qapp)
        assert main_window.size() == QSize(w, h), (
            f"expected {w}x{h}, got {main_window.width()}x{main_window.height()}"
        )


def test_resize_event_does_not_crash(main_window, qapp):
    main_window.show()
    _settle(qapp)
    for w, h in ((800, 500), (1100, 700), (720, 480), (1800, 1100)):
        main_window.resize(w, h)
        _settle(qapp)
        assert main_window.width() == w
        assert main_window.height() == h
