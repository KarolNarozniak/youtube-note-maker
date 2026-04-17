from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _loads_list(value: str | None) -> list[Any]:
    if not value:
        return []
    loaded = json.loads(value)
    return loaded if isinstance(loaded, list) else []


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    language TEXT,
                    whisper_model TEXT NOT NULL,
                    force INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    progress REAL NOT NULL DEFAULT 0,
                    current_video TEXT,
                    errors TEXT NOT NULL DEFAULT '[]',
                    source_ids TEXT NOT NULL DEFAULT '[]',
                    video_ids TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT
                );

                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    playlist_id TEXT,
                    channel TEXT,
                    video_count INTEGER NOT NULL DEFAULT 0,
                    job_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS videos (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    youtube_id TEXT NOT NULL,
                    playlist_id TEXT,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    channel TEXT,
                    duration_sec REAL,
                    audio_path TEXT,
                    transcript_json_path TEXT,
                    transcript_txt_path TEXT,
                    transcript_srt_path TEXT,
                    language TEXT,
                    status TEXT NOT NULL,
                    error TEXT,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(source_id, youtube_id)
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    video_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    start_sec REAL NOT NULL,
                    end_sec REAL NOT NULL,
                    token_estimate INTEGER NOT NULL,
                    qdrant_point_id TEXT NOT NULL,
                    embedding_model TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(video_id, chunk_index, embedding_model)
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    model_provider TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    text TEXT NOT NULL,
                    citations TEXT NOT NULL DEFAULT '[]',
                    model_provider TEXT,
                    model_id TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS conversation_context_items (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT,
                    text TEXT,
                    source_id TEXT,
                    video_id TEXT,
                    playlist_id TEXT,
                    status TEXT NOT NULL,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_videos_source ON videos(source_id);
                CREATE INDEX IF NOT EXISTS idx_chunks_video ON chunks(video_id);
                CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id);
                CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
                CREATE INDEX IF NOT EXISTS idx_context_conversation ON conversation_context_items(conversation_id);
                """
            )

    def create_job(
        self,
        *,
        url: str,
        language: str | None,
        whisper_model: str,
        force: bool,
    ) -> dict[str, Any]:
        now = utc_now()
        job_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    id, url, language, whisper_model, force, status, stage,
                    progress, errors, source_ids, video_ids, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'queued', 'queued', 0, '[]', '[]', '[]', ?, ?)
                """,
                (job_id, url, language, whisper_model, int(force), now, now),
            )
        job = self.get_job(job_id)
        assert job is not None
        return job

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        job = _row_to_dict(row)
        if job is None:
            return None
        job["force"] = bool(job["force"])
        job["errors"] = _loads_list(job["errors"])
        job["source_ids"] = _loads_list(job["source_ids"])
        job["video_ids"] = _loads_list(job["video_ids"])
        return job

    def recoverable_job_ids(self) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id FROM jobs WHERE status IN ('queued', 'running') ORDER BY created_at"
            ).fetchall()
            conn.execute(
                """
                UPDATE jobs
                SET status = 'queued', stage = 'queued', updated_at = ?
                WHERE status = 'running'
                """,
                (utc_now(),),
            )
        return [row["id"] for row in rows]

    def update_job(self, job_id: str, **fields: Any) -> None:
        allowed = {
            "status",
            "stage",
            "progress",
            "current_video",
            "errors",
            "source_ids",
            "video_ids",
            "started_at",
            "finished_at",
        }
        updates: list[str] = []
        values: list[Any] = []
        for key, value in fields.items():
            if key not in allowed:
                raise ValueError(f"Unsupported job field: {key}")
            if key in {"errors", "source_ids", "video_ids"}:
                value = _json(value)
            updates.append(f"{key} = ?")
            values.append(value)
        updates.append("updated_at = ?")
        values.append(utc_now())
        values.append(job_id)
        with self.connect() as conn:
            conn.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?", values)

    def append_job_error(self, job_id: str, message: str) -> None:
        job = self.get_job(job_id)
        if job is None:
            return
        errors = list(job["errors"])
        errors.append(message)
        self.update_job(job_id, errors=errors)

    def upsert_source(self, source: dict[str, Any]) -> None:
        now = utc_now()
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT created_at FROM sources WHERE id = ?", (source["id"],)
            ).fetchone()
            created_at = existing["created_at"] if existing else now
            conn.execute(
                """
                INSERT INTO sources (
                    id, type, url, title, playlist_id, channel, video_count,
                    job_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    type = excluded.type,
                    url = excluded.url,
                    title = excluded.title,
                    playlist_id = excluded.playlist_id,
                    channel = excluded.channel,
                    video_count = excluded.video_count,
                    job_id = excluded.job_id,
                    updated_at = excluded.updated_at
                """,
                (
                    source["id"],
                    source["type"],
                    source["url"],
                    source["title"],
                    source.get("playlist_id"),
                    source.get("channel"),
                    int(source.get("video_count") or 0),
                    source["job_id"],
                    created_at,
                    now,
                ),
            )

    def list_sources(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sources ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        return _row_to_dict(row)

    def upsert_video(self, video: dict[str, Any]) -> None:
        now = utc_now()
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT created_at FROM videos WHERE id = ?", (video["id"],)
            ).fetchone()
            created_at = existing["created_at"] if existing else now
            conn.execute(
                """
                INSERT INTO videos (
                    id, source_id, youtube_id, playlist_id, url, title, channel,
                    duration_sec, audio_path, transcript_json_path, transcript_txt_path,
                    transcript_srt_path, language, status, error, chunk_count,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    source_id = excluded.source_id,
                    youtube_id = excluded.youtube_id,
                    playlist_id = excluded.playlist_id,
                    url = excluded.url,
                    title = excluded.title,
                    channel = excluded.channel,
                    duration_sec = excluded.duration_sec,
                    audio_path = COALESCE(excluded.audio_path, videos.audio_path),
                    transcript_json_path = COALESCE(excluded.transcript_json_path, videos.transcript_json_path),
                    transcript_txt_path = COALESCE(excluded.transcript_txt_path, videos.transcript_txt_path),
                    transcript_srt_path = COALESCE(excluded.transcript_srt_path, videos.transcript_srt_path),
                    language = COALESCE(excluded.language, videos.language),
                    status = excluded.status,
                    error = excluded.error,
                    chunk_count = excluded.chunk_count,
                    updated_at = excluded.updated_at
                """,
                (
                    video["id"],
                    video["source_id"],
                    video["youtube_id"],
                    video.get("playlist_id"),
                    video["url"],
                    video["title"],
                    video.get("channel"),
                    video.get("duration_sec"),
                    video.get("audio_path"),
                    video.get("transcript_json_path"),
                    video.get("transcript_txt_path"),
                    video.get("transcript_srt_path"),
                    video.get("language"),
                    video.get("status", "pending"),
                    video.get("error"),
                    int(video.get("chunk_count") or 0),
                    created_at,
                    now,
                ),
            )

    def update_video(self, video_id: str, **fields: Any) -> None:
        allowed = {
            "audio_path",
            "transcript_json_path",
            "transcript_txt_path",
            "transcript_srt_path",
            "language",
            "status",
            "error",
            "chunk_count",
        }
        updates: list[str] = []
        values: list[Any] = []
        for key, value in fields.items():
            if key not in allowed:
                raise ValueError(f"Unsupported video field: {key}")
            updates.append(f"{key} = ?")
            values.append(value)
        updates.append("updated_at = ?")
        values.append(utc_now())
        values.append(video_id)
        with self.connect() as conn:
            conn.execute(f"UPDATE videos SET {', '.join(updates)} WHERE id = ?", values)

    def get_video(self, video_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
        return _row_to_dict(row)

    def list_videos_for_source(self, source_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM videos WHERE source_id = ? ORDER BY created_at, title",
                (source_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_source(self, source_id: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM chunks WHERE source_id = ?", (source_id,))
            conn.execute("DELETE FROM videos WHERE source_id = ?", (source_id,))
            conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))

    def delete_chunks_for_video(self, video_id: str, embedding_model: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM chunks WHERE video_id = ? AND embedding_model = ?",
                (video_id, embedding_model),
            )

    def insert_chunks(self, chunks: list[dict[str, Any]]) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO chunks (
                    id, video_id, source_id, chunk_index, text, start_sec, end_sec,
                    token_estimate, qdrant_point_id, embedding_model, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(video_id, chunk_index, embedding_model) DO UPDATE SET
                    text = excluded.text,
                    start_sec = excluded.start_sec,
                    end_sec = excluded.end_sec,
                    token_estimate = excluded.token_estimate,
                    qdrant_point_id = excluded.qdrant_point_id
                """,
                [
                    (
                        chunk["id"],
                        chunk["video_id"],
                        chunk["source_id"],
                        chunk["chunk_index"],
                        chunk["text"],
                        chunk["start_sec"],
                        chunk["end_sec"],
                        chunk["token_estimate"],
                        chunk["qdrant_point_id"],
                        chunk["embedding_model"],
                        now,
                    )
                    for chunk in chunks
                ],
            )

    def get_chunks_for_video(self, video_id: str, embedding_model: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM chunks
                WHERE video_id = ? AND embedding_model = ?
                ORDER BY chunk_index
                """,
                (video_id, embedding_model),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_conversation(
        self,
        *,
        title: str,
        model_provider: str,
        model_id: str,
    ) -> dict[str, Any]:
        now = utc_now()
        conversation_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO conversations (
                    id, title, model_provider, model_id, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (conversation_id, title, model_provider, model_id, now, now),
            )
        conversation = self.get_conversation(conversation_id)
        assert conversation is not None
        return conversation

    def list_conversations(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    c.*,
                    (
                        SELECT text FROM messages
                        WHERE conversation_id = c.id
                        ORDER BY created_at DESC
                        LIMIT 1
                    ) AS last_message,
                    (
                        SELECT COUNT(*) FROM messages
                        WHERE conversation_id = c.id
                    ) AS message_count
                FROM conversations c
                ORDER BY c.updated_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
        return _row_to_dict(row)

    def touch_conversation(
        self,
        conversation_id: str,
        *,
        title: str | None = None,
        model_provider: str | None = None,
        model_id: str | None = None,
    ) -> None:
        updates = ["updated_at = ?"]
        values: list[Any] = [utc_now()]
        if title is not None:
            updates.append("title = ?")
            values.append(title)
        if model_provider is not None:
            updates.append("model_provider = ?")
            values.append(model_provider)
        if model_id is not None:
            updates.append("model_id = ?")
            values.append(model_id)
        values.append(conversation_id)
        with self.connect() as conn:
            conn.execute(
                f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?",
                values,
            )

    def delete_conversation(self, conversation_id: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            conn.execute(
                "DELETE FROM conversation_context_items WHERE conversation_id = ?",
                (conversation_id,),
            )
            conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))

    def create_message(
        self,
        *,
        conversation_id: str,
        role: str,
        text: str,
        citations: list[dict[str, Any]] | None = None,
        model_provider: str | None = None,
        model_id: str | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        message_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (
                    id, conversation_id, role, text, citations,
                    model_provider, model_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    conversation_id,
                    role,
                    text,
                    _json(citations or []),
                    model_provider,
                    model_id,
                    now,
                ),
            )
        self.touch_conversation(
            conversation_id,
            model_provider=model_provider,
            model_id=model_id,
        )
        message = self.get_message(message_id)
        assert message is not None
        return message

    def get_message(self, message_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
        message = _row_to_dict(row)
        if message is None:
            return None
        message["citations"] = _loads_list(message["citations"])
        return message

    def list_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at
                """,
                (conversation_id,),
            ).fetchall()
        messages = [dict(row) for row in rows]
        for message in messages:
            message["citations"] = _loads_list(message["citations"])
        return messages

    def create_context_item(
        self,
        *,
        conversation_id: str,
        item_type: str,
        title: str,
        url: str | None = None,
        text: str | None = None,
        source_id: str | None = None,
        video_id: str | None = None,
        playlist_id: str | None = None,
        status: str = "completed",
        error: str | None = None,
    ) -> dict[str, Any]:
        now = utc_now()
        item_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO conversation_context_items (
                    id, conversation_id, type, title, url, text, source_id,
                    video_id, playlist_id, status, error, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    conversation_id,
                    item_type,
                    title,
                    url,
                    text,
                    source_id,
                    video_id,
                    playlist_id,
                    status,
                    error,
                    now,
                    now,
                ),
            )
        self.touch_conversation(conversation_id)
        item = self.get_context_item(item_id)
        assert item is not None
        return item

    def update_context_item(self, item_id: str, **fields: Any) -> None:
        allowed = {"title", "url", "text", "source_id", "video_id", "playlist_id", "status", "error"}
        updates: list[str] = []
        values: list[Any] = []
        for key, value in fields.items():
            if key not in allowed:
                raise ValueError(f"Unsupported context item field: {key}")
            updates.append(f"{key} = ?")
            values.append(value)
        updates.append("updated_at = ?")
        values.append(utc_now())
        values.append(item_id)
        with self.connect() as conn:
            conn.execute(
                f"UPDATE conversation_context_items SET {', '.join(updates)} WHERE id = ?",
                values,
            )

    def get_context_item(self, item_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM conversation_context_items WHERE id = ?", (item_id,)
            ).fetchone()
        return _row_to_dict(row)

    def list_context_items(self, conversation_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM conversation_context_items
                WHERE conversation_id = ?
                ORDER BY created_at
                """,
                (conversation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_context_item(self, item_id: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM conversation_context_items WHERE id = ?", (item_id,))
