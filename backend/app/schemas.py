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
