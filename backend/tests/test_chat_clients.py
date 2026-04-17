from backend.app.services.chat_clients import OpenAIResponsesClient, parse_openai_response_text


def test_openai_payload_uses_responses_input_messages() -> None:
    payload = OpenAIResponsesClient.build_payload(
        model="gpt-5.4",
        messages=[{"role": "user", "content": "hello"}],
    )

    assert payload == {"model": "gpt-5.4", "input": [{"role": "user", "content": "hello"}]}


def test_parse_openai_response_text_prefers_output_text() -> None:
    assert parse_openai_response_text({"output_text": "answer"}) == "answer"


def test_parse_openai_response_text_falls_back_to_output_content() -> None:
    text = parse_openai_response_text(
        {
            "output": [
                {
                    "content": [
                        {"type": "output_text", "text": "hello"},
                        {"type": "output_text", "text": "world"},
                    ]
                }
            ]
        }
    )

    assert text == "hello\nworld"
