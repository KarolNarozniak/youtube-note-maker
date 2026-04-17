from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_env_file(path: Path | None = None) -> None:
    env_path = path or _repo_root() / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    host: str
    port: int
    data_dir: Path
    db_path: Path
    audio_dir: Path
    transcript_dir: Path
    chunks_dir: Path
    qdrant_url: str
    qdrant_collection: str
    ollama_url: str
    ollama_embed_model: str
    whisper_model: str
    whisper_device: str
    downloader_timeout_sec: int
    downloader_project: Path
    downloader_dll: Path
    chunk_target_tokens: int
    chunk_overlap_tokens: int

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.transcript_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_dir.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    load_env_file()
    root = _repo_root()
    data_dir = Path(_env("DATA_DIR", "data"))
    if not data_dir.is_absolute():
        data_dir = root / data_dir

    return Settings(
        repo_root=root,
        host=_env("APP_HOST", "127.0.0.1"),
        port=_env_int("APP_PORT", 8000),
        data_dir=data_dir,
        db_path=data_dir / "app.db",
        audio_dir=data_dir / "audio",
        transcript_dir=data_dir / "transcripts",
        chunks_dir=data_dir / "chunks",
        qdrant_url=_env("QDRANT_URL", "http://localhost:6333").rstrip("/"),
        qdrant_collection=_env("QDRANT_COLLECTION", "youtube_notes_v1"),
        ollama_url=_env("OLLAMA_URL", "http://localhost:11434").rstrip("/"),
        ollama_embed_model=_env("OLLAMA_EMBED_MODEL", "embeddinggemma"),
        whisper_model=_env("WHISPER_MODEL", "turbo"),
        whisper_device=_env("WHISPER_DEVICE", "auto"),
        downloader_timeout_sec=_env_int("DOWNLOADER_TIMEOUT_SEC", 7200),
        downloader_project=root
        / "downloader"
        / "YoutubeNoteDownloader"
        / "YoutubeNoteDownloader.csproj",
        downloader_dll=root
        / "downloader"
        / "YoutubeNoteDownloader"
        / "bin"
        / "Debug"
        / "net10.0"
        / "YoutubeNoteDownloader.dll",
        chunk_target_tokens=_env_int("INGEST_CHUNK_TARGET_TOKENS", 900),
        chunk_overlap_tokens=_env_int("INGEST_CHUNK_OVERLAP_TOKENS", 150),
    )
