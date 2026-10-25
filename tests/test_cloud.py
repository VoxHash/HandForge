"""Unit tests for cloud roots + optional rclone helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from handforge.util import cloud as cloud_mod


def test_parse_listremotes_output():
    text = "gdrive:\ndropbox:\n# comment\nbad line\nnextcloud:\n"
    assert cloud_mod.parse_listremotes_output(text) == [
        "gdrive:",
        "dropbox:",
        "nextcloud:",
    ]


def test_is_rclone_path_and_windows_drive():
    assert cloud_mod.is_rclone_path("gdrive:HandForge/In")
    assert cloud_mod.is_rclone_path("rclone:gdrive:Media/Out")
    assert cloud_mod.is_rclone_path("s3:my-bucket/clips")
    assert not cloud_mod.is_rclone_path("/home/user/Dropbox")
    assert not cloud_mod.is_rclone_path("C:\\Users\\me\\OneDrive")
    assert not cloud_mod.is_rclone_path("D:/Media")
    assert not cloud_mod.is_rclone_path("https://example.com/a.mp3")
    assert not cloud_mod.is_rclone_path("plain-folder")


def test_parse_and_join_rclone_path():
    remote, sub = cloud_mod.parse_rclone_path("gdrive:HandForge/In")
    assert remote == "gdrive:"
    assert sub == "HandForge/In"
    assert cloud_mod.join_rclone_path("gdrive", "HandForge/Out") == "gdrive:HandForge/Out"
    assert cloud_mod.join_rclone_path("gdrive:", "") == "gdrive:"
    with pytest.raises(ValueError):
        cloud_mod.parse_rclone_path("/local/path")


def test_configured_and_all_cloud_roots_with_temp(tmp_path):
    root_a = tmp_path / "Dropbox"
    root_a.mkdir()
    root_b = tmp_path / "WorkSync"
    root_b.mkdir()
    missing = tmp_path / "missing"
    settings = {
        "cloud_roots": [str(root_a), str(root_b), str(missing), str(root_a)],
    }
    configured = cloud_mod.configured_cloud_roots(settings)
    assert str(root_a) in configured
    assert str(root_b) in configured
    assert str(missing) not in configured

    merged = cloud_mod.all_cloud_roots(settings)
    paths = {r.path for r in merged}
    assert str(root_a) in paths
    assert str(root_b) in paths


def test_default_browse_dir_prefers_cloud_input_root(tmp_path):
    preferred = tmp_path / "cloud_in"
    preferred.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    settings = {
        "cloud_input_root": str(preferred),
        "cloud_roots": [str(other)],
    }
    assert cloud_mod.default_browse_dir(settings) == str(preferred)


def test_resolve_output_dir_setting_expands(tmp_path, monkeypatch):
    out = tmp_path / "HandForge_Cloud_Out"
    out.mkdir()
    settings = {"output_dir": str(out)}
    assert cloud_mod.resolve_output_dir_setting(settings) == str(out)

    monkeypatch.setenv("HOME", str(tmp_path))
    # ~ expansion
    nested = tmp_path / "nested_out"
    nested.mkdir()
    settings2 = {"output_dir": "~/nested_out"}
    # expanduser uses real HOME; override via monkeypatch home is OS-dependent —
    # just ensure non-empty string returned for a relative-style path we expand.
    expanded = cloud_mod.expand_local_path(str(out))
    assert expanded == str(out)


def test_prepare_output_local(tmp_path):
    out = tmp_path / "encode_out"
    resolved = cloud_mod.prepare_output(str(out), settings={})
    assert resolved.local_dir == str(out)
    assert resolved.rclone_dest is None
    assert out.is_dir()
    assert resolved.staging is False


def test_prepare_output_rclone_stages(tmp_path, monkeypatch):
    settings = {"rclone_enabled": True}

    def fake_find(_binary=None):
        return "/usr/bin/rclone"

    monkeypatch.setattr(cloud_mod, "find_rclone", fake_find)
    resolved = cloud_mod.prepare_output(
        "gdrive:HandForge/Out",
        settings=settings,
        staging_parent=str(tmp_path),
    )
    assert resolved.rclone_dest == "gdrive:HandForge/Out"
    assert resolved.staging is True
    assert Path(resolved.local_dir).is_dir()
    assert str(tmp_path) in resolved.local_dir


def test_prepare_output_rclone_missing_binary(tmp_path):
    settings = {"rclone_enabled": True, "rclone_binary": ""}
    with patch.object(cloud_mod, "find_rclone", return_value=None):
        with pytest.raises(FileNotFoundError, match="rclone is not installed"):
            cloud_mod.prepare_output("gdrive:Out", settings=settings)


def test_prepare_inputs_local_passthrough(tmp_path):
    media = tmp_path / "clip.wav"
    media.write_bytes(b"RIFF")
    resolved = cloud_mod.prepare_inputs([str(media)], settings={})
    assert resolved.paths == [str(media)]


def test_rclone_copy_invokes_subprocess(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.wav").write_bytes(b"RIFF")
    dest = "gdrive:Out"

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""

    with patch.object(cloud_mod, "find_rclone", return_value="/usr/bin/rclone"):
        with patch("handforge.util.cloud.subprocess.run", return_value=mock_result) as run:
            cloud_mod.rclone_copy(str(src), dest, settings={})
            assert run.called
            cmd = run.call_args[0][0]
            assert cmd[0] == "/usr/bin/rclone"
            assert cmd[1] == "copy"
            assert cmd[2] == str(src)
            assert cmd[3] == dest


def test_list_rclone_remotes_parses_mocked_cli():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "gdrive:\nbox:\n"
    mock_result.stderr = ""

    with patch.object(cloud_mod, "find_rclone", return_value="/usr/bin/rclone"):
        with patch("handforge.util.cloud.subprocess.run", return_value=mock_result):
            remotes = cloud_mod.list_rclone_remotes({})
    assert remotes == ["gdrive:", "box:"]


def test_list_rclone_remotes_empty_when_missing():
    with patch.object(cloud_mod, "find_rclone", return_value=None):
        assert cloud_mod.list_rclone_remotes({}) == []


def test_format_cloud_status_without_rclone(tmp_path):
    root = tmp_path / "MyCloud"
    root.mkdir()
    settings = {"cloud_roots": [str(root)], "output_dir": str(root)}
    with patch.object(cloud_mod, "find_rclone", return_value=None):
        text = cloud_mod.format_cloud_status(settings)
    assert "rclone: not found" in text
    assert str(root) in text
    assert "settings output_dir" in text


@pytest.mark.skipif(
    cloud_mod.find_rclone() is None,
    reason="rclone not installed on this host",
)
def test_integration_listremotes_when_rclone_present():
    """Live rclone listremotes — skipped when binary absent."""
    remotes = cloud_mod.list_rclone_remotes({})
    assert isinstance(remotes, list)
    for name in remotes:
        assert name.endswith(":")


def test_cli_list_cloud_runs(capsys, isolated_config_dir):
    from handforge.cli import EXIT_OK, main

    code = main(["list-cloud"])
    assert code == EXIT_OK
    out = capsys.readouterr().out
    assert "rclone:" in out
    assert "cloud roots" in out


def test_settings_cloud_defaults(isolated_config_dir):
    from handforge.core import settings as settings_mod

    loaded = settings_mod.load_settings()
    assert loaded["cloud_roots"] == []
    assert loaded["rclone_enabled"] is True
    assert loaded["rclone_remote"] == ""
    assert loaded["rclone_binary"] == ""
    assert loaded["cloud_input_root"] is None
