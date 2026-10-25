"""Tests for companion real-time preview and collaborative preset sharing."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from handforge.companion.preview import generate_preview, resolve_preview_source
from handforge.companion.server import CompanionServer, generate_token
from handforge.companion.share import (
    export_share_payload,
    import_share_payload,
    list_shareable_presets,
)
from handforge.companion.status import QueueStatusHub
from handforge.core.presets import load_custom_presets, save_custom_presets
from handforge.util.ffmpeg import find_ffmpeg


def _free_port() -> int:
    import socket

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _http(url: str, *, data=None, method: str = "GET"):
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = method if method != "GET" else "POST"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw.startswith("{") or raw.startswith("[") else raw
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return err.code, payload


@pytest.fixture
def custom_preset(isolated_config_dir):
    save_custom_presets(
        {
            "LAN Share Test": {
                "format": "flac",
                "mode": "Lossless",
            }
        }
    )
    yield
    save_custom_presets({})


def test_list_and_export_shareable_presets(custom_preset):
    data = list_shareable_presets()
    assert data["ok"] is True
    assert "LAN Share Test" in data["names"]
    payload = export_share_payload()
    assert payload["type"] == "handforge-presets"
    assert "LAN Share Test" in payload["presets"]


def test_import_share_payload_merges(isolated_config_dir):
    result = import_share_payload(
        {
            "version": 1,
            "type": "handforge-presets",
            "presets": {"Imported A": {"format": "mp3", "mode": "CBR", "bitrate": "128"}},
        }
    )
    assert result["ok"] is True
    assert "Imported A" in result["imported"]
    customs = load_custom_presets()
    assert customs["Imported A"]["format"] == "mp3"


@pytest.mark.skipif(not find_ffmpeg(), reason="FFmpeg required for real preview")
def test_generate_audio_preview(tmp_path, isolated_config_dir, monkeypatch):
    from handforge.companion import preview as preview_mod

    monkeypatch.setattr(preview_mod, "get_config_dir", lambda: tmp_path)

    # Tiny valid-ish wav header + silence payload; FFmpeg accepts short wavs.
    wav = tmp_path / "tone.wav"
    # Generate via FFmpeg lavfi for a real file
    import subprocess

    ffmpeg = find_ffmpeg()
    subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            str(wav),
        ],
        check=True,
        capture_output=True,
    )
    result = generate_preview(str(wav), seconds=1.0, config_dir=tmp_path)
    assert result["ok"] is True
    assert result["kind"] == "audio"
    assert result["url"].startswith("/api/preview/")


def test_preview_and_presets_http_routes(isolated_config_dir, custom_preset):
    hub = QueueStatusHub()
    token = generate_token()
    port = _free_port()
    server = CompanionServer(hub, host="127.0.0.1", port=port, token=token)
    server.start()
    try:
        base = f"http://127.0.0.1:{port}"
        code, presets = _http(f"{base}/api/presets?token={token}")
        assert code == 200
        assert "LAN Share Test" in presets["names"]

        code, exported = _http(f"{base}/api/presets/export?token={token}")
        assert code == 200
        assert exported["type"] == "handforge-presets"

        code, imported = _http(
            f"{base}/api/presets/import?token={token}",
            data={
                "version": 1,
                "type": "handforge-presets",
                "presets": {
                    "Via API": {"format": "ogg", "mode": "VBR", "vbrq": 5}
                },
            },
        )
        assert code == 200
        assert imported["ok"] is True

        code, report = _http(f"{base}/api/analytics/report?token={token}")
        assert code == 200
        assert report["local_only"] is True
        assert report["ok"] is True

        code, missing = _http(
            f"{base}/api/control/preview?token={token}",
            data={"path": "/tmp/does-not-exist-handforge.wav"},
        )
        assert code == 400
        assert missing["ok"] is False
    finally:
        server.stop()


def test_quest_and_pwa_static_routes():
    hub = QueueStatusHub()
    token = generate_token()
    port = _free_port()
    server = CompanionServer(hub, host="127.0.0.1", port=port, token=token)
    server.start()
    try:
        base = f"http://127.0.0.1:{port}"
        with urllib.request.urlopen(f"{base}/quest.html?token={token}", timeout=3) as resp:
            html = resp.read().decode("utf-8")
        assert "HandForge Quest" in html
        assert "Shared control" in html

        with urllib.request.urlopen(
            f"{base}/manifest.webmanifest?token={token}", timeout=3
        ) as resp:
            manifest = json.loads(resp.read().decode("utf-8"))
        assert manifest["name"]
        assert any(i.get("src") for i in manifest.get("icons") or [])

        with urllib.request.urlopen(f"{base}/sw.js", timeout=3) as resp:
            sw = resp.read().decode("utf-8")
        assert "handforge-companion" in sw
    finally:
        server.stop()


def test_resolve_preview_source_from_path():
    src, err = resolve_preview_source(path="/media/a.wav")
    assert err is None
    assert src.endswith("a.wav")
