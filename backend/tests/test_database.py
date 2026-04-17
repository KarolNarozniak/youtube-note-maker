from backend.app.database import Database


def test_delete_source_removes_source_videos_and_chunks(tmp_path) -> None:
    db = Database(tmp_path / "app.db")
    db.init()
    job = db.create_job(url="https://youtu.be/example", language=None, whisper_model="turbo", force=False)
    db.upsert_source(
        {
            "id": "source1",
            "type": "video",
            "url": "https://youtu.be/example",
            "title": "Example",
            "job_id": job["id"],
            "video_count": 1,
        }
    )
    db.upsert_video(
        {
            "id": "video1",
            "source_id": "source1",
            "youtube_id": "example",
            "url": "https://youtu.be/example",
            "title": "Example",
            "status": "completed",
        }
    )
    db.insert_chunks(
        [
            {
                "id": "point1",
                "video_id": "video1",
                "source_id": "source1",
                "chunk_index": 0,
                "text": "hello",
                "start_sec": 0,
                "end_sec": 1,
                "token_estimate": 2,
                "qdrant_point_id": "point1",
                "embedding_model": "embeddinggemma",
            }
        ]
    )

    db.delete_source("source1")

    assert db.get_source("source1") is None
    assert db.list_videos_for_source("source1") == []
    assert db.get_chunks_for_video("video1", "embeddinggemma") == []
