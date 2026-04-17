---
sidebar_position: 4
title: Library
---

# Library

The Library tab ingests YouTube videos and playlists into local transcript and vector artifacts.

## Pipeline

1. Submit a video or playlist URL.
2. The backend creates a persistent SQLite job.
3. The worker resolves video metadata through the downloader sidecar.
4. Audio is downloaded to `data/audio/`.
5. Whisper writes transcript JSON, TXT, and SRT artifacts to `data/transcripts/`.
6. Transcript segments are chunked at timestamp boundaries where possible.
7. Ollama embeds chunks with `embeddinggemma`.
8. Qdrant stores vectors with citation metadata.
9. Audio is deleted after successful processing.

## Deletion

Deleting a source from the GUI removes:

- The source and video metadata from SQLite.
- Transcript files.
- Chunk files.
- Qdrant vectors for that source.
- Any remaining audio artifact directory for that source.

Playlist ingestion is partial-failure tolerant. A failed video records its error while successful videos remain usable.
