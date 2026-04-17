from __future__ import annotations

from typing import Any

from backend.app.config import Settings
from backend.app.database import Database
from backend.app.services.chat_clients import OllamaChatClient, OpenAIResponsesClient
from backend.app.services.embeddings import OllamaEmbeddingClient
from backend.app.services.text_context import chunk_text, fetch_web_page_text
from backend.app.services.vector_store import QdrantVectorStore
from backend.app.services.youtube import stable_point_id


LOCAL_MODEL_PRESETS = ["qwen3:30b", "deepseek-r1:8b"]
OPENAI_MODEL_PRESETS = ["gpt-5.4", "gpt-5.4-mini", "gpt-5.3-chat-latest"]


class ChatService:
    def __init__(
        self,
        *,
        settings: Settings,
        db: Database,
        embedder: OllamaEmbeddingClient,
        vector_store: QdrantVectorStore,
    ) -> None:
        self.settings = settings
        self.db = db
        self.embedder = embedder
        self.vector_store = vector_store

    async def add_context(self, conversation_id: str, request: Any) -> dict[str, Any]:
        if request.type == "source":
            source = self.db.get_source(request.source_id or "")
            if source is None:
                raise ValueError("Source not found.")
            return self.db.create_context_item(
                conversation_id=conversation_id,
                item_type="source",
                title=request.title or source["title"],
                source_id=source["id"],
                playlist_id=source.get("playlist_id"),
                status="completed",
            )

        if request.type == "video":
            video = self.db.get_video(request.video_id or "")
            if video is None:
                raise ValueError("Video not found.")
            return self.db.create_context_item(
                conversation_id=conversation_id,
                item_type="video",
                title=request.title or video["title"],
                url=video["url"],
                video_id=video["id"],
                playlist_id=video.get("playlist_id"),
                status="completed",
            )

        if request.type == "playlist":
            title = request.title or request.playlist_id or "Playlist"
            return self.db.create_context_item(
                conversation_id=conversation_id,
                item_type="playlist",
                title=title,
                playlist_id=request.playlist_id,
                status="completed",
            )

        if request.type == "manual":
            if not request.text or not request.text.strip():
                raise ValueError("Manual context text is required.")
            item = self.db.create_context_item(
                conversation_id=conversation_id,
                item_type="manual",
                title=request.title or "Manual note",
                text=request.text.strip(),
                status="processing",
            )
            try:
                return await self._embed_context_item(item, title=item["title"], text=item["text"], url=None)
            except Exception as exc:
                self.db.update_context_item(item["id"], status="failed", error=str(exc))
                return self.db.get_context_item(item["id"]) or item

        if request.type == "web":
            if not request.url or not request.url.strip():
                raise ValueError("Web URL is required.")
            item = self.db.create_context_item(
                conversation_id=conversation_id,
                item_type="web",
                title=request.title or request.url,
                url=request.url.strip(),
                status="processing",
            )
            try:
                page = await fetch_web_page_text(request.url.strip())
                self.db.update_context_item(item["id"], title=request.title or page.title, text=page.text)
                item = self.db.get_context_item(item["id"]) or item
                return await self._embed_context_item(
                    item,
                    title=request.title or page.title,
                    text=page.text,
                    url=request.url.strip(),
                )
            except Exception as exc:
                self.db.update_context_item(item["id"], status="failed", error=str(exc))
                return self.db.get_context_item(item["id"]) or item

        raise ValueError("Unsupported context item type.")

    async def delete_context_item(self, item: dict[str, Any]) -> None:
        if item["type"] in {"manual", "web"}:
            await self.vector_store.delete_by_filter({"context_item_id": item["id"]})
        self.db.delete_context_item(item["id"])

    async def delete_conversation(self, conversation_id: str) -> None:
        await self.vector_store.delete_by_filter(
            {"scope": "chat", "conversation_id": conversation_id}
        )
        self.db.delete_conversation(conversation_id)

    async def send_message(
        self,
        *,
        conversation: dict[str, Any],
        text: str,
        model_provider: str,
        model_id: str,
        api_key: str | None,
        top_k: int,
    ) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
        user_message = self.db.create_message(
            conversation_id=conversation["id"],
            role="user",
            text=text,
        )
        citations = await self.retrieve_context(conversation_id=conversation["id"], query=text, top_k=top_k)
        messages = build_model_messages(
            user_text=text,
            history=self.db.list_messages(conversation["id"]),
            citations=citations,
        )

        if model_provider == "ollama":
            answer = await OllamaChatClient(base_url=self.settings.ollama_url).chat(
                model=model_id,
                messages=messages,
            )
        elif model_provider == "openai":
            if not api_key:
                raise ValueError("OpenAI API key is required for online models.")
            answer = await OpenAIResponsesClient(api_key=api_key).chat(
                model=model_id,
                messages=messages,
            )
        else:
            raise ValueError("Unsupported model provider.")

        assistant_message = self.db.create_message(
            conversation_id=conversation["id"],
            role="assistant",
            text=answer,
            citations=citations,
            model_provider=model_provider,
            model_id=model_id,
        )
        maybe_title = make_title(text)
        if conversation["title"] == "New conversation" and maybe_title:
            self.db.touch_conversation(conversation["id"], title=maybe_title)
        return user_message, assistant_message, citations

    async def retrieve_context(self, *, conversation_id: str, query: str, top_k: int) -> list[dict[str, Any]]:
        items = [
            item
            for item in self.db.list_context_items(conversation_id)
            if item["status"] == "completed"
        ]
        if not items:
            return []

        query_vector = (await self.embedder.embed_texts([query]))[0]
        all_results: dict[str, dict[str, Any]] = {}
        for item in items:
            filters = filters_for_context_item(conversation_id, item)
            if not filters:
                continue
            raw_results = await self.vector_store.search(
                vector=query_vector,
                limit=top_k,
                filters=filters,
            )
            for result in raw_results:
                result_id = str(result.get("id"))
                if result_id not in all_results or result.get("score", 0) > all_results[result_id].get("score", 0):
                    all_results[result_id] = result

        ranked = sorted(all_results.values(), key=lambda item: item.get("score", 0), reverse=True)[:top_k]
        return [citation_from_qdrant(index, result) for index, result in enumerate(ranked, start=1)]

    async def _embed_context_item(
        self,
        item: dict[str, Any],
        *,
        title: str,
        text: str,
        url: str | None,
    ) -> dict[str, Any]:
        chunks = chunk_text(
            text,
            target_tokens=self.settings.chunk_target_tokens,
            overlap_tokens=self.settings.chunk_overlap_tokens,
        )
        if not chunks:
            self.db.update_context_item(item["id"], status="failed", error="No readable text to embed.")
            return self.db.get_context_item(item["id"]) or item

        vector_size = await self.embedder.probe_vector_size()
        await self.vector_store.ensure_collection(vector_size)
        embeddings = await self.embedder.embed_texts([chunk.text for chunk in chunks])
        points = []
        for chunk, vector in zip(chunks, embeddings, strict=True):
            point_id = stable_point_id(item["id"], chunk.chunk_index, self.embedder.model)
            points.append(
                {
                    "id": point_id,
                    "vector": vector,
                    "payload": {
                        "scope": "chat",
                        "conversation_id": item["conversation_id"],
                        "context_item_id": item["id"],
                        "context_type": item["type"],
                        "title": title,
                        "url": url,
                        "chunk_index": chunk.chunk_index,
                        "embedding_model": self.embedder.model,
                        "text": chunk.text,
                    },
                }
            )
        await self.vector_store.delete_by_filter({"context_item_id": item["id"]})
        await self.vector_store.upsert_points(points)
        self.db.update_context_item(item["id"], status="completed", error=None)
        return self.db.get_context_item(item["id"]) or item


def filters_for_context_item(conversation_id: str, item: dict[str, Any]) -> dict[str, Any] | None:
    if item["type"] == "source" and item.get("source_id"):
        return {"source_id": item["source_id"]}
    if item["type"] == "video" and item.get("video_id"):
        return {"video_id": item["video_id"]}
    if item["type"] == "playlist" and item.get("playlist_id"):
        return {"playlist_id": item["playlist_id"]}
    if item["type"] in {"manual", "web"}:
        return {
            "scope": "chat",
            "conversation_id": conversation_id,
            "context_item_id": item["id"],
        }
    return None


def citation_from_qdrant(index: int, result: dict[str, Any]) -> dict[str, Any]:
    payload = result.get("payload") or {}
    return {
        "index": index,
        "title": payload.get("title") or "Untitled context",
        "text": payload.get("text") or "",
        "score": float(result.get("score") or 0),
        "url": payload.get("url"),
        "source_id": payload.get("source_id"),
        "video_id": payload.get("video_id"),
        "playlist_id": payload.get("playlist_id"),
        "context_item_id": payload.get("context_item_id"),
        "context_type": payload.get("context_type"),
        "start_sec": payload.get("start_sec"),
        "end_sec": payload.get("end_sec"),
    }


def build_model_messages(
    *,
    user_text: str,
    history: list[dict[str, Any]],
    citations: list[dict[str, Any]],
) -> list[dict[str, str]]:
    context = build_chat_context(citations)
    system = (
        "You are Context Studio, a concise research assistant. "
        "Answer using the provided context first. Cite sources as [1], [2], etc. "
        "If the context is insufficient, say what is missing and then answer cautiously."
    )
    messages = [{"role": "system", "content": system}]
    if context:
        messages.append({"role": "user", "content": f"Retrieved context:\n{context}"})

    history_budget = 8_000
    kept: list[dict[str, str]] = []
    total = 0
    for message in reversed(history[:-1]):
        content = message["text"]
        total += len(content)
        if total > history_budget:
            break
        kept.append({"role": message["role"], "content": content})
    messages.extend(reversed(kept))
    messages.append({"role": "user", "content": user_text})
    return messages


def build_chat_context(citations: list[dict[str, Any]]) -> str:
    blocks = []
    for citation in citations:
        source = citation.get("url") or citation.get("title")
        blocks.append(f"[{citation['index']}] {citation['title']}\nSource: {source}\n{citation['text']}")
    return "\n\n".join(blocks)


def make_title(text: str) -> str:
    words = text.strip().split()
    return " ".join(words[:8])[:80] or "New conversation"
