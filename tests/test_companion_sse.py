"""Companion Server-Sent Events live status stream."""

from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from handforge.companion.server import CompanionServer
from handforge.companion.status import QueueStatusHub
from handforge.core.models import Job


def _free_port() -> int:
    import socket

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def test_hub_subscribe_notify_wakes_subscriber():
    hub = QueueStatusHub()
    q = hub.subscribe()
    # Initial version
    assert q.get(timeout=1) == 0
    hub.notify(force=True)
    assert q.get(timeout=1) == 1
    hub.unsubscribe(q)


def test_sse_requires_token_when_configured():
    hub = QueueStatusHub()
    port = _free_port()
    server = CompanionServer(hub, host="127.0.0.1", port=port, token="secret-sse")
    server.start()
    try:
        url = f"http://127.0.0.1:{port}/api/events"
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(url, timeout=2)
        assert exc.value.code == 401
    finally:
        server.stop()


def test_sse_streams_status_event_and_updates():
    hub = QueueStatusHub()
    hub.attach(
        None,
        pending_provider=lambda: [
            Job(src="/tmp/media/track.wav", dst_dir="/tmp/out", format="mp3")
        ],
        app_label="SSETest",
    )
    port = _free_port()
    token = "live-token"
    server = CompanionServer(hub, host="127.0.0.1", port=port, token=token)
    server.start()
    received: list = []
    error: list = []

    def _reader() -> None:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/events?token={token}",
            headers={"Accept": "text/event-stream"},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                assert "text/event-stream" in (resp.headers.get("Content-Type") or "")
                buf = ""
                deadline = time.time() + 4.0
                while time.time() < deadline and len(received) < 2:
                    chunk = resp.read(256)
                    if not chunk:
                        break
                    buf += chunk.decode("utf-8", errors="replace")
                    while "\n\n" in buf:
                        block, buf = buf.split("\n\n", 1)
                        if block.startswith(":"):
                            continue
                        event = "message"
                        data_lines = []
                        for line in block.splitlines():
                            if line.startswith("event:"):
                                event = line[6:].strip()
                            elif line.startswith("data:"):
                                data_lines.append(line[5:].lstrip())
                        if event == "status" and data_lines:
                            received.append(json.loads("\n".join(data_lines)))
                            if len(received) == 1:
                                # Trigger a second push after first snapshot
                                hub.notify(force=True)
        except Exception as exc:  # noqa: BLE001
            error.append(exc)

    thread = threading.Thread(target=_reader, daemon=True)
    thread.start()
    thread.join(timeout=6)
    server.stop()
    assert not error, error[0]
    assert len(received) >= 1
    assert received[0]["app"] == "SSETest"
    assert received[0]["live"] == "sse"
    assert received[0]["counts"]["pending"] == 1
    assert "version" in received[0]
    if len(received) >= 2:
        assert received[1]["version"] >= received[0]["version"]
