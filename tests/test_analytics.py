"""Unit tests for opt-in local performance analytics."""

from __future__ import annotations

import json
import time

import pytest

from handforge.util import analytics as analytics_mod


def test_analytics_enabled_default_off():
    assert analytics_mod.analytics_enabled(None) is False
    assert analytics_mod.analytics_enabled({}) is False
    assert analytics_mod.analytics_enabled({"performance_analytics": False}) is False
    assert analytics_mod.analytics_enabled({"performance_analytics": True}) is True


def test_parse_speed_variants():
    assert analytics_mod._parse_speed("1.5x") == pytest.approx(1.5)
    assert analytics_mod._parse_speed("2.00X") == pytest.approx(2.0)
    assert analytics_mod._parse_speed(3) == pytest.approx(3.0)
    assert analytics_mod._parse_speed("?") is None
    assert analytics_mod._parse_speed("n/a") is None
    assert analytics_mod._parse_speed(None) is None


def test_batch_session_collects_real_metrics(tmp_path, monkeypatch):
    monkeypatch.setattr(analytics_mod, "get_config_dir", lambda: tmp_path)

    src = tmp_path / "in.wav"
    src.write_bytes(b"x" * 2048)
    out = tmp_path / "out.flac"
    out.write_bytes(b"y" * 4096)

    session = analytics_mod.BatchAnalyticsSession.start(
        {"parallel": 2, "adaptive_parallel": True, "performance_analytics": True}
    )
    session.on_started(1, str(src))
    session.note_parallel(1)
    session.on_progress(1, 25.0, 1.0, 3.0, "1.2x")
    time.sleep(0.05)
    session.on_progress(1, 60.0, 2.0, 1.5, "1.8x")
    session.on_started(2, str(src))
    session.note_parallel(2)
    session.on_done(1, True, "ok", str(out))
    session.note_parallel(1)
    session.on_progress(2, 40.0, 0.5, 2.0, "0.9x")
    session.on_done(2, False, "fail", "")
    session.note_parallel(0)

    summary = session.finish(persist=True)
    assert summary.job_count == 2
    assert summary.succeeded == 1
    assert summary.failed == 1
    assert summary.peak_parallel == 2
    assert summary.parallel_setting == 2
    assert summary.adaptive_parallel is True
    assert summary.mean_speed_x is not None
    assert summary.peak_speed_x is not None
    assert summary.peak_speed_x >= summary.mean_speed_x
    assert summary.total_bytes_out == 4096
    assert summary.total_bytes_in >= 2048
    assert summary.throughput_bps is not None
    assert summary.eta_mae_seconds is not None
    assert summary.wall_seconds >= 0.0

    path = analytics_mod.batches_path(tmp_path)
    assert path.exists()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    stored = json.loads(lines[0])
    assert stored["batch_id"] == summary.batch_id
    assert stored["peak_parallel"] == 2

    text = analytics_mod.format_batch_summary(summary, detailed=True)
    assert "peak_parallel=2" in text
    assert "LOCAL" not in text or "local" in text.lower()
    assert str(path) in text or "batches.jsonl" in text

    oneline = analytics_mod.format_summary_oneline(summary)
    assert "Analytics:" in oneline
    assert "peak∥2" in oneline


def test_append_trims_to_max(tmp_path, monkeypatch):
    monkeypatch.setattr(analytics_mod, "get_config_dir", lambda: tmp_path)

    for i in range(5):
        session = analytics_mod.BatchAnalyticsSession.start({"parallel": 1})
        session.on_started(1, f"/tmp/f{i}.wav")
        session.on_done(1, True, "ok", "")
        summary = session.summarize()
        analytics_mod.append_batch_summary(summary, config_dir=tmp_path, max_batches=3)

    recent = analytics_mod.load_recent_batches(limit=10, config_dir=tmp_path)
    assert len(recent) == 3


def test_format_analytics_status_mentions_local_only(tmp_path, monkeypatch):
    monkeypatch.setattr(analytics_mod, "get_config_dir", lambda: tmp_path)
    status = analytics_mod.format_analytics_status({"performance_analytics": False})
    assert "LOCAL ONLY" in status
    assert "Enabled: no" in status
    status_on = analytics_mod.format_analytics_status({"performance_analytics": True})
    assert "Enabled: yes" in status_on


def test_job_eta_mae_and_throughput():
    job = analytics_mod.JobRecord(wid=1, src="/a.wav")
    job.started_at = 100.0
    job.ended_at = 110.0
    job.wall_seconds = 10.0
    job.bytes_out = 1000
    job.eta_forecasts = [(100.0, 12.0), (105.0, 4.0)]  # predicted ends 112 and 109
    # abs(112-110)=2, abs(109-110)=1 → mae=1.5
    assert job.eta_mae_seconds() == pytest.approx(1.5)
    assert job.throughput_bps() == pytest.approx(100.0)


def test_settings_default_merges_performance_analytics(monkeypatch, tmp_path):
    from handforge.core import settings as settings_mod

    monkeypatch.setattr(settings_mod, "get_config_dir", lambda: tmp_path)
    (tmp_path / "settings.json").write_text("{}", encoding="utf-8")
    loaded = settings_mod.load_settings()
    assert loaded.get("performance_analytics") is False
    assert loaded.get("watchfolder_enabled") is False


def test_build_aggregate_report(tmp_path, monkeypatch):
    monkeypatch.setattr(analytics_mod, "get_config_dir", lambda: tmp_path)
    empty = analytics_mod.build_aggregate_report(limit=10, config_dir=tmp_path)
    assert empty["ok"] is True
    assert empty["batch_count"] == 0
    assert empty["local_only"] is True

    for i in range(2):
        session = analytics_mod.BatchAnalyticsSession.start(
            {"parallel": 2, "adaptive_parallel": True, "performance_analytics": True}
        )
        session.on_started(1, str(tmp_path / f"in{i}.wav"))
        session.on_progress(1, 50.0, 1.0, 1.0, "1.5x")
        session.on_done(1, True, "ok", str(tmp_path / f"out{i}.mp3"))
        session.finish(persist=True)

    report = analytics_mod.build_aggregate_report(limit=10, config_dir=tmp_path)
    assert report["batch_count"] == 2
    assert report["jobs_ok"] == 2
    assert report["success_rate"] == pytest.approx(1.0)
    text = analytics_mod.format_aggregate_report(report, detailed=True)
    assert "LOCAL ONLY" in text
    assert "batches=2" in text
