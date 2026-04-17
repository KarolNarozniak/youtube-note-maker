from __future__ import annotations

from typing import Any

import httpx


class QdrantVectorStore:
    def __init__(self, *, base_url: str, collection: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.collection = collection

    async def ensure_collection(self, vector_size: int) -> None:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(f"{self.base_url}/collections/{self.collection}")
            if response.status_code == 404:
                create = await client.put(
                    f"{self.base_url}/collections/{self.collection}",
                    json={"vectors": {"size": vector_size, "distance": "Cosine"}},
                )
                create.raise_for_status()
                return
            response.raise_for_status()
            payload = response.json()
            existing_size = _extract_vector_size(payload)
            if existing_size is not None and existing_size != vector_size:
                raise RuntimeError(
                    f"Qdrant collection '{self.collection}' has vector size {existing_size}, "
                    f"but Ollama model produced {vector_size}."
                )

    async def upsert_points(self, points: list[dict[str, Any]]) -> None:
        if not points:
            return
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.put(
                f"{self.base_url}/collections/{self.collection}/points",
                params={"wait": "true"},
                json={"points": points},
            )
            response.raise_for_status()

    async def delete_by_filter(self, filters: dict[str, Any]) -> None:
        qdrant_filter = build_filter(filters)
        if not qdrant_filter:
            return
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/collections/{self.collection}/points/delete",
                params={"wait": "true"},
                json={"filter": qdrant_filter},
            )
            if response.status_code == 404:
                return
            response.raise_for_status()

    async def search(
        self,
        *,
        vector: list[float],
        limit: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        body: dict[str, Any] = {
            "vector": vector,
            "limit": limit,
            "with_payload": True,
        }
        qdrant_filter = build_filter(filters or {})
        if qdrant_filter:
            body["filter"] = qdrant_filter

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/collections/{self.collection}/points/search",
                json=body,
            )
            response.raise_for_status()
            payload = response.json()
        return payload.get("result") or []


def build_filter(filters: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {
        "source_id",
        "video_id",
        "playlist_id",
        "language",
        "embedding_model",
        "scope",
        "conversation_id",
        "context_item_id",
        "context_type",
    }
    must = []
    for key, value in filters.items():
        if key not in allowed or value in (None, ""):
            continue
        must.append({"key": key, "match": {"value": value}})
    return {"must": must} if must else None


def _extract_vector_size(payload: dict[str, Any]) -> int | None:
    vectors = (
        payload.get("result", {})
        .get("config", {})
        .get("params", {})
        .get("vectors")
    )
    if isinstance(vectors, dict) and isinstance(vectors.get("size"), int):
        return vectors["size"]
    return None
