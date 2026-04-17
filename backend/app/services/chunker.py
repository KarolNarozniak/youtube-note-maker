from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TranscriptChunk:
    chunk_index: int
    text: str
    start_sec: float
    end_sec: float
    token_estimate: int
    segment_ids: list[int]


def estimate_tokens(text: str) -> int:
    compact = " ".join(text.split())
    if not compact:
        return 0
    return max(1, math.ceil(len(compact) / 4))


def chunk_segments(
    segments: list[dict[str, Any]],
    *,
    target_tokens: int = 900,
    overlap_tokens: int = 150,
) -> list[TranscriptChunk]:
    clean_segments = [segment for segment in segments if str(segment.get("text") or "").strip()]
    if not clean_segments:
        return []

    chunks: list[TranscriptChunk] = []
    current: list[dict[str, Any]] = []
    current_tokens = 0

    for segment in clean_segments:
        segment_tokens = estimate_tokens(str(segment["text"]))
        if current and current_tokens + segment_tokens > target_tokens:
            chunks.append(_make_chunk(len(chunks), current))
            current = _overlap_tail(current, overlap_tokens)
            current_tokens = sum(estimate_tokens(str(item["text"])) for item in current)

        current.append(segment)
        current_tokens += segment_tokens

    if current:
        candidate = _make_chunk(len(chunks), current)
        if not chunks or candidate.text != chunks[-1].text:
            chunks.append(candidate)

    return chunks


def _make_chunk(index: int, segments: list[dict[str, Any]]) -> TranscriptChunk:
    text = " ".join(str(segment["text"]).strip() for segment in segments).strip()
    return TranscriptChunk(
        chunk_index=index,
        text=text,
        start_sec=float(segments[0]["start"]),
        end_sec=float(segments[-1]["end"]),
        token_estimate=estimate_tokens(text),
        segment_ids=[int(segment["id"]) for segment in segments],
    )


def _overlap_tail(segments: list[dict[str, Any]], overlap_tokens: int) -> list[dict[str, Any]]:
    if overlap_tokens <= 0:
        return []
    selected: list[dict[str, Any]] = []
    total = 0
    for segment in reversed(segments):
        selected.append(segment)
        total += estimate_tokens(str(segment["text"]))
        if total >= overlap_tokens:
            break
    return list(reversed(selected))
