from backend.app.services.search_format import build_context, qdrant_results_to_search_results


def test_formats_qdrant_results_into_context() -> None:
    raw = [
        {
            "score": 0.9,
            "payload": {
                "text": "Important sentence.",
                "source_id": "source",
                "video_id": "video",
                "title": "A Video",
                "url": "https://youtu.be/example",
                "start_sec": 61,
                "end_sec": 72,
                "chunk_index": 2,
            },
        }
    ]

    results = qdrant_results_to_search_results(raw)
    context = build_context(results)

    assert results[0]["score"] == 0.9
    assert "[1] A Video (1:01-1:12)" in context
    assert "Important sentence." in context
