"""Tests for plugin discovery, registration, and convert hooks."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from handforge.core.presets import all_presets, get_preset
from handforge.plugins import (
    ConvertHookContext,
    ensure_plugins_loaded,
    get_registry,
    load_file_plugin,
    load_plugins,
    mark_plugins_unloaded,
    reset_registry,
)
from handforge.plugins.api import PluginInfo
from handforge.plugins.loader import discover_plugin_files


@pytest.fixture(autouse=True)
def _clean_plugins():
    """Isolate plugin state for every test."""
    reset_registry()
    mark_plugins_unloaded()
    yield
    reset_registry()
    mark_plugins_unloaded()


def _write_plugin(root: Path, name: str, body: str) -> Path:
    plugin_dir = root / name
    plugin_dir.mkdir(parents=True)
    path = plugin_dir / "plugin.py"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def test_discover_plugin_files(tmp_path: Path):
    _write_plugin(
        tmp_path,
        "demo",
        """
        def register(registry):
            pass
        """,
    )
    found = discover_plugin_files([tmp_path])
    assert len(found) == 1
    assert found[0].name == "plugin.py"


def test_load_preset_plugin(tmp_path: Path):
    _write_plugin(
        tmp_path,
        "voice_preset",
        """
        from handforge.plugins.api import PluginInfo

        def register(registry):
            registry.register_preset(
                "Voice Memo (plugin)",
                {"format": "mp3", "mode": "CBR", "bitrate": "96"},
            )
            return PluginInfo(
                name="voice_preset",
                version="0.1.0",
                description="test preset plugin",
            )
        """,
    )
    reg = load_plugins(
        directories=[tmp_path],
        include_entry_points=False,
        reload=True,
    )
    assert "Voice Memo (plugin)" in reg.presets
    assert reg.presets["Voice Memo (plugin)"]["format"] == "mp3"
    assert any(p.info.name == "voice_preset" for p in reg.loaded_plugins)
    assert get_preset("Voice Memo (plugin)")["bitrate"] == "96"
    assert "Voice Memo (plugin)" in all_presets()


def test_custom_preset_overrides_plugin(tmp_path: Path, isolated_config_dir, monkeypatch):
    from handforge.core import settings as settings_mod

    _write_plugin(
        tmp_path,
        "overlap",
        """
        def register(registry):
            registry.register_preset(
                "Overlap",
                {"format": "mp3", "mode": "CBR", "bitrate": "64"},
            )
        """,
    )
    load_plugins(directories=[tmp_path], include_entry_points=False, reload=True)
    settings_mod.save_custom_presets(
        {"Overlap": {"format": "flac", "mode": "Lossless"}}
    )
    merged = all_presets()
    assert merged["Overlap"]["format"] == "flac"


def test_post_convert_hook_writes_sidecar(tmp_path: Path):
    # Load via a real file so discovery path is exercised
    path = _write_plugin(
        tmp_path,
        "marker",
        """
        from pathlib import Path
        from handforge.plugins.api import PluginInfo

        def register(registry):
            def on_post(ctx):
                Path(ctx.dst + ".mark").write_text("ok", encoding="utf-8")
            registry.register_post_convert(on_post)
            return PluginInfo(name="marker", version="1.0.0")
        """,
    )
    reg = reset_registry()
    load_file_plugin(path, reg)
    out = tmp_path / "out.flac"
    out.write_text("fake", encoding="utf-8")
    ctx = ConvertHookContext(
        src="in.wav",
        dst=str(out),
        format="flac",
        success=True,
        job=None,
        settings={},
        message="done",
    )
    errors = reg.run_post_convert(ctx)
    assert errors == []
    assert Path(str(out) + ".mark").read_text(encoding="utf-8") == "ok"


def test_hook_errors_are_isolated(tmp_path: Path):
    reg = reset_registry()

    def bad(_ctx):
        raise RuntimeError("boom")

    def good(ctx):
        ctx.settings["seen"] = True

    reg.register_post_convert(bad)
    reg.register_post_convert(good)
    ctx = ConvertHookContext(
        src="a",
        dst="b",
        format="mp3",
        success=True,
        job=None,
        settings={},
    )
    errors = reg.run_post_convert(ctx)
    assert len(errors) == 1
    assert "boom" in errors[0]
    assert ctx.settings.get("seen") is True


def test_broken_plugin_does_not_abort_others(tmp_path: Path):
    _write_plugin(
        tmp_path,
        "broken",
        """
        def register(registry):
            raise RuntimeError("cannot start")
        """,
    )
    _write_plugin(
        tmp_path,
        "good",
        """
        from handforge.plugins.api import PluginInfo

        def register(registry):
            registry.register_preset(
                "Good Plugin Preset",
                {"format": "ogg", "mode": "VBR", "vbrq": "5"},
            )
            return PluginInfo(name="good", version="1.0.0")
        """,
    )
    reg = load_plugins(
        directories=[tmp_path],
        include_entry_points=False,
        reload=True,
    )
    assert "Good Plugin Preset" in reg.presets
    failed = [p for p in reg.loaded_plugins if p.errors]
    assert any("cannot start" in e for p in failed for e in p.errors)


def test_ensure_plugins_loaded_respects_disabled(tmp_path: Path, monkeypatch):
    _write_plugin(
        tmp_path,
        "ignored",
        """
        def register(registry):
            registry.register_preset(
                "Should Not Load",
                {"format": "mp3", "mode": "CBR", "bitrate": "128"},
            )
        """,
    )
    monkeypatch.setenv("HANDFORGE_PLUGIN_DIRS", str(tmp_path))
    mark_plugins_unloaded()
    reg = ensure_plugins_loaded({"plugins_enabled": False}, reload=True)
    assert "Should Not Load" not in reg.presets


def test_ensure_plugins_loaded_extra_dirs(tmp_path: Path):
    _write_plugin(
        tmp_path,
        "extra",
        """
        from handforge.plugins.api import PluginInfo

        def register(registry):
            registry.register_preset(
                "Extra Dir Preset",
                {"format": "wav", "mode": "Lossless"},
            )
            return PluginInfo(name="extra", version="1.0.0")
        """,
    )
    mark_plugins_unloaded()
    reg = ensure_plugins_loaded(
        {"plugins_enabled": True, "plugin_dirs": [str(tmp_path)]},
        reload=True,
    )
    assert "Extra Dir Preset" in reg.presets


def test_example_plugin_loads_and_writes_sidecar(tmp_path: Path):
    """Load the in-repo example plugin and exercise its post_convert hook."""
    repo_example = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "plugins"
        / "archive_flac_sidecar"
        / "plugin.py"
    )
    assert repo_example.is_file()
    reg = reset_registry()
    load_file_plugin(repo_example, reg)
    assert "Archive FLAC (plugin)" in reg.presets
    assert reg.presets["Archive FLAC (plugin)"]["format"] == "flac"
    assert len(reg.post_convert_hooks) == 1

    out = tmp_path / "archive.flac"
    out.write_bytes(b"fLaC")
    ctx = ConvertHookContext(
        src="src.wav",
        dst=str(out),
        format="flac",
        success=True,
        job=None,
        settings={},
        message="ok",
    )
    errors = reg.run_post_convert(ctx)
    assert errors == []
    sidecar = Path(str(out) + ".handforge.json")
    assert sidecar.is_file()
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    assert data["handforge_plugin"] == "archive_flac_sidecar"
    assert data["dst"] == str(out)


def test_invalid_preset_rejected():
    reg = reset_registry()
    with pytest.raises(ValueError):
        reg.register_preset("", {"format": "mp3"})
    with pytest.raises(ValueError):
        reg.register_preset("Bad", {"bitrate": "128"})  # missing format
