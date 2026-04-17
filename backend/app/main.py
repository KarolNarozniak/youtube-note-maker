from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.database import Database
from backend.app.schemas import (
    IngestionRequest,
    IngestionResponse,
    JobResponse,
    SearchRequest,
    SearchResponse,
    SourceDetail,
    SourceSummary,
    TranscriptResponse,
)
from backend.app.services.artifacts import load_transcript_artifact
from backend.app.services.deletion import delete_source_artifacts
from backend.app.services.downloader import DownloaderClient
from backend.app.services.embeddings import OllamaEmbeddingClient
from backend.app.services.ingest import IngestionPipeline
from backend.app.services.search_format import build_context, qdrant_results_to_search_results
from backend.app.services.transcriber import WhisperTranscriber
from backend.app.services.vector_store import QdrantVectorStore
from backend.app.worker import IngestionWorker


settings = get_settings()
settings.ensure_dirs()
db = Database(settings.db_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    pipeline = IngestionPipeline(
        settings=settings,
        db=db,
        downloader=DownloaderClient(settings),
        transcriber=WhisperTranscriber(settings),
        embedder=OllamaEmbeddingClient(
            base_url=settings.ollama_url,
            model=settings.ollama_embed_model,
        ),
        vector_store=QdrantVectorStore(
            base_url=settings.qdrant_url,
            collection=settings.qdrant_collection,
        ),
    )
    worker = IngestionWorker(pipeline)
    app.state.worker = worker
    worker.start(db.recoverable_job_ids())
    try:
        yield
    finally:
        await worker.stop()


app = FastAPI(title="YouTube Note Maker", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/api/ingestions",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_ingestion(request: IngestionRequest) -> IngestionResponse:
    job = db.create_job(
        url=request.url,
        language=request.language,
        whisper_model=request.whisper_model or settings.whisper_model,
        force=request.force,
    )
    app.state.worker.enqueue(job["id"])
    return IngestionResponse(job_id=job["id"], status=job["status"])


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    job = db.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(**job)


@app.get("/api/sources", response_model=list[SourceSummary])
async def list_sources() -> list[SourceSummary]:
    return [SourceSummary(**source) for source in db.list_sources()]


@app.get("/api/sources/{source_id}", response_model=SourceDetail)
async def get_source(source_id: str) -> SourceDetail:
    source = db.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    videos = db.list_videos_for_source(source_id)
    return SourceDetail(**source, videos=videos)


@app.delete("/api/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: str) -> None:
    source = db.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    videos = db.list_videos_for_source(source_id)
    vector_store = QdrantVectorStore(
        base_url=settings.qdrant_url,
        collection=settings.qdrant_collection,
    )
    try:
        await vector_store.delete_by_filter({"source_id": source_id})
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    delete_source_artifacts(settings, videos)
    db.delete_source(source_id)
    return None


@app.get("/api/videos/{video_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(video_id: str) -> TranscriptResponse:
    video = db.get_video(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    transcript_path = video.get("transcript_json_path")
    if not transcript_path or not Path(transcript_path).exists():
        raise HTTPException(status_code=404, detail="Transcript not found")
    artifact = load_transcript_artifact(Path(transcript_path))
    return TranscriptResponse(
        video_id=video_id,
        text=artifact.text,
        language=artifact.language,
        segments=artifact.segments,
    )


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    embedder = OllamaEmbeddingClient(
        base_url=settings.ollama_url,
        model=settings.ollama_embed_model,
    )
    vector_store = QdrantVectorStore(
        base_url=settings.qdrant_url,
        collection=settings.qdrant_collection,
    )
    try:
        vector = (await embedder.embed_texts([request.query]))[0]
        raw_results = await vector_store.search(
            vector=vector,
            limit=request.top_k,
            filters=request.filters,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    results = qdrant_results_to_search_results(raw_results)
    return SearchResponse(
        query=request.query,
        results=results,
        context=build_context(results),
    )
