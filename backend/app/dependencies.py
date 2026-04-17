from __future__ import annotations

from backend.app.config import get_settings
from backend.app.database import Database
from backend.app.schemas import ConversationDetail
from backend.app.services.chat import ChatService
from backend.app.services.downloader import DownloaderClient
from backend.app.services.embeddings import OllamaEmbeddingClient
from backend.app.services.ingest import IngestionPipeline
from backend.app.services.transcriber import WhisperTranscriber
from backend.app.services.vector_store import QdrantVectorStore


settings = get_settings()
settings.ensure_dirs()
db = Database(settings.db_path)


def create_embedder() -> OllamaEmbeddingClient:
    return OllamaEmbeddingClient(
        base_url=settings.ollama_url,
        model=settings.ollama_embed_model,
    )


def create_vector_store() -> QdrantVectorStore:
    return QdrantVectorStore(
        base_url=settings.qdrant_url,
        collection=settings.qdrant_collection,
    )


def create_ingestion_pipeline() -> IngestionPipeline:
    return IngestionPipeline(
        settings=settings,
        db=db,
        downloader=DownloaderClient(settings),
        transcriber=WhisperTranscriber(settings),
        embedder=create_embedder(),
        vector_store=create_vector_store(),
    )


def create_chat_service() -> ChatService:
    return ChatService(
        settings=settings,
        db=db,
        embedder=create_embedder(),
        vector_store=create_vector_store(),
    )


def build_conversation_detail(conversation_id: str) -> ConversationDetail | None:
    conversation = db.get_conversation(conversation_id)
    if conversation is None:
        return None
    return ConversationDetail(
        **conversation,
        messages=db.list_messages(conversation_id),
        context_items=db.list_context_items(conversation_id),
    )
