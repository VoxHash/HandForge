"""Crash-safe queue persistence under ~/.handforge/queue.json."""

from __future__ import annotations

import json
import os
from pathlib import Path

from handforge.core.models import Job
from handforge.core.queue_persist import (
    QUEUE_FILENAME,
    clear_queue_state,
    job_from_dict,
    jobs_for_restore,
    load_queue_state,
    persist_live_queue,
    save_queue_state,
)


def _job(src: str, fmt: str = "mp3") -> Job:
    return Job(src=src, dst_dir="/tmp/out", format=fmt, mode="CBR", bitrate="192")


def test_save_load_roundtrip(isolated_config_dir, tmp_path):
    media = tmp_path / "a.wav"
    media.write_bytes(b"RIFF")
    pending = [_job(str(media))]
    save_queue_state(pending=pending, session={"preset": "MP3 192k"})
    path = isolated_config_dir / QUEUE_FILENAME
    assert path.is_file()
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["version"] == 1
    assert len(raw["pending"]) == 1
    assert raw["session"]["preset"] == "MP3 192k"

    state = load_queue_state()
    assert len(state["pending"]) == 1
    assert state["pending"][0].src == str(media)
    assert state["pending"][0].format == "mp3"


def test_clear_when_empty(isolated_config_dir, tmp_path):
    media = tmp_path / "b.wav"
    media.write_bytes(b"x")
    save_queue_state(pending=[_job(str(media))])
    assert (isolated_config_dir / QUEUE_FILENAME).is_file()
    save_queue_state(pending=[], queued=[], active=[])
    assert not (isolated_config_dir / QUEUE_FILENAME).is_file()
    clear_queue_state()  # idempotent


def test_atomic_replace_leaves_valid_json(isolated_config_dir, tmp_path):
    media = tmp_path / "c.flac"
    media.write_bytes(b"fLaC")
    save_queue_state(pending=[_job(str(media), fmt="flac")])
    text = (isolated_config_dir / QUEUE_FILENAME).read_text(encoding="utf-8")
    json.loads(text)
    assert not (isolated_config_dir / (QUEUE_FILENAME + ".tmp")).exists()


def test_jobs_for_restore_dedupes_and_skips_missing(isolated_config_dir, tmp_path):
    good = tmp_path / "ok.wav"
    good.write_bytes(b"ok")
    missing = str(tmp_path / "gone.wav")
    state = {
        "pending": [_job(str(good))],
        "queued": [_job(str(good))],  # duplicate src
        "active": [_job(missing)],
        "session": {},
    }
    restored = jobs_for_restore(state, require_existing=True)
    assert len(restored) == 1
    assert os.path.realpath(restored[0].src) == os.path.realpath(str(good))


def test_job_from_dict_ignores_unknown_keys():
    job = job_from_dict(
        {
            "src": "/tmp/x.wav",
            "dst_dir": "/tmp/out",
            "format": "mp3",
            "mode": "CBR",
            "extra_future_field": 123,
        }
    )
    assert job is not None
    assert job.src == "/tmp/x.wav"
    assert job_from_dict({"format": "mp3"}) is None


def test_persist_live_queue_running_vs_idle(isolated_config_dir, tmp_path):
    media = tmp_path / "run.wav"
    media.write_bytes(b"ok")
    pending = [_job(str(media))]

    class FakeWorker:
        def __init__(self, job: Job):
            self.job = job

    class FakeOrch:
        def __init__(self):
            self.job_queue = [_job(str(media))]
            self.workers = {1: FakeWorker(_job(str(tmp_path / "active.wav")))}

    # Running: unfinished work in queued/active (pending list ignored)
    persist_live_queue(pending=pending, orchestrator=FakeOrch())
    state = load_queue_state()
    assert state["pending"] == []
    assert len(state["queued"]) == 1
    assert len(state["active"]) == 1

    # Idle: persist pending and clear file when empty
    class IdleOrch:
        job_queue = []
        workers = {}

    persist_live_queue(pending=pending, orchestrator=IdleOrch())
    state = load_queue_state()
    assert len(state["pending"]) == 1
    persist_live_queue(pending=[], orchestrator=IdleOrch())
    assert not (isolated_config_dir / QUEUE_FILENAME).is_file()
