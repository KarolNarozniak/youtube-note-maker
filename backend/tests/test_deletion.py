from backend.app.config import Settings
from backend.app.services.deletion import delete_audio_artifacts, delete_source_artifacts


def make_settings(tmp_path):
    return Settings(
        repo_root=tmp_path,
        host="127.0.0.1",
        port=2002,
        frontend_host="127.0.0.1",
        frontend_port=2001,
        docs_host="127.0.0.1",
        docs_port=2003,
        data_dir=tmp_path / "data",
        db_path=tmp_path / "data" / "app.db",
        audio_dir=tmp_path / "data" / "audio",
        transcript_dir=tmp_path / "data" / "transcripts",
        chunks_dir=tmp_path / "data" / "chunks",
        qdrant_url="http://localhost:2004",
        qdrant_collection="test",
        ollama_url="http://localhost:11434",
        ollama_embed_model="embeddinggemma",
        whisper_model="turbo",
        whisper_device="cpu",
        downloader_timeout_sec=10,
        downloader_project=tmp_path / "downloader.csproj",
        downloader_dll=tmp_path / "downloader.dll",
        chunk_target_tokens=900,
        chunk_overlap_tokens=150,
    )


def test_delete_audio_artifacts_removes_video_audio_dir(tmp_path) -> None:
    settings = make_settings(tmp_path)
    audio_dir = settings.audio_dir / "video1"
    audio_dir.mkdir(parents=True)
    audio_file = audio_dir / "video1.m4a"
    audio_file.write_text("audio", encoding="utf-8")

    delete_audio_artifacts(settings, video_id="video1", audio_path=audio_file)

    assert not audio_file.exists()
    assert not audio_dir.exists()


def test_delete_source_artifacts_removes_transcripts_chunks_and_audio(tmp_path) -> None:
    settings = make_settings(tmp_path)
    audio_dir = settings.audio_dir / "video1"
    transcript_dir = settings.transcript_dir / "video1"
    audio_dir.mkdir(parents=True)
    transcript_dir.mkdir(parents=True)
    settings.chunks_dir.mkdir(parents=True)

    audio_file = audio_dir / "video1.m4a"
    json_file = transcript_dir / "video1.json"
    txt_file = transcript_dir / "video1.txt"
    srt_file = transcript_dir / "video1.srt"
    chunk_file = settings.chunks_dir / "video1.json"
    for path in [audio_file, json_file, txt_file, srt_file, chunk_file]:
        path.write_text("x", encoding="utf-8")

    delete_source_artifacts(
        settings,
        [
            {
                "id": "video1",
                "audio_path": str(audio_file),
                "transcript_json_path": str(json_file),
                "transcript_txt_path": str(txt_file),
                "transcript_srt_path": str(srt_file),
            }
        ],
    )

    for path in [audio_file, json_file, txt_file, srt_file, chunk_file]:
        assert not path.exists()
