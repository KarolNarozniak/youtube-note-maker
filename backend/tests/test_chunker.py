from backend.app.services.chunker import chunk_segments, estimate_tokens


def test_estimate_tokens_is_nonzero_for_text() -> None:
    assert estimate_tokens("hello") == 2
    assert estimate_tokens("") == 0


def test_chunk_segments_respects_boundaries_and_overlap() -> None:
    segments = [
        {"id": 1, "start": 0.0, "end": 5.0, "text": "a" * 120},
        {"id": 2, "start": 5.0, "end": 10.0, "text": "b" * 120},
        {"id": 3, "start": 10.0, "end": 15.0, "text": "c" * 120},
    ]

    chunks = chunk_segments(segments, target_tokens=50, overlap_tokens=20)

    assert len(chunks) == 3
    assert chunks[0].start_sec == 0.0
    assert chunks[1].segment_ids[0] == 1
    assert chunks[2].end_sec == 15.0


def test_empty_segments_produce_no_chunks() -> None:
    assert chunk_segments([]) == []
    assert chunk_segments([{"id": 1, "start": 0, "end": 1, "text": " "}]) == []
