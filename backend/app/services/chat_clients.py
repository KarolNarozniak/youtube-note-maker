from __future__ import annotations

from typing import Any

import httpx


class OllamaChatClient:
    def __init__(self, *, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            payload = response.json()
        return [item["name"] for item in payload.get("models", []) if item.get("name")]

    async def chat(self, *, model: str, messages: list[dict[str, str]]) -> str:
        async with httpx.AsyncClient(timeout=600) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
            )
            response.raise_for_status()
            payload = response.json()
        content = payload.get("message", {}).get("content")
        if not content:
            raise RuntimeError("Ollama returned an empty chat response.")
        return str(content)


class OpenAIResponsesClient:
    def __init__(self, *, api_key: str, base_url: str = "https://api.openai.com/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    @staticmethod
    def build_payload(*, model: str, messages: list[dict[str, str]]) -> dict[str, Any]:
        return {"model": model, "input": messages}

    async def chat(self, *, model: str, messages: list[dict[str, str]]) -> str:
        async with httpx.AsyncClient(timeout=600) as client:
            response = await client.post(
                f"{self.base_url}/responses",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=self.build_payload(model=model, messages=messages),
            )
            response.raise_for_status()
            payload = response.json()
        return parse_openai_response_text(payload)


def parse_openai_response_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    parts: list[str] = []
    for item in payload.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                parts.append(str(content["text"]))
    text = "\n".join(parts).strip()
    if not text:
        raise RuntimeError("OpenAI returned an empty response.")
    return text
