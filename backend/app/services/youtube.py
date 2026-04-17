from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse


YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
}


def classify_youtube_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host not in YOUTUBE_HOSTS:
        return "unknown"

    query = parse_qs(parsed.query)
    if "list" in query:
        return "playlist"
    if parsed.path.startswith("/playlist"):
        return "playlist"
    if extract_youtube_video_id(url):
        return "video"
    return "unknown"


def extract_youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    query = parse_qs(parsed.query)

    if host == "youtu.be":
        candidate = parsed.path.strip("/").split("/")[0]
        return candidate or None

    if host in YOUTUBE_HOSTS:
        if "v" in query and query["v"]:
            return query["v"][0]
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] in {"shorts", "embed", "live"}:
            return parts[1]
    return None


def extract_playlist_id(url: str) -> str | None:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    values = query.get("list")
    return values[0] if values else None


def stable_source_id(kind: str, raw_id: str) -> str:
    prefix = "pl" if kind == "playlist" else "vid"
    return f"{prefix}_{safe_id(raw_id)}"


def stable_video_row_id(source_id: str, youtube_id: str) -> str:
    return f"{source_id}_{safe_id(youtube_id)}"


def stable_point_id(video_id: str, chunk_index: int, embedding_model: str) -> str:
    seed = f"{video_id}:{chunk_index}:{embedding_model}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    return f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"


def safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    if cleaned:
        return cleaned[:120]
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def safe_filename(value: str, fallback: str = "file") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", value).strip(" ._")
    return (cleaned or fallback)[:160]


def relative_to_repo(path: str | Path, repo_root: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return str(resolved.relative_to(repo_root))
    except ValueError:
        return str(resolved)
