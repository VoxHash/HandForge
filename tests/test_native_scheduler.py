"""Tests for adaptive parallel scheduling (Rust + Python fallback)."""

from handforge.core.native_scheduler import (
    estimate_job_rss_mb,
    native_available,
    recommend_parallel,
    recommend_parallel_from_metrics,
    system_snapshot,
)


def test_metrics_respect_user_max():
    n = recommend_parallel_from_metrics(2, 0, 350, 32768, 30000, 16, 50)
    assert n == 2


def test_metrics_tight_memory():
    n = recommend_parallel_from_metrics(8, 0, 350, 2048, 900, 8, 100)
    assert n == 1


def test_metrics_high_load_cuts_cap():
    low = recommend_parallel_from_metrics(16, 0, 64, 65536, 60000, 8, 50)
    high = recommend_parallel_from_metrics(16, 0, 64, 65536, 60000, 8, 800)
    assert high <= low
    assert high <= 4


def test_recommend_parallel_returns_positive():
    n = recommend_parallel(user_max=4, active_jobs=0, avg_job_rss_mb=350)
    assert 1 <= n <= 4


def test_system_snapshot_shape():
    snap = system_snapshot(user_max=2)
    assert snap["recommended_parallel"] >= 1
    assert snap["total_mem_mb"] > 0
    assert snap["backend"] in ("rust", "python")
    if native_available():
        assert snap["backend"] == "rust"
        assert snap["lib_path"]


def test_estimate_job_rss_mb():
    assert estimate_job_rss_mb(is_video=True) == 500
    assert estimate_job_rss_mb(is_video=False) == 180


def test_metrics_zero_user_max_clamped():
    n = recommend_parallel_from_metrics(0, 0, 350, 16384, 8000, 8, 50)
    assert n >= 1


def test_active_jobs_increase_capacity():
    # With active jobs, capacity_mb includes their RSS so we do not starve further slots
    # when memory is already allocated to running workers.
    idle = recommend_parallel_from_metrics(8, 0, 350, 8192, 2000, 8, 50)
    busy = recommend_parallel_from_metrics(8, 4, 350, 8192, 2000, 8, 50)
    assert busy >= idle
