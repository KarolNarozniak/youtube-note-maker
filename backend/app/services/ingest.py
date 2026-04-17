from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.config import Settings
from backend.app.database import Database, utc_now
from backend.app.services.artifacts import TranscriptArtifact, load_transcript_artifact
from backend.app.services.chunker import TranscriptChunk, chunk_segments
from backend.app.services.deletion import delete_audio_artifacts
from backend.app.services.downloader import DownloaderClient, Manifest, ManifestVideo
from backend.app.services.embeddings import OllamaEmbeddingClient
from backend.app.services.transcriber import WhisperTranscriber
from backend.app.services.vector_store import QdrantVectorStore
from backend.app.services.youtube import (
    stable_point_id,
    stable_source_id,
    stable_video_row_id,
)


class IngestionPipeline:
    def __init__(
        self,
        *,
        settings: Settings,
        db: Database,
        downloader: DownloaderClient,
        transcriber: WhisperTranscriber,
        embedder: OllamaEmbeddingClient,
        vector_store: QdrantVectorStore,
    ) -> None:
        self.settings = settings
        self.db = db
        self.downloader = downloader
        self.transcriber = transcriber
        self.embedder = embedder
        self.vector_store = vector_store

    async def run(self, job_id: str) -> None:
        job = self.db.get_job(job_id)
        if job is None:
            return

        self.db.update_job(
            job_id,
            status="running",
            stage="resolving",
            progress=0,
            started_at=job.get("started_at") or utc_now(),
            finished_at=None,
        )

        try:
            manifest = await self.downloader.inspect(job["url"])
        except Exception as exc:
            self.db.update_job(
                job_id,
                status="failed",
                stage="failed",
                progress=1,
                errors=[str(exc)],
                finished_at=utc_now(),
            )
            return

        if not manifest.videos:
            self.db.update_job(
                job_id,
                status="failed",
                stage="failed",
                progress=1,
                errors=["No videos were found for this URL."],
                finished_at=utc_now(),
            )
            return

        source_id = self._upsert_source(job_id, manifest)
        video_ids: list[str] = []
        successes = 0
        failures = 0
        total = max(1, len(manifest.videos))

        for index, video in enumerate(manifest.videos):
            video_id = stable_video_row_id(source_id, video.id)
            video_ids.append(video_id)
            self._upsert_video_stub(source_id, video_id, video)
            self.db.update_job(
                job_id,
                source_ids=[source_id],
                video_ids=video_ids,
                current_video=video.title,
                stage="queued_video",
                progress=index / total,
            )

            existing = self.db.get_video(video_id)
            if (
                existing
                and existing.get("status") == "completed"
                and existing.get("chunk_count", 0) > 0
                and not job["force"]
            ):
                successes += 1
                continue

            try:
                await self._process_video(
                    job=job,
                    job_id=job_id,
                    source_id=source_id,
                    video_id=video_id,
                    video=video,
                    video_index=index,
                    total_videos=total,
                )
                successes += 1
            except Exception as exc:
                failures += 1
                message = f"{video.title}: {exc}"
                self.db.append_job_error(job_id, message)
                self.db.update_video(video_id, status="failed", error=str(exc))

        final_status = "completed"
        if failures and successes:
            final_status = "partial"
        elif failures and not successes:
            final_status = "failed"

        self.db.update_job(
            job_id,
            status=final_status,
            stage=final_status,
            progress=1,
            current_video=None,
            source_ids=[source_id],
            video_ids=video_ids,
            finished_at=utc_now(),
        )

    async def _process_video(
        self,
        *,
        job: dict[str, Any],
        job_id: str,
        source_id: str,
        video_id: str,
        video: ManifestVideo,
        video_index: int,
        total_videos: int,
    ) -> None:
        force = bool(job["force"])
        whisper_model = job["whisper_model"]
        language = job.get("language")

        self._progress(job_id, video_index, total_videos, "downloading", 0.15, video.title)
        audio_path = await self._ensure_audio(video_id=video_id, video=video, force=force)

        self._progress(job_id, video_index, total_videos, "transcribing", 0.35, video.title)
        transcript = await self._ensure_transcript(
            audio_path=audio_path,
            source_id=source_id,
            video_id=video_id,
            video=video,
            model_name=whisper_model,
            language=language,
            force=force,
        )

        self._progress(job_id, video_index, total_videos, "chunking", 0.72, video.title)
        chunks = chunk_segments(
            transcript.segments,
            target_tokens=self.settings.chunk_target_tokens,
            overlap_tokens=self.settings.chunk_overlap_tokens,
        )
        if not chunks:
            raise RuntimeError("Whisper produced no transcript chunks.")
        self._write_chunks_file(video_id, chunks)

        self._progress(job_id, video_index, total_videos, "embedding", 0.82, video.title)
        await self._embed_and_store(
            source_id=source_id,
            video_id=video_id,
            video=video,
            transcript=transcript,
            audio_path=audio_path,
            chunks=chunks,
            force=force,
        )
        delete_audio_artifacts(self.settings, video_id=video_id, audio_path=audio_path)

        self.db.update_video(
            video_id,
            audio_path=None,
            transcript_json_path=str(transcript.json_path),
            transcript_txt_path=str(transcript.txt_path),
            transcript_srt_path=str(transcript.srt_path),
            language=transcript.language,
            status="completed",
            error=None,
            chunk_count=len(chunks),
        )
        self._progress(job_id, video_index, total_videos, "completed_video", 1.0, video.title)

    async def _ensure_audio(self, *, video_id: str, video: ManifestVideo, force: bool) -> Path:
        existing = self.db.get_video(video_id)
        if existing and existing.get("audio_path") and not force:
            path = Path(existing["audio_path"])
            if path.exists():
                return path

        audio_dir = self.settings.audio_dir / video_id
        downloaded = await self.downloader.download_audio(
            url=video.url,
            output_dir=audio_dir,
            basename=video_id,
        )
        self.db.update_video(video_id, audio_path=str(downloaded.audio_path), status="downloaded")
        return downloaded.audio_path

    async def _ensure_transcript(
        self,
        *,
        audio_path: Path,
        source_id: str,
        video_id: str,
        video: ManifestVideo,
        model_name: str,
        language: str | None,
        force: bool,
    ) -> TranscriptArtifact:
        existing = self.db.get_video(video_id)
        if existing and existing.get("transcript_json_path") and not force:
            path = Path(existing["transcript_json_path"])
            if path.exists():
                return load_transcript_artifact(path)

        metadata = {
            "source_id": source_id,
            "video_id": video_id,
            "youtube_id": video.id,
            "title": video.title,
            "channel": video.channel,
            "url": video.url,
            "playlist_id": video.playlist_id,
            "whisper_model": model_name,
        }
        transcript = await self.transcriber.transcribe(
            audio_path=audio_path,
            video_id=video_id,
            model_name=model_name,
            language=language,
            metadata=metadata,
        )
        self.db.update_video(
            video_id,
            transcript_json_path=str(transcript.json_path),
            transcript_txt_path=str(transcript.txt_path),
            transcript_srt_path=str(transcript.srt_path),
            language=transcript.language,
            status="transcribed",
        )
        return transcript

    async def _embed_and_store(
        self,
        *,
        source_id: str,
        video_id: str,
        video: ManifestVideo,
        transcript: TranscriptArtifact,
        audio_path: Path,
        chunks: list[TranscriptChunk],
        force: bool,
    ) -> None:
        vector_size = await self.embedder.probe_vector_size()
        await self.vector_store.ensure_collection(vector_size)

        if force:
            self.db.delete_chunks_for_video(video_id, self.embedder.model)
            await self.vector_store.delete_by_filter(
                {"video_id": video_id, "embedding_model": self.embedder.model}
            )

        embeddings = await self.embedder.embed_texts([chunk.text for chunk in chunks])
        points: list[dict[str, Any]] = []
        db_chunks: list[dict[str, Any]] = []

        for chunk, vector in zip(chunks, embeddings, strict=True):
            point_id = stable_point_id(video_id, chunk.chunk_index, self.embedder.model)
            payload = {
                "source_id": source_id,
                "video_id": video_id,
                "playlist_id": video.playlist_id,
                "title": video.title,
                "channel": video.channel,
                "url": video.url,
                "start_sec": chunk.start_sec,
                "end_sec": chunk.end_sec,
                "chunk_index": chunk.chunk_index,
                "language": transcript.language,
                "transcript_path": str(transcript.json_path),
                "audio_path": None,
                "embedding_model": self.embedder.model,
                "text": chunk.text,
            }
            points.append({"id": point_id, "vector": vector, "payload": payload})
            db_chunks.append(
                {
                    "id": point_id,
                    "video_id": video_id,
                    "source_id": source_id,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "start_sec": chunk.start_sec,
                    "end_sec": chunk.end_sec,
                    "token_estimate": chunk.token_estimate,
                    "qdrant_point_id": point_id,
                    "embedding_model": self.embedder.model,
                }
            )

        await self.vector_store.upsert_points(points)
        self.db.insert_chunks(db_chunks)

    def _upsert_source(self, job_id: str, manifest: Manifest) -> str:
        source_raw_id = manifest.source.playlist_id or manifest.source.id
        source_id = stable_source_id(manifest.kind, source_raw_id)
        self.db.upsert_source(
            {
                "id": source_id,
                "type": manifest.kind,
                "url": manifest.source.url,
                "title": manifest.source.title,
                "playlist_id": manifest.source.playlist_id,
                "channel": manifest.source.channel,
                "video_count": len(manifest.videos),
                "job_id": job_id,
            }
        )
        return source_id

    def _upsert_video_stub(self, source_id: str, video_id: str, video: ManifestVideo) -> None:
        self.db.upsert_video(
            {
                "id": video_id,
                "source_id": source_id,
                "youtube_id": video.id,
                "playlist_id": video.playlist_id,
                "url": video.url,
                "title": video.title,
                "channel": video.channel,
                "duration_sec": video.duration_sec,
                "status": "pending",
            }
        )

    def _write_chunks_file(self, video_id: str, chunks: list[TranscriptChunk]) -> None:
        path = self.settings.chunks_dir / f"{video_id}.json"
        path.write_text(
            json.dumps([chunk.__dict__ for chunk in chunks], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _progress(
        self,
        job_id: str,
        video_index: int,
        total_videos: int,
        stage: str,
        stage_fraction: float,
        current_video: str,
    ) -> None:
        progress = min(0.999, (video_index + stage_fraction) / max(1, total_videos))
        self.db.update_job(
            job_id,
            stage=stage,
            progress=progress,
            current_video=current_video,
        )
