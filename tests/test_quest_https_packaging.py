"""Quest / store HTTPS packaging: assetlinks + quest.webmanifest routes."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from handforge.companion.server import CompanionServer, STATIC_DIR, generate_token
from handforge.companion.status import QueueStatusHub

REPO_ROOT = Path(__file__).resolve().parents[1]
BW_DIR = REPO_ROOT / "companions" / "quest" / "bubblewrap"
SCRIPT = REPO_ROOT / "scripts" / "quest-https-package.sh"


def _free_port() -> int:
    import socket

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def test_bubblewrap_kit_files_exist():
    assert (BW_DIR / "twa-manifest.template.json").is_file()
    assert (BW_DIR / "assetlinks.template.json").is_file()
    assert (BW_DIR / "Caddyfile.example").is_file()
    assert (BW_DIR / "nginx.conf.example").is_file()
    assert (BW_DIR / "README.md").is_file()
    assert SCRIPT.is_file()
    assert (STATIC_DIR / "quest.webmanifest").is_file()
    twa = json.loads((BW_DIR / "twa-manifest.template.json").read_text(encoding="utf-8"))
    assert twa["isMetaQuest"] is True
    assert twa["horizonOSAppMode"] == "2D"
    assert twa["startUrl"] == "/quest.html"
    assert twa["packageId"] == "dev.voxhash.handforge.quest"


def test_quest_webmanifest_public_without_token():
    hub = QueueStatusHub()
    token = generate_token()
    port = _free_port()
    server = CompanionServer(hub, host="127.0.0.1", port=port, token=token)
    server.start()
    try:
        base = f"http://127.0.0.1:{port}"
        # No ?token= — Bubblewrap must fetch this over public HTTPS.
        with urllib.request.urlopen(f"{base}/quest.webmanifest", timeout=3) as resp:
            manifest = json.loads(resp.read().decode("utf-8"))
        assert manifest["start_url"] == "/quest.html"
        assert manifest["display"] == "standalone"

        with urllib.request.urlopen(f"{base}/static/icon-512.png", timeout=3) as resp:
            assert resp.status == 200
            assert resp.headers.get_content_type() == "image/png"
            assert len(resp.read()) > 32
    finally:
        server.stop()


def test_assetlinks_404_until_published_then_public():
    hub = QueueStatusHub()
    token = generate_token()
    port = _free_port()
    server = CompanionServer(hub, host="127.0.0.1", port=port, token=token)
    server.start()
    well_known = STATIC_DIR / ".well-known"
    target = well_known / "assetlinks.json"
    backup = None
    if target.is_file():
        backup = target.read_bytes()
        target.unlink()
    try:
        base = f"http://127.0.0.1:{port}"
        try:
            urllib.request.urlopen(f"{base}/.well-known/assetlinks.json", timeout=3)
            raise AssertionError("expected 404 before publish")
        except urllib.error.HTTPError as err:
            assert err.code == 404
            body = json.loads(err.read().decode("utf-8"))
            assert body.get("error") == "assetlinks_not_configured"

        well_known.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "relation": ["delegate_permission/common.handle_all_urls"],
                "target": {
                    "namespace": "android_app",
                    "package_name": "dev.voxhash.handforge.quest",
                    "sha256_cert_fingerprints": ["AA:BB:CC:DD"],
                },
            }
        ]
        target.write_text(json.dumps(payload), encoding="utf-8")
        with urllib.request.urlopen(f"{base}/.well-known/assetlinks.json", timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        assert data[0]["target"]["package_name"] == "dev.voxhash.handforge.quest"
    finally:
        if target.is_file() and backup is None:
            # Remove test-only publish so developers do not ship AA:BB:CC:DD
            target.unlink()
        elif backup is not None:
            target.write_bytes(backup)
        server.stop()
