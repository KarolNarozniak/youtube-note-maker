from backend.app.services.artifacts import format_srt_time, render_srt, write_transcript_artifacts


def test_srt_time_format() -> None:
    assert format_srt_time(65.432) == "00:01:05,432"


def test_writes_transcript_artifacts(tmp_path) -> None:
    result = {
        "language": "en",
        "text": "Hello world.",
        "segments": [{"id": 0, "start": 0.0, "end": 1.25, "text": " Hello world. "}],
    }

    artifact = write_transcript_artifacts(
        video_id="video1",
        result=result,
        output_dir=tmp_path,
        metadata={"title": "Example"},
    )

    assert artifact.json_path.exists()
    assert artifact.txt_path.read_text(encoding="utf-8").strip() == "Hello world."
    assert "00:00:01,250" in artifact.srt_path.read_text(encoding="utf-8")


def test_render_srt_empty() -> None:
    assert render_srt([]) == ""
