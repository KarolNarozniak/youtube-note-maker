from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from backend.app.config import Settings
from backend.app.services.artifacts import TranscriptArtifact, write_transcript_artifacts


class WhisperTranscriber:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._models: dict[tuple[str, str], Any] = {}

    async def transcribe(
        self,
        *,
        audio_path: Path,
        video_id: str,
        model_name: str,
        language: str | None,
        metadata: dict[str, Any],
    ) -> TranscriptArtifact:
        return await asyncio.to_thread(
            self._transcribe_sync,
            audio_path,
            video_id,
            model_name,
            language,
            metadata,
        )

    def _transcribe_sync(
        self,
        audio_path: Path,
        video_id: str,
        model_name: str,
        language: str | None,
        metadata: dict[str, Any],
    ) -> TranscriptArtifact:
        try:
            import torch
            import whisper
        except ImportError as exc:
            raise RuntimeError(
                "Whisper dependencies are missing. Run scripts/setup.ps1 with Python 3.11."
            ) from exc

        device = self._select_device(torch)
        cache_key = (model_name, device)
        model = self._models.get(cache_key)
        if model is None:
            model = whisper.load_model(model_name, device=device)
            self._models[cache_key] = model

        options: dict[str, Any] = {"verbose": False}
        if language:
            options["language"] = language
        result = model.transcribe(str(audio_path), **options)
        output_dir = self.settings.transcript_dir / video_id
        return write_transcript_artifacts(
            video_id=video_id,
            result=result,
            output_dir=output_dir,
            metadata=metadata,
        )

    def _select_device(self, torch: Any) -> str:
        configured = self.settings.whisper_device.lower()
        if configured != "auto":
            return configured
        return "cuda" if torch.cuda.is_available() else "cpu"
