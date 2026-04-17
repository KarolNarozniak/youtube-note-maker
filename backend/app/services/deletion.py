from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from backend.app.config import Settings


def delete_source_artifacts(settings: Settings, videos: list[dict[str, Any]]) -> None:
    for video in videos:
        video_id = str(video["id"])
        candidates = [
            video.get("audio_path"),
            video.get("transcript_json_path"),
            video.get("transcript_txt_path"),
            video.get("transcript_srt_path"),
            settings.audio_dir / video_id,
            settings.transcript_dir / video_id,
            settings.chunks_dir / f"{video_id}.json",
        ]
        for candidate in candidates:
            if candidate:
                delete_data_path(settings, Path(candidate))


def delete_audio_artifacts(settings: Settings, *, video_id: str, audio_path: Path) -> None:
    delete_data_path(settings, audio_path)
    delete_data_path(settings, settings.audio_dir / video_id)


def delete_data_path(settings: Settings, path: Path) -> None:
    try:
        resolved = path.resolve()
    except OSError:
        return

    data_root = settings.data_dir.resolve()
    if resolved != data_root and data_root not in resolved.parents:
        return
    if not resolved.exists():
        return
    if resolved.is_dir():
        shutil.rmtree(resolved)
    else:
        resolved.unlink()
        _remove_empty_parents(resolved.parent, stop_at=data_root)


def _remove_empty_parents(path: Path, *, stop_at: Path) -> None:
    current = path
    while current != stop_at and stop_at in current.parents:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent
