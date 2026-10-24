"""Unit tests for Job model serialization."""

from handforge.core.models import Job


def test_job_defaults():
    job = Job(src="/a.wav", dst_dir="/out", format="mp3")
    assert job.mode == "CBR"
    assert job.copy_meta is True
    assert job.extract_audio_only is False
    assert job.reduce_size is False
    assert job.delete_original is False


def test_job_to_dict_from_dict_roundtrip():
    job = Job(
        src="/media/in.mkv",
        dst_dir="/media/out",
        format="mp4",
        mode="CBR",
        bitrate="192",
        reduce_size=True,
        size_reduction_factor=7.0,
        use_hevc=True,
        two_pass=False,
        video_quality_preset="high",
        audio_track=1,
        subtitle_track=3,
        meta_title="Title",
        meta_artist="Artist",
        trim_start=1.5,
        fade_in=0.1,
    )
    data = job.to_dict()
    assert data["src"] == "/media/in.mkv"
    assert data["reduce_size"] is True
    assert data["audio_track"] == 1

    restored = Job.from_dict(data)
    assert restored == job
    assert restored.to_dict() == data
