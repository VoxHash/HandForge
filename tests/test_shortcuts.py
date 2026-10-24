"""Tests for GUI keyboard shortcuts on MainWindow."""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PyQt6")

from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QMessageBox

from handforge.core.models import Job
from handforge.ui.main_window import KEYBOARD_SHORTCUTS, MainWindow


# Expected action attribute → key sequence string from KEYBOARD_SHORTCUTS
_ACTION_SHORTCUTS = {
    "act_add_files": "Ctrl+O",
    "act_add_folder": "Ctrl+Shift+O",
    "act_start": "Ctrl+Return",
    "act_stop": "Ctrl+.",
    "act_remove_selected": "Delete",
    "act_clear_queue": "Ctrl+Shift+K",
    "act_clear_conversions": "Ctrl+Shift+Delete",
    "act_preferences": "Ctrl+,",
    "act_manage_presets": "Ctrl+P",
    "act_preset_library": "Ctrl+Shift+L",
    "act_focus_queue": "Ctrl+1",
    "act_focus_active": "Ctrl+2",
    "act_quit": "Ctrl+Q",
    "act_shortcuts_help": "F1",
}


@pytest.fixture
def main_window(qapp, isolated_config_dir, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    # Avoid system tray / native dialogs side effects in CI
    monkeypatch.setattr(
        "handforge.ui.main_window.QSystemTrayIcon.isSystemTrayAvailable",
        staticmethod(lambda: False),
    )
    win = MainWindow()
    yield win
    win.close()


def test_keyboard_shortcuts_catalog_complete():
    """Catalog lists every common action documented for Help / docs."""
    keys = {k for k, _ in KEYBOARD_SHORTCUTS}
    assert keys == {
        "Ctrl+O",
        "Ctrl+Shift+O",
        "Ctrl+Return",
        "Ctrl+.",
        "Delete",
        "Ctrl+Shift+K",
        "Ctrl+Shift+Delete",
        "Ctrl+,",
        "Ctrl+P",
        "Ctrl+Shift+L",
        "Ctrl+1",
        "Ctrl+2",
        "Ctrl+Q",
        "F1",
    }


def test_actions_have_expected_shortcuts(main_window):
    for attr, expected in _ACTION_SHORTCUTS.items():
        action = getattr(main_window, attr)
        actual = action.shortcut().toString(QKeySequence.SequenceFormat.PortableText)
        # Compare via QKeySequence so "Delete" / "Del" and platform variants match
        assert action.shortcut() == QKeySequence(expected), (
            f"{attr}: expected {expected!r}, got {actual!r}"
        )
        # Every shortcut action must be connected (receivers > 0)
        assert action.receivers(action.triggered) >= 1


def test_clear_queue_removes_jobs(main_window, monkeypatch, tmp_path):
    src = tmp_path / "a.wav"
    src.write_bytes(b"RIFF")
    main_window.queue = [
        Job(src=str(src), dst_dir=str(tmp_path), format="mp3", mode="CBR", bitrate="192")
    ]
    main_window.file_subtitle_tracks[str(src)] = []
    main_window.update_queue_table()
    assert len(main_window.queue) == 1

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    main_window.clear_queue()
    assert main_window.queue == []
    assert main_window.file_subtitle_tracks == {}
    assert main_window.queue_table.rowCount() == 0


def test_focus_queue_and_active(main_window, monkeypatch):
    """Focus helpers call setFocus on the real queue / Active Conversions tables."""
    calls: list[str] = []

    def _track(name):
        def _set_focus(*_args, **_kwargs):
            calls.append(name)

        return _set_focus

    monkeypatch.setattr(main_window.queue_table, "setFocus", _track("queue"))
    monkeypatch.setattr(main_window.workers_table, "setFocus", _track("active"))

    main_window.focus_queue()
    main_window.focus_active_conversions()
    assert calls == ["queue", "active"]
