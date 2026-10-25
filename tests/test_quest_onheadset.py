"""Quest on-headset encode surface: UI copy + heavy presets wiring."""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from handforge.companion.server import CompanionServer, generate_token
from handforge.companion.status import QueueStatusHub

ROOT = Path(__file__).resolve().parents[1]


def _free_port() -> int:
    import socket

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port

QUEST_HTML = ROOT / "handforge" / "companion" / "static" / "quest.html"
QUEST_README = ROOT / "companions" / "quest" / "README.md"
PRESETS = (
    ROOT
    / "companions"
    / "android"
    / "android"
    / "app"
    / "src"
    / "main"
    / "assets"
    / "encode_presets.json"
)


def test_quest_html_on_headset_section():
    html = QUEST_HTML.read_text(encoding="utf-8")
    assert 'id="on-headset"' in html
    assert "HandForgeNative" in html
    assert "Open on-headset encode" in html
    assert "video_mp4_quest_1080" in html
    assert "Thermal" in html or "thermal" in html
    assert "LocalEncodeActivity" in html


def test_quest_readme_documents_apk_path():
    text = QUEST_README.read_text(encoding="utf-8")
    assert "LocalEncodeActivity" in text
    assert "fetch-android-ffmpeg" in text
    assert "thermal" in text.lower()
    assert "HandForgeNative" in text


def test_heavy_presets_exist_for_quest():
    doc = json.loads(PRESETS.read_text(encoding="utf-8"))
    heavy_ids = {p["id"] for p in doc["presets"] if p.get("tier") == "heavy"}
    assert "video_mp4_quest_720_hq" in heavy_ids
    assert "video_mp4_quest_1080" in heavy_ids
    assert "video_mp4_quest_bitrate" in heavy_ids


def test_quest_html_served_includes_on_headset():
    hub = QueueStatusHub()
    token = generate_token()
    port = _free_port()
    server = CompanionServer(hub, host="127.0.0.1", port=port, token=token)
    server.start()
    try:
        base = f"http://127.0.0.1:{port}"
        with urllib.request.urlopen(f"{base}/quest.html?token={token}", timeout=3) as resp:
            html = resp.read().decode("utf-8")
        assert "On-headset encode" in html
        assert "btn-headset-encode" in html
        assert "HandForgeNative" in html
    finally:
        server.stop()
