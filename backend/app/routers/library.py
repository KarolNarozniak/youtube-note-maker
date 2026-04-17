from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status

from backend.app.dependencies import create_embedder, create_vector_store, db, settings
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
from backend.app.services.search_format import build_context, qdrant_results_to_search_results


router = APIRouter(prefix="/api", tags=["library"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Return backend health status. Takes no input and outputs a simple status dictionary."""
    return {"status": "ok"}


@router.post(
    "/ingestions",
    response_model=IngestionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_ingestion(
    ingestion: IngestionRequest,
    request: Request,
) -> IngestionResponse:
    """Create and enqueue an ingestion job. Inputs are the request body and FastAPI app state; output is the accepted job id/status."""
    job = db.create_job(
        url=ingestion.url,
        language=ingestion.language,
        whisper_model=ingestion.whisper_model or settings.whisper_model,
        force=ingestion.force,
    )
    request.app.state.worker.enqueue(job["id"])
    return IngestionResponse(job_id=job["id"], status=job["status"])


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    """Return one ingestion job. Input is a job id path parameter; output is job status data or a 404 error."""
    job = db.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(**job)


@router.get("/sources", response_model=list[SourceSummary])
async def list_sources() -> list[SourceSummary]:
    """List ingested library sources. Takes no input and outputs source summaries."""
    return [SourceSummary(**source) for source in db.list_sources()]


@router.get("/sources/{source_id}", response_model=SourceDetail)
async def get_source(source_id: str) -> SourceDetail:
    """Return one source with its videos. Input is a source id; output is source detail or a 404 error."""
    source = db.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    videos = db.list_videos_for_source(source_id)
    return SourceDetail(**source, videos=videos)


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: str) -> None:
    """Delete a source from SQLite, Qdrant, and local artifacts. Input is a source id; output is no response body."""
    source = db.get_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    videos = db.list_videos_for_source(source_id)
    try:
        await create_vector_store().delete_by_filter({"source_id": source_id})
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    delete_source_artifacts(settings, videos)
    db.delete_source(source_id)


@router.get("/videos/{video_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(video_id: str) -> TranscriptResponse:
    """Return the full transcript for one video. Input is a video id; output is transcript text and timestamped segments."""
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


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """Run semantic search against Qdrant. Input is a query plus optional filters; output is ranked chunks and a formatted context block."""
    try:
        vector = (await create_embedder().embed_texts([request.query]))[0]
        raw_results = await create_vector_store().search(
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
