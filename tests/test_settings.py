"""Unit tests for settings persistence (isolated config dir)."""

from __future__ import annotations

from handforge.core import settings as settings_mod


def test_load_settings_merges_defaults(isolated_config_dir):
    loaded = settings_mod.load_settings()
    assert loaded["parallel"] == 2
    assert loaded["adaptive_parallel"] is True
    assert loaded["ewma_alpha"] == 0.3
    assert loaded["hw_accel"] == "auto"
    assert loaded["eq_enabled"] is False
    assert loaded["compressor_enabled"] is False
    assert loaded["limiter_enabled"] is False
    assert loaded["denoise_enabled"] is False
    assert loaded["video_color_enabled"] is False
    assert loaded["video_stabilize_enabled"] is False
    assert loaded["video_brightness"] == 0.0
    assert loaded["video_contrast"] == 1.0
    assert loaded["video_saturation"] == 1.0
    assert loaded["plugins_enabled"] is True
    assert loaded["plugin_dirs"] == []
    assert "auto_retry_patterns" in loaded
    assert (isolated_config_dir / "settings.json").exists() is False  # not written yet


def test_save_and_reload_settings(isolated_config_dir):
    data = settings_mod.load_settings()
    data["parallel"] = 6
    data["adaptive_parallel"] = False
    data["ewma_alpha"] = 0.5
    settings_mod.save_settings(data)

    path = isolated_config_dir / "settings.json"
    assert path.is_file()

    reloaded = settings_mod.load_settings()
    assert reloaded["parallel"] == 6
    assert reloaded["adaptive_parallel"] is False
    assert reloaded["ewma_alpha"] == 0.5
    # Defaults still fill missing keys
    assert "codec_threads" in reloaded


def test_presets_roundtrip(isolated_config_dir):
    presets = {
        "Podcast": {"format": "mp3", "mode": "CBR", "bitrate": "128"},
        "Archive": {"format": "flac", "mode": "Lossless"},
    }
    settings_mod.save_custom_presets(presets)
    assert settings_mod.load_custom_presets() == presets


def test_patterns_default_and_save(isolated_config_dir):
    patterns = settings_mod.load_patterns()
    assert "{artist} - {title}" in patterns
    custom = ["{title}", "{album}/{track} - {title}"]
    settings_mod.save_patterns(custom)
    assert settings_mod.load_patterns() == custom


def test_autoretry_defaults_and_save(isolated_config_dir):
    rules = settings_mod.load_autoretry()
    assert rules["enabled"] is True
    assert any("Invalid data" in p for p in rules["patterns"])
    rules["enabled"] = False
    rules["patterns"] = ["Custom failure"]
    settings_mod.save_autoretry(rules)
    again = settings_mod.load_autoretry()
    assert again["enabled"] is False
    assert again["patterns"] == ["Custom failure"]


def test_seen_files_roundtrip(isolated_config_dir):
    cache = {"/tmp/a.wav": {"mtime": 1.0, "size": 10}}
    settings_mod.save_seen_files(cache)
    assert settings_mod.load_seen_files() == cache


def test_corrupt_json_returns_default(isolated_config_dir):
    bad = isolated_config_dir / "settings.json"
    bad.write_text("{not-json", encoding="utf-8")
    loaded = settings_mod.load_settings()
    # Falls back to empty merge → defaults
    assert loaded["parallel"] == 2
