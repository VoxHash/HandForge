"""Tests for the curated preset template library and import/export."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from handforge.cli import EXIT_OK, EXIT_USAGE, main
from handforge.core.presets import (
    BUILTIN_PRESETS,
    apply_template,
    export_presets,
    export_template_library,
    get_preset,
    get_template,
    import_presets,
    list_template_categories,
    list_templates,
    parse_preset_file_payload,
)
from handforge.core.settings import load_custom_presets


def test_template_library_loads_real_json():
    templates = list_templates()
    assert len(templates) >= 10
    ids = {t["id"] for t in templates}
    assert "podcast-aac-128" in ids
    assert "youtube-1080p-h264" in ids
    for template in templates:
        assert template["name"]
        assert template["category"]
        assert "format" in template["options"]


def test_list_templates_category_filter():
    podcast = list_templates(category="Podcast")
    assert podcast
    assert all(t["category"] == "Podcast" for t in podcast)
    assert "Podcast" in list_template_categories()


def test_get_template_by_id_and_name():
    by_id = get_template("podcast-aac-128")
    by_name = get_template("Podcast AAC 128k")
    assert by_id["id"] == by_name["id"]
    assert by_id["options"]["bitrate"] == "128"
    assert by_id["options"]["format"] == "m4a"


def test_get_preset_resolves_template_without_install(isolated_config_dir):
    opts = get_preset("youtube-1080p-h264")
    assert opts["format"] == "mp4"
    assert opts["video_codec"] == "libx264"
    assert opts["video_bitrate"] == "8000"
    assert opts["bitrate"] == "384"
    # Not written to customs until apply_template
    assert load_custom_presets() == {}


def test_youtube_and_podcast_values_match_published_guidance():
    yt = get_template("youtube-1080p-h264")["options"]
    assert yt["video_bitrate"] == "8000"  # YouTube SDR 1080p ~8 Mbps
    assert yt["bitrate"] == "384"  # YouTube stereo AAC recommendation
    pod = get_template("podcast-aac-128")["options"]
    assert pod["bitrate"] == "128"  # Apple Podcasts stereo RSS baseline


def test_apply_template_persists_custom(isolated_config_dir):
    name, opts = apply_template("podcast-aac-160")
    assert name == "Podcast AAC 160k"
    assert opts["bitrate"] == "160"
    customs = load_custom_presets()
    assert customs[name] == opts
    with pytest.raises(FileExistsError):
        apply_template("podcast-aac-160")
    name2, _ = apply_template("podcast-aac-160", overwrite=True)
    assert name2 == name


def test_apply_template_as_name(isolated_config_dir):
    name, opts = apply_template("music-archive-flac", as_name="My FLAC")
    assert name == "My FLAC"
    assert opts["format"] == "flac"
    assert load_custom_presets()["My FLAC"]["mode"] == "Lossless"


def test_export_import_roundtrip(isolated_config_dir, tmp_path):
    apply_template("voice-speech-mp3-96", as_name="Speech")
    out = tmp_path / "presets.json"
    export_presets(out)
    raw = json.loads(out.read_text(encoding="utf-8"))
    assert raw["type"] == "handforge-presets"
    assert "Speech" in raw["presets"]

    # Replace with a different set via import
    other = tmp_path / "other.json"
    other.write_text(
        json.dumps(
            {
                "version": 1,
                "presets": {
                    "Imported AAC": {
                        "format": "aac",
                        "mode": "CBR",
                        "bitrate": "256",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    result = import_presets(other, replace=True)
    assert set(result.keys()) == {"Imported AAC"}
    assert load_custom_presets() == result


def test_import_accepts_template_library_shape(isolated_config_dir, tmp_path):
    lib = tmp_path / "lib.json"
    export_template_library(lib)
    # Importing the library file installs templates as named customs
    customs = import_presets(lib, replace=True)
    assert "Podcast AAC 128k" in customs
    assert customs["Podcast AAC 128k"]["bitrate"] == "128"


def test_parse_bare_preset_map():
    parsed = parse_preset_file_payload(
        {"X": {"format": "mp3", "mode": "CBR", "bitrate": "192"}}
    )
    assert parsed["X"]["format"] == "mp3"


def test_cli_list_templates(capsys, isolated_config_dir):
    assert main(["list-templates"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "podcast-aac-128" in out
    assert "youtube-1080p-h264" in out


def test_cli_list_templates_bad_category(capsys, isolated_config_dir):
    assert main(["list-templates", "--category", "Nope"]) == EXIT_USAGE


def test_cli_apply_and_convert_preset_resolution(capsys, isolated_config_dir):
    assert main(["apply-template", "podcast-aac-128"]) == EXIT_OK
    assert "Podcast AAC 128k" in capsys.readouterr().out
    customs = load_custom_presets()
    assert "Podcast AAC 128k" in customs


def test_cli_export_import(isolated_config_dir, tmp_path):
    apply_template("music-hifi-mp3-320", as_name="HiFi")
    out = tmp_path / "out.json"
    assert main(["export-presets", str(out)]) == EXIT_OK
    assert out.is_file()
    # Clear and re-import
    from handforge.core.settings import save_custom_presets

    save_custom_presets({})
    assert load_custom_presets() == {}
    assert main(["import-presets", str(out)]) == EXIT_OK
    assert "HiFi" in load_custom_presets()


def test_builtin_still_preferred_over_same_name_template(isolated_config_dir):
    # AAC 256k is builtin; get_preset must return builtin options
    opts = get_preset("AAC 256k")
    assert opts == BUILTIN_PRESETS["AAC 256k"]
