from backend.app.services.vector_store import build_filter


def test_build_filter_uses_allowed_payload_fields_only() -> None:
    qdrant_filter = build_filter(
        {
            "source_id": "src",
            "video_id": "",
            "unknown": "ignored",
            "language": "en",
        }
    )

    assert qdrant_filter == {
        "must": [
            {"key": "source_id", "match": {"value": "src"}},
            {"key": "language", "match": {"value": "en"}},
        ]
    }
