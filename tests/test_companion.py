"""Tests for companion remote queue status + shared workstation control API."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional, Tuple

import pytest

from handforge.companion.control import SessionController
from handforge.companion.server import (
    CompanionServer,
    companion_enabled,
    companion_url,
    generate_token,
    is_loopback_host,
    resolve_companion_bind,
)
from handforge.companion.status import QueueStatusHub, serialize_job_summary
from handforge.core.models import Job
from handforge.core.settings import load_settings


def _job(name: str = "track.wav", fmt: str = "mp3") -> Job:
    return Job(src=f"/tmp/media/{name}", dst_dir="/tmp/out", format=fmt, mode="CBR")


def _free_port() -> int:
    import socket

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _http_json(
    url: str, *, data: Optional[dict] = None, method: str = "GET"
) -> Tuple[int, dict]:
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = method if method != "GET" else "POST"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return err.code, payload


def test_companion_defaults_off(isolated_config_dir):
    settings = load_settings()
    assert companion_enabled(settings) is False
    assert settings["companion_host"] == "127.0.0.1"
    assert int(settings["companion_port"]) == 8765
    assert settings["companion_token"] == ""


def test_is_loopback_and_lan_requires_token():
    assert is_loopback_host("127.0.0.1")
    assert is_loopback_host("localhost")
    assert not is_loopback_host("0.0.0.0")
    host, port, token = resolve_companion_bind({}, lan=True)
    assert host == "0.0.0.0"
    assert port == 8765
    assert token  # auto-minted
    with pytest.raises(ValueError):
        CompanionServer(QueueStatusHub(), host="0.0.0.0", port=8765, token="")


def test_serialize_job_summary_basename_only():
    data = serialize_job_summary(_job("Episode 01.flac"), position=3)
    assert data["file"] == "Episode 01.flac"
    assert data["format"] == "mp3"
    assert data["position"] == 3
    assert "/tmp" not in data["file"]


def test_hub_snapshot_from_orchestrator_state():
    class FakeWorker:
        def __init__(self, job: Job):
            self.job = job
            self._paused = False

    class FakeOrch:
        def __init__(self):
            self.settings = {"parallel": 3, "adaptive_parallel": True}
            self.job_queue = [_job("queued.wav")]
            self.workers = {7: FakeWorker(_job("active.mkv", fmt="mp4"))}

    hub = QueueStatusHub()
    orch = FakeOrch()
    pending = [_job("pending.wav")]
    hub.attach(orch, pending_provider=lambda: pending)
    hub.on_started(7, "/tmp/media/active.mkv")
    hub.on_progress(7, 42.5, 10.0, 12.0, "1.5x")

    snap = hub.snapshot()
    assert snap["state"] == "running"
    assert snap["counts"]["pending"] == 1
    assert snap["counts"]["queued"] == 1
    assert snap["counts"]["active"] == 1
    assert snap["active"][0]["wid"] == 7
    assert snap["active"][0]["progress"] == pytest.approx(42.5)
    assert snap["active"][0]["speed"] == "1.5x"
    assert snap["queued"][0]["file"] == "queued.wav"
    assert snap["pending"][0]["file"] == "pending.wav"
    assert snap["parallel"] == 3

    del orch.workers[7]
    hub.on_done(7, True, "ok", "/tmp/out/active.mp4")
    snap2 = hub.snapshot()
    assert snap2["counts"]["active"] == 0
    assert snap2["recent"][0]["success"] is True
    assert snap2["recent"][0]["output"] == "active.mp4"


def test_http_status_and_auth_roundtrip():
    hub = QueueStatusHub()

    class FakeOrch:
        settings = {"parallel": 2, "adaptive_parallel": False}
        job_queue = [_job("a.wav")]
        workers = {}

    hub.attach(FakeOrch())
    token = generate_token()
    port = _free_port()
    server = CompanionServer(hub, host="127.0.0.1", port=port, token=token)
    server.start()
    try:
        url = companion_url("127.0.0.1", port, token)
        assert f"token={token}" in url

        with pytest.raises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=2)
        assert err.value.code == 401

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/health", timeout=2
        ) as resp:
            health = json.loads(resp.read().decode("utf-8"))
        assert health["ok"] is True
        assert health["auth_required"] is True
        assert health["writes_require_token"] is True

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/status?token={token}", timeout=2
        ) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        assert data["counts"]["queued"] == 1
        assert data["queued"][0]["file"] == "a.wav"
        assert data["control_available"] is False

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/?token={token}", timeout=2
        ) as resp:
            html = resp.read().decode("utf-8")
        assert "HandForge" in html
        assert "Shared workstation" in html
    finally:
        server.stop()


def test_progress_is_monotonic_in_hub():
    hub = QueueStatusHub()
    hub.on_started(1, "/tmp/x.wav")
    hub.on_progress(1, 50.0, 1.0, 1.0, "1x")
    hub.on_progress(1, 40.0, 1.2, 1.0, "1x")
    snap = hub.snapshot()
    assert snap["active"][0]["progress"] == pytest.approx(50.0)


def test_control_writes_require_token_even_on_localhost():
    hub = QueueStatusHub()
    controller = SessionController()

    class FakeOrch:
        settings = {"parallel": 1, "adaptive_parallel": False, "output_dir": "/tmp"}
        job_queue = []
        workers = {}

        def enqueue(self, jobs):
            self.job_queue.extend(jobs)

        def stop_all(self):
            self.job_queue.clear()
            self.workers.clear()

    orch = FakeOrch()
    controller.attach(orch, orch.settings, pending=[])
    port = _free_port()
    # No token configured
    server = CompanionServer(hub, host="127.0.0.1", port=port, token="", controller=controller)
    server.start()
    try:
        code, data = _http_json(f"http://127.0.0.1:{port}/api/control/start", data={})
        assert code == 403
        assert data["error"] == "write_token_required"
    finally:
        server.stop()


def test_control_api_start_stop_add_remove_options(tmp_path):
    hub = QueueStatusHub()
    controller = SessionController()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    media = tmp_path / "clip.wav"
    # Minimal RIFF/WAVE header so is_audio_file accepts .wav by extension
    media.write_bytes(b"RIFF" + b"\x00" * 8 + b"WAVE" + b"\x00" * 32)

    class FakeOrch:
        def __init__(self):
            self.settings = {
                "parallel": 1,
                "adaptive_parallel": False,
                "output_dir": str(out_dir),
            }
            self.job_queue = []
            self.workers = {}
            self.enqueued = []

        def enqueue(self, jobs):
            self.enqueued.extend(jobs)
            self.job_queue.extend(jobs)

        def stop_all(self):
            self.job_queue.clear()
            self.workers.clear()

    orch = FakeOrch()
    pending: list = []
    hub.attach(orch, pending_provider=lambda: list(pending))
    controller.attach(orch, orch.settings, pending=pending, preset_name="MP3 192k")

    token = generate_token()
    port = _free_port()
    server = CompanionServer(
        hub, host="127.0.0.1", port=port, token=token, controller=controller
    )
    server.start()
    try:
        base = f"http://127.0.0.1:{port}"
        # Wrong token
        code, _ = _http_json(f"{base}/api/control/start?token=wrong", data={})
        assert code == 401

        code, ctrl = _http_json(f"{base}/api/control?token={token}")
        assert code == 200
        assert ctrl["control"] is True
        assert "MP3 192k" in ctrl["presets"]
        assert ctrl["writes_require_token"] is True

        code, status = _http_json(f"{base}/api/status?token={token}")
        assert code == 200
        assert status["control_available"] is True

        code, added = _http_json(
            f"{base}/api/control/jobs?token={token}",
            data={"paths": [str(media)]},
        )
        assert code == 200
        assert added["ok"] is True
        assert added["added"] == ["clip.wav"]
        assert len(pending) == 1

        code, opts = _http_json(
            f"{base}/api/control/options?token={token}",
            data={"format": "flac", "mode": "Lossless", "preset": "FLAC Lossless"},
        )
        assert code == 200
        assert opts["ok"] is True
        assert opts["format"] == "flac"

        code, started = _http_json(f"{base}/api/control/start?token={token}", data={})
        assert code == 200
        assert started["ok"] is True
        assert started["enqueued"] == 1
        assert len(orch.enqueued) == 1
        assert orch.enqueued[0].format == "flac"
        assert pending == []

        # Re-queue for remove test
        orch.job_queue = [orch.enqueued[0]]
        code, removed = _http_json(
            f"{base}/api/control/jobs/remove?token={token}",
            data={"scope": "queued", "index": 0},
        )
        assert code == 200
        assert removed["ok"] is True
        assert orch.job_queue == []

        code, added2 = _http_json(
            f"{base}/api/control/jobs?token={token}",
            data={"paths": [str(media)]},
        )
        assert code == 200
        code, cleared = _http_json(
            f"{base}/api/control/jobs/clear?token={token}", data={}
        )
        assert code == 200
        assert cleared["cleared"] == 1
        assert pending == []

        code, stopped = _http_json(f"{base}/api/control/stop?token={token}", data={})
        assert code == 200
        assert stopped["ok"] is True
    finally:
        server.stop()


def test_session_controller_rejects_missing_media(tmp_path):
    controller = SessionController()

    class FakeOrch:
        settings = {"output_dir": str(tmp_path)}
        job_queue = []
        workers = {}

    controller.attach(FakeOrch(), {"output_dir": str(tmp_path)}, pending=[])
    result = controller.add_paths([str(tmp_path / "missing.wav")])
    assert result["added"] == []
    assert result["skipped"][0]["reason"] == "not_a_file"
