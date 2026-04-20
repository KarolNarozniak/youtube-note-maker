from types import SimpleNamespace

from backend.app.services.chunker import TranscriptChunk
from backend.app.services.ingest import IngestionPipeline


def test_write_chunks_file_creates_chunks_directory(tmp_path) -> None:
    pipeline = SimpleNamespace(settings=SimpleNamespace(chunks_dir=tmp_path / "data" / "chunks"))
    chunks = [
        TranscriptChunk(
            chunk_index=0,
            text="Hello world",
            start_sec=0.0,
            end_sec=1.0,
            token_estimate=2,
            segment_ids=[0],
        )
    ]

    IngestionPipeline._write_chunks_file(pipeline, "video123", chunks)

    chunk_file = tmp_path / "data" / "chunks" / "video123.json"
    assert chunk_file.exists()
