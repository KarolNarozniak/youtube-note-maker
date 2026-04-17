---
sidebar_position: 7
title: Operations
---

# Operations

## Data Locations

```text
data/app.db              SQLite metadata and chat history
data/transcripts/        Whisper JSON, TXT, and SRT transcript artifacts
data/chunks/             Chunk metadata written during ingestion
data/audio/              Temporary audio during processing
qdrant_storage           Docker volume for Qdrant vectors
```

Audio is deleted after successful video processing. If a job fails during download or transcription, a partial audio file may remain and can be removed by deleting the failed source or clearing `data/audio/`.

## Backups

For a local backup, copy:

- `data/app.db`
- `data/transcripts/`
- `data/chunks/`
- The Docker Qdrant volume, or export Qdrant collection data separately.

## Troubleshooting

If Qdrant is unavailable, run:

```powershell
.\scripts\start-qdrant.ps1
```

If the downloader cannot start, rebuild the sidecar:

```powershell
dotnet build downloader\YoutubeNoteDownloader\YoutubeNoteDownloader.csproj
```

If Whisper is slow, use a smaller model through the ingestion request or set `WHISPER_MODEL` in `.env`.
