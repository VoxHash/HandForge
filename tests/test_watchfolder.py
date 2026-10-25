"""Tests for watch-folder / hotfolder auto-convert."""

from __future__ import annotations

import time

import pytest

from handforge.core.settings import load_seen_files, load_settings, save_seen_files
from handforge.util import watchfolder as wf


def test_watchfolder_defaults_off(isolated_config_dir):
    settings = load_settings()
    assert wf.watchfolder_enabled(settings) is False
    assert wf.watchfolder_dirs(settings) == []
    assert wf.watchfolder_interval(settings) == pytest.approx(5.0)
    assert wf.watchfolder_recursive(settings) is True


def test_iter_media_files_and_scan(tmp_path, isolated_config_dir):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    media = inbox / "clip.wav"
    media.write_bytes(b"RIFF" + b"\x00" * 8 + b"WAVE" + b"\x00" * 64)
    (inbox / "notes.txt").write_text("ignore")

    found = wf.iter_media_files([str(inbox)], recursive=True)
    assert [p.name for p in found] == ["clip.wav"]

    ready, seen, pending = wf.scan_once(
        [str(inbox)], settle_seconds=0.25, pending_fps={}
    )
    assert ready == []
    assert pending

    time.sleep(0.3)
    ready2, seen2, _pending2 = wf.scan_once(
        [str(inbox)],
        seen=seen,
        settle_seconds=0.25,
        pending_fps=pending,
    )
    assert len(ready2) == 1
    assert ready2[0].name == "clip.wav"
    assert str(media.resolve()) in seen2
    save_seen_files(seen2)
    assert str(media.resolve()) in load_seen_files()

    ready3, _, _ = wf.scan_once(
        [str(inbox)], seen=seen2, settle_seconds=0.0, pending_fps={}
    )
    assert ready3 == []


def test_format_watchfolder_status():
    text = wf.format_watchfolder_status(
        {
            "watchfolder_enabled": True,
            "watchfolder_dirs": ["/tmp/inbox"],
            "watchfolder_interval_seconds": 3,
            "watchfolder_recursive": False,
        }
    )
    assert "enabled: yes" in text
    assert "/tmp/inbox" in text
    assert "recursive: no" in text
