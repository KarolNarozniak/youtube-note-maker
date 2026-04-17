from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


JobStatus = Literal["queued", "running", "completed", "partial", "failed"]


class IngestionRequest(BaseModel):
    url: str = Field(min_length=8)
    language: str | None = None
    whisper_model: str | None = None
    force: bool = False


class IngestionResponse(BaseModel):
    job_id: str
    status: JobStatus


class JobResponse(BaseModel):
    id: str
    url: str
    language: str | None
    whisper_model: str
    force: bool
    status: JobStatus
    stage: str
    progress: float
    current_video: str | None
    errors: list[str]
    source_ids: list[str]
    video_ids: list[str]
    created_at: str
    updated_at: str
    started_at: str | None
    finished_at: str | None


class SourceSummary(BaseModel):
    id: str
    type: str
    url: str
    title: str
    playlist_id: str | None
    channel: str | None
    video_count: int
    job_id: str
    created_at: str
    updated_at: str


class VideoSummary(BaseModel):
    id: str
    source_id: str
    youtube_id: str
    playlist_id: str | None
    url: str
    title: str
    channel: str | None
    duration_sec: float | None
    audio_path: str | None
    transcript_json_path: str | None
    transcript_txt_path: str | None
    transcript_srt_path: str | None
    language: str | None
    status: str
    error: str | None
    chunk_count: int
    created_at: str
    updated_at: str


class SourceDetail(SourceSummary):
    videos: list[VideoSummary]


class TranscriptSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str


class TranscriptResponse(BaseModel):
    video_id: str
    text: str
    language: str | None
    segments: list[TranscriptSegment]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=6, ge=1, le=30)
    filters: dict[str, Any] | None = None


class SearchResult(BaseModel):
    score: float
    text: str
    source_id: str
    video_id: str
    playlist_id: str | None = None
    title: str
    channel: str | None = None
    url: str
    start_sec: float
    end_sec: float
    chunk_index: int
    language: str | None = None
    transcript_path: str | None = None
    audio_path: str | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    context: str


ModelProvider = Literal["ollama", "openai"]
ContextItemType = Literal["manual", "web", "source", "video", "playlist"]


class ChatModelInfo(BaseModel):
    provider: ModelProvider
    id: str
    label: str
    available: bool = True


class ChatModelsResponse(BaseModel):
    local: list[ChatModelInfo]
    online: list[ChatModelInfo]


class ConversationCreateRequest(BaseModel):
    title: str | None = None
    model_provider: ModelProvider = "ollama"
    model_id: str = "qwen3:30b"


class ConversationSummary(BaseModel):
    id: str
    title: str
    model_provider: ModelProvider
    model_id: str
    created_at: str
    updated_at: str
    last_message: str | None = None
    message_count: int = 0


class ConversationContextCreateRequest(BaseModel):
    type: ContextItemType
    title: str | None = None
    url: str | None = None
    text: str | None = None
    source_id: str | None = None
    video_id: str | None = None
    playlist_id: str | None = None


class ConversationContextItem(BaseModel):
    id: str
    conversation_id: str
    type: ContextItemType
    title: str
    url: str | None = None
    text: str | None = None
    source_id: str | None = None
    video_id: str | None = None
    playlist_id: str | None = None
    status: str
    error: str | None = None
    created_at: str
    updated_at: str


class ChatCitation(BaseModel):
    index: int
    title: str
    text: str
    score: float
    url: str | None = None
    source_id: str | None = None
    video_id: str | None = None
    playlist_id: str | None = None
    context_item_id: str | None = None
    context_type: str | None = None
    start_sec: float | None = None
    end_sec: float | None = None


class ChatMessage(BaseModel):
    id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    text: str
    citations: list[ChatCitation] = []
    model_provider: ModelProvider | None = None
    model_id: str | None = None
    created_at: str


class ConversationDetail(BaseModel):
    id: str
    title: str
    model_provider: ModelProvider
    model_id: str
    created_at: str
    updated_at: str
    messages: list[ChatMessage]
    context_items: list[ConversationContextItem]


class ChatSendRequest(BaseModel):
    text: str = Field(min_length=1)
    model_provider: ModelProvider = "ollama"
    model_id: str = "qwen3:30b"
    api_key: str | None = None
    top_k: int = Field(default=8, ge=1, le=20)


class ChatSendResponse(BaseModel):
    user_message: ChatMessage
    assistant_message: ChatMessage
    citations: list[ChatCitation]
