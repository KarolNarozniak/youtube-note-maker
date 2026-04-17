SQLITE_SCHEMA = """
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
