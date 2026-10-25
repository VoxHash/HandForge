"""Tests for companion remote queue status API and serialization."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

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

    # Real Orchestrator removes the worker before emitting sig_worker_done
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
    server = CompanionServer(hub, host="127.0.0.1", port=0, token=token)
    # ThreadingHTTPServer with port 0 picks an ephemeral port after start
    server.port = 0
    # Bind explicitly via start — override by constructing httpd; use fixed high port
    import socket

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    server = CompanionServer(hub, host="127.0.0.1", port=port, token=token)
    server.start()
    try:
        url = companion_url("127.0.0.1", port, token)
        assert f"token={token}" in url

        # Unauthorized without token
        with pytest.raises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=2)
        assert err.value.code == 401

        # Health is open
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/health", timeout=2
        ) as resp:
            health = json.loads(resp.read().decode("utf-8"))
        assert health["ok"] is True
        assert health["auth_required"] is True

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/status?token={token}", timeout=2
        ) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        assert data["counts"]["queued"] == 1
        assert data["queued"][0]["file"] == "a.wav"

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/?token={token}", timeout=2
        ) as resp:
            html = resp.read().decode("utf-8")
        assert "HandForge" in html
        assert "Active conversions" in html
    finally:
        server.stop()


def test_progress_is_monotonic_in_hub():
    hub = QueueStatusHub()
    hub.on_started(1, "/tmp/x.wav")
    hub.on_progress(1, 50.0, 1.0, 1.0, "1x")
    hub.on_progress(1, 40.0, 1.2, 1.0, "1x")  # regressive sample ignored for %
    snap = hub.snapshot()
    # No orch attached → active comes from hub cache
    assert snap["active"][0]["progress"] == pytest.approx(50.0)
