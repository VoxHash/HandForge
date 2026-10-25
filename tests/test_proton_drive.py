"""Unit tests for Proton Drive backup helpers (mocked CLI)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from handforge.util import proton_drive as pd


def test_normalize_remote_folder():
    assert pd.normalize_remote_folder(None) == "/my-files/HandForge"
    assert pd.normalize_remote_folder("") == "/my-files/HandForge"
    assert pd.normalize_remote_folder("HandForge/Out") == "/my-files/HandForge/Out"
    assert pd.normalize_remote_folder("/my-files/HandForge/") == "/my-files/HandForge"
    assert pd.normalize_remote_folder("\\my-files\\A") == "/my-files/A"


def test_backup_enabled_and_after_convert_defaults():
    assert not pd.backup_enabled({})
    assert not pd.after_convert_enabled({})
    settings = {
        "proton_drive_backup_enabled": True,
        "proton_drive_after_convert": True,
    }
    assert pd.backup_enabled(settings)
    assert pd.after_convert_enabled(settings)
    settings["proton_drive_after_convert"] = False
    assert not pd.after_convert_enabled(settings)


def test_collect_successful_outputs(tmp_path):
    good = tmp_path / "a.mp3"
    good.write_bytes(b"abc")
    empty = tmp_path / "empty.mp3"
    empty.write_bytes(b"")
    missing = tmp_path / "nope.mp3"
    found = pd.collect_successful_outputs(
        [str(good), str(empty), str(missing), str(good)]
    )
    assert found == [str(good)]


def test_get_status_missing_binary():
    with patch.object(pd, "find_proton_drive", return_value=None):
        st = pd.get_status({"proton_drive_backup_enabled": False})
    assert not st.available
    assert not st.authenticated
    assert "not found" in st.message.lower()


def test_get_status_authenticated():
    with patch.object(pd, "find_proton_drive", return_value="/usr/bin/proton-drive"), \
         patch.object(pd, "check_authenticated", return_value=True), \
         patch.object(pd, "detect_desktop_running", return_value=False):
        st = pd.get_status(
            {
                "proton_drive_backup_enabled": True,
                "proton_drive_remote_folder": "/my-files/HandForge",
            }
        )
    assert st.available
    assert st.authenticated
    assert st.backup_enabled
    assert "/my-files/HandForge" in st.message


def test_ensure_remote_folder_creates_chain():
    existing = {"/my-files"}

    def fake_exists(path, *, binary=None):
        return path in existing

    calls = []

    def fake_run(args, *, binary=None, timeout=None, check=True):
        # create-folder parent name
        assert args[0:2] == ["filesystem", "create-folder"]
        parent, name = args[2], args[3]
        new_path = f"{parent.rstrip('/')}/{name}"
        existing.add(new_path)
        calls.append(new_path)
        return MagicMock(returncode=0, stdout="{}", stderr="")

    with patch.object(pd, "_folder_exists", side_effect=fake_exists), \
         patch.object(pd, "_run_proton", side_effect=fake_run):
        path = pd.ensure_remote_folder("/my-files/HandForge/Out", settings={})
    assert path == "/my-files/HandForge/Out"
    assert "/my-files/HandForge" in calls
    assert "/my-files/HandForge/Out" in calls


def test_upload_paths_invokes_cli(tmp_path):
    f = tmp_path / "out.mp3"
    f.write_bytes(b"data")
    captured = {}

    def fake_run(args, *, binary=None, timeout=None, check=True):
        captured["args"] = list(args)
        return MagicMock(returncode=0, stdout="", stderr="")

    with patch.object(pd, "find_proton_drive", return_value="/bin/proton-drive"), \
         patch.object(pd, "check_authenticated", return_value=True), \
         patch.object(pd, "ensure_remote_folder", return_value="/my-files/HandForge"), \
         patch.object(pd, "_run_proton", side_effect=fake_run):
        remote = pd.upload_paths([str(f)], "/my-files/HandForge", settings={})
    assert remote == "/my-files/HandForge"
    assert captured["args"][0:2] == ["filesystem", "upload"]
    assert str(f) in captured["args"]
    assert captured["args"][-1] == "/my-files/HandForge"
    assert "-t" in captured["args"]


def test_backup_outputs_include_config(tmp_path, monkeypatch):
    out = tmp_path / "x.mp4"
    out.write_bytes(b"video")
    home = tmp_path / "home"
    cfg = home / ".handforge"
    cfg.mkdir(parents=True)
    (cfg / "settings.json").write_text("{}", encoding="utf-8")
    (cfg / "presets.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(pd, "Path", Path)
    monkeypatch.setattr(Path, "home", lambda: home)

    uploaded = {}

    def fake_upload(paths, remote_folder=None, *, settings=None, **kwargs):
        uploaded["paths"] = list(paths)
        return "/my-files/HandForge"

    with patch.object(pd, "upload_paths", side_effect=fake_upload):
        result = pd.backup_outputs(
            [str(out)],
            settings={"proton_drive_backup_config": True},
            include_config=True,
        )
    assert result["uploaded"] == 3
    assert str(out) in uploaded["paths"]
    assert any(p.endswith("settings.json") for p in uploaded["paths"])


def test_format_cloud_status_includes_proton():
    from handforge.util import cloud as cloud_mod

    with patch.object(
        cloud_mod,
        "find_rclone",
        return_value=None,
    ), patch(
        "handforge.util.proton_drive.format_proton_status",
        return_value="proton-drive: available (test); authenticated",
    ):
        text = cloud_mod.format_cloud_status({})
    assert "proton-drive:" in text
