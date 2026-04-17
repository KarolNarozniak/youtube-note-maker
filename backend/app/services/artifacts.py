from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TranscriptArtifact:
    text: str
    language: str | None
    segments: list[dict[str, Any]]
    json_path: Path
    txt_path: Path
    srt_path: Path


def normalize_segments(raw_segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, segment in enumerate(raw_segments):
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        normalized.append(
            {
                "id": int(segment.get("id", index)),
                "start": float(segment.get("start") or 0),
                "end": float(segment.get("end") or 0),
                "text": text,
            }
        )
    return normalized


def write_transcript_artifacts(
    *,
    video_id: str,
    result: dict[str, Any],
    output_dir: Path,
    metadata: dict[str, Any] | None = None,
) -> TranscriptArtifact:
    output_dir.mkdir(parents=True, exist_ok=True)
    segments = normalize_segments(result.get("segments") or [])
    text = str(result.get("text") or "\n".join(segment["text"] for segment in segments)).strip()
    language = result.get("language")

    json_path = output_dir / f"{video_id}.json"
    txt_path = output_dir / f"{video_id}.txt"
    srt_path = output_dir / f"{video_id}.srt"

    payload = {
        "video_id": video_id,
        "language": language,
        "text": text,
        "segments": segments,
        "metadata": metadata or {},
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_path.write_text(text + "\n", encoding="utf-8")
    srt_path.write_text(render_srt(segments), encoding="utf-8")

    return TranscriptArtifact(
        text=text,
        language=language,
        segments=segments,
        json_path=json_path,
        txt_path=txt_path,
        srt_path=srt_path,
    )


def load_transcript_artifact(json_path: Path) -> TranscriptArtifact:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    video_id = payload.get("video_id") or json_path.stem
    return TranscriptArtifact(
        text=payload.get("text") or "",
        language=payload.get("language"),
        segments=normalize_segments(payload.get("segments") or []),
        json_path=json_path,
        txt_path=json_path.with_suffix(".txt"),
        srt_path=json_path.with_suffix(".srt"),
    )


def render_srt(segments: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for index, segment in enumerate(segments, start=1):
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{format_srt_time(float(segment['start']))} --> {format_srt_time(float(segment['end']))}",
                    str(segment["text"]),
                ]
            )
        )
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def format_srt_time(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"
