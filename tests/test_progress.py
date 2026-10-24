"""Tests for parallel-safe progress tracking."""

from handforge.core.progress import (
    ProgressTracker,
    batch_progress_with_eta,
    eta_from_speed,
    ewma,
    parse_duration,
    parse_out_time,
    parse_speed,
    progress_percent,
)


def test_parse_duration_and_time():
    assert parse_duration("  Duration: 00:01:30.50, start:") == 90.5
    assert parse_out_time("frame= 10 time=00:00:15.25 bitrate=100kbits/s") == 15.25
    assert parse_speed("speed=1.25x") == 1.25
    assert parse_speed("speed=N/A") is None


def test_progress_percent_clamped():
    assert progress_percent(50, 100) == 50.0
    assert progress_percent(200, 100) == 99.0
    assert progress_percent(0, 0) == 0.0


def test_eta_uses_speed():
    # 50s media left at 2x => 25s wall clock
    assert abs(eta_from_speed(50, 100, 2.0) - 25.0) < 1e-6
    # Without speed, fall back to remaining media time
    assert abs(eta_from_speed(50, 100, None) - 50.0) < 1e-6


def test_ewma_smoothing():
    assert ewma(0.0, 10.0, 1.0) == 10.0
    assert ewma(10.0, 20.0, 0.0) == 10.0
    assert abs(ewma(0.0, 10.0, 0.3) - 3.0) < 1e-6


def test_tracker_monotonic_and_throttle():
    t = ProgressTracker(ewma_alpha=1.0, min_emit_interval=1.0, min_progress_delta=0.5)
    t.note_duration(100.0)
    s1 = t.update_from_line("time=00:00:10.00 speed=1.00x", elapsed=1.0, now=1.0)
    assert s1.emitted
    assert abs(s1.progress - 10.0) < 1e-6
    # Second line within throttle window with tiny change — should not emit
    s2 = t.update_from_line("time=00:00:10.20 speed=1.00x", elapsed=1.1, now=1.1)
    assert not s2.emitted
    # Regression in time= must not lower display progress
    s3 = t.update_from_line("time=00:00:05.00 speed=1.00x", elapsed=2.0, now=3.0)
    assert s3.progress >= 10.0


def test_keepalive_does_not_overwrite_real_progress():
    t = ProgressTracker(ewma_alpha=1.0)
    t.note_duration(100.0)
    t.update_from_line("time=00:00:40.00 speed=0.50x", elapsed=5.0, now=1.0)
    assert t.last_display_progress >= 39.0
    keep = t.keepalive(elapsed=10.0, now=10.0)
    assert not keep.emitted
    assert keep.progress >= 39.0


def test_keepalive_before_real_progress():
    t = ProgressTracker()
    keep = t.keepalive(elapsed=5.0, now=5.0)
    assert keep.emitted
    assert keep.progress == 0.1


def test_eta_speed_aware_in_tracker():
    t = ProgressTracker(ewma_alpha=1.0, min_emit_interval=0.0)
    t.note_duration(100.0)
    sample = t.update_from_line("time=00:00:50.00 speed=2.00x", elapsed=10.0, now=1.0)
    # 50s remaining media / 2x = 25s ETA
    assert abs(sample.eta - 25.0) < 0.01


def test_batch_progress_parallel_aggregate():
    workers = {
        1: {"progress": 50.0, "eta": 20.0, "status": "Running"},
        2: {"progress": 100.0, "eta": 0.0, "status": "Done"},
        3: {"progress": 25.0, "eta": 40.0, "status": "Running"},
    }
    overall, batch_eta = batch_progress_with_eta(workers, queued=2)
    # (50+100+25+0+0) / 5 = 35
    assert abs(overall - 35.0) < 1e-6
    # max running ETA 40 + 1 wave * mean(20,40)=30 => 70
    assert batch_eta >= 40.0


def test_force_complete():
    t = ProgressTracker()
    sample = t.force_complete(12.5, "1.10x")
    assert sample.progress == 100.0
    assert sample.eta == 0.0
    assert sample.emitted
