from __future__ import annotations

from typing import Any


def seconds_label(seconds: float) -> str:
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02}:{secs:02}"
    return f"{minutes}:{secs:02}"


def qdrant_results_to_search_results(raw_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    formatted: list[dict[str, Any]] = []
    for item in raw_results:
        payload = item.get("payload") or {}
        formatted.append(
            {
                "score": float(item.get("score") or 0),
                "text": payload.get("text") or "",
                "source_id": payload.get("source_id") or "",
                "video_id": payload.get("video_id") or "",
                "playlist_id": payload.get("playlist_id"),
                "title": payload.get("title") or "Untitled video",
                "channel": payload.get("channel"),
                "url": payload.get("url") or "",
                "start_sec": float(payload.get("start_sec") or 0),
                "end_sec": float(payload.get("end_sec") or 0),
                "chunk_index": int(payload.get("chunk_index") or 0),
                "language": payload.get("language"),
                "transcript_path": payload.get("transcript_path"),
                "audio_path": payload.get("audio_path"),
            }
        )
    return formatted


def build_context(results: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for index, result in enumerate(results, start=1):
        start = seconds_label(float(result["start_sec"]))
        end = seconds_label(float(result["end_sec"]))
        blocks.append(
            "\n".join(
                [
                    f"[{index}] {result['title']} ({start}-{end})",
                    f"URL: {result['url']}",
                    result["text"],
                ]
            )
        )
    return "\n\n".join(blocks)
