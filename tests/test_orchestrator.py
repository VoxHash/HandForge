"""Unit tests for Orchestrator adaptive concurrency (no full encode)."""

from __future__ import annotations

from handforge.core.models import Job
from handforge.core.orchestrator import Orchestrator


def test_effective_max_parallel_respects_user_ceiling(qapp, monkeypatch):
    orch = Orchestrator(max_parallel=8)
    orch.set_settings({"parallel": 3, "adaptive_parallel": True})

    monkeypatch.setattr(
        "handforge.core.orchestrator.recommend_parallel",
        lambda user_max, active, avg: min(user_max, 99),
    )
    assert orch._effective_max_parallel() == 3


def test_adaptive_parallel_can_lower_concurrency(qapp, monkeypatch):
    orch = Orchestrator(max_parallel=8)
    orch.set_settings({"parallel": 8, "adaptive_parallel": True})
    monkeypatch.setattr(
        "handforge.core.orchestrator.recommend_parallel",
        lambda user_max, active, avg: 2,
    )
    assert orch._effective_max_parallel() == 2


def test_adaptive_parallel_disabled_uses_user_max(qapp, monkeypatch):
    orch = Orchestrator(max_parallel=4)
    orch.set_settings({"parallel": 4, "adaptive_parallel": False})
    called = {"n": 0}

    def boom(*_a, **_k):
        called["n"] += 1
        return 1

    monkeypatch.setattr("handforge.core.orchestrator.recommend_parallel", boom)
    assert orch._effective_max_parallel() == 4
    assert called["n"] == 0


def test_estimate_rss_from_queued_video(qapp, monkeypatch):
    orch = Orchestrator()
    orch.set_settings({"parallel": 4, "adaptive_parallel": True})
    orch.job_queue = [
        Job(src="/tmp/clip.mp4", dst_dir="/tmp/out", format="mp4"),
    ]
    seen = {}

    def capture(user_max, active, avg):
        seen["avg"] = avg
        return user_max

    monkeypatch.setattr("handforge.core.orchestrator.recommend_parallel", capture)
    assert orch._effective_max_parallel() == 4
    # estimate_job_rss_mb(is_video=True) -> 500
    assert seen["avg"] == 500


def test_estimate_rss_from_queued_audio(qapp, monkeypatch):
    orch = Orchestrator()
    orch.set_settings({"parallel": 4, "adaptive_parallel": True})
    orch.job_queue = [
        Job(src="/tmp/song.flac", dst_dir="/tmp/out", format="mp3"),
    ]
    seen = {}

    def capture(user_max, active, avg):
        seen["avg"] = avg
        return user_max

    monkeypatch.setattr("handforge.core.orchestrator.recommend_parallel", capture)
    orch._effective_max_parallel()
    assert seen["avg"] == 180


def test_enqueue_starts_worker_for_missing_source(qapp, tmp_path):
    """Worker should fail cleanly when the source path does not exist."""
    orch = Orchestrator(max_parallel=1)
    orch.set_settings({"parallel": 1, "adaptive_parallel": False, "on_exists": "overwrite"})

    results = []

    def on_done(wid, success, message, output_path):
        results.append((wid, success, message, output_path))

    orch.sig_worker_done.connect(on_done)
    missing = str(tmp_path / "does-not-exist.wav")
    orch.enqueue(
        [Job(src=missing, dst_dir=str(tmp_path / "out"), format="mp3", bitrate="128")]
    )

    # Wait for the worker thread to finish
    from PyQt6.QtCore import QCoreApplication
    import time

    deadline = time.time() + 10
    while not results and time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.05)

    assert results, "worker did not signal completion"
    wid, success, message, _out = results[0]
    assert success is False
    assert "not found" in message.lower() or "Source file" in message
    assert wid == 1
