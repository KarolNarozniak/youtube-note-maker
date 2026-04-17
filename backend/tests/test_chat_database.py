from backend.app.database import Database


def test_conversation_message_context_crud(tmp_path) -> None:
    db = Database(tmp_path / "app.db")
    db.init()

    conversation = db.create_conversation(
        title="New conversation",
        model_provider="ollama",
        model_id="qwen3:30b",
    )
    context = db.create_context_item(
        conversation_id=conversation["id"],
        item_type="manual",
        title="Note",
        text="important context",
        status="completed",
    )
    message = db.create_message(
        conversation_id=conversation["id"],
        role="assistant",
        text="answer",
        citations=[{"index": 1, "title": "Note", "text": "important context", "score": 0.9}],
        model_provider="ollama",
        model_id="qwen3:30b",
    )

    detail = db.get_conversation(conversation["id"])
    assert detail is not None
    assert db.list_context_items(conversation["id"])[0]["id"] == context["id"]
    assert db.list_messages(conversation["id"])[0]["citations"][0]["title"] == "Note"
    assert db.get_message(message["id"]) is not None

    db.delete_conversation(conversation["id"])

    assert db.get_conversation(conversation["id"]) is None
    assert db.list_context_items(conversation["id"]) == []
    assert db.list_messages(conversation["id"]) == []
