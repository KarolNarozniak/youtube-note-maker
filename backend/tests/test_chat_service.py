from backend.app.services.chat import (
    build_chat_context,
    build_model_messages,
    citation_from_qdrant,
    filters_for_context_item,
    make_title,
)


def test_filters_for_context_item_scopes_chat_context() -> None:
    assert filters_for_context_item("conv", {"id": "ctx", "type": "manual"}) == {
        "scope": "chat",
        "conversation_id": "conv",
        "context_item_id": "ctx",
    }
    assert filters_for_context_item("conv", {"type": "source", "source_id": "src"}) == {
        "source_id": "src"
    }


def test_citation_from_qdrant_is_api_ready() -> None:
    citation = citation_from_qdrant(
        1,
        {
            "score": 0.8,
            "payload": {
                "title": "Video",
                "text": "quoted text",
                "url": "https://example.com",
                "source_id": "source",
            },
        },
    )

    assert citation["index"] == 1
    assert citation["title"] == "Video"
    assert citation["score"] == 0.8


def test_build_model_messages_includes_context_and_history() -> None:
    citations = [{"index": 1, "title": "Doc", "url": "https://example.com", "text": "source text"}]
    messages = build_model_messages(
        user_text="Question?",
        history=[
            {"role": "user", "text": "Earlier question"},
            {"role": "assistant", "text": "Earlier answer"},
            {"role": "user", "text": "Question?"},
        ],
        citations=citations,
    )

    assert messages[0]["role"] == "system"
    assert "Retrieved context" in messages[1]["content"]
    assert messages[-1] == {"role": "user", "content": "Question?"}
    assert "[1] Doc" in build_chat_context(citations)


def test_make_title_is_short() -> None:
    assert make_title("What does the speaker say about retrieval augmented generation?") == (
        "What does the speaker say about retrieval augmented"
    )
