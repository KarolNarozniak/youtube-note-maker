<p align="center">
  <img src="./logo.png" alt="Thothscribe logo" width="140" />
</p>

# Thothscribe

Thothscribe is a local YouTube-to-RAG workspace. Paste a YouTube video or playlist URL, download audio locally through a small YoutubeExplode sidecar, transcribe with Whisper, chunk and embed with Ollama, store vectors in Qdrant, and chat over the resulting context.

## What This Builds

- FastAPI backend on `127.0.0.1:8000`
- React/Vite app on `127.0.0.1:5173`
- Docusaurus documentation on `127.0.0.1:3000`
- .NET downloader sidecar using `YoutubeExplode`
- SQLite metadata and chat history in `data/app.db`
- Transcript and chunk artifacts under `data/`
- Qdrant collection `youtube_notes_v1`
- Chat workspace with local Ollama models and optional session-only OpenAI API keys

Audio is deleted after successful transcription, chunking, and embedding. Transcripts, chunk metadata, SQLite rows, and Qdrant vectors remain until you delete the source or conversation.

## Prerequisites

- Python 3.11
- .NET SDK 10+
- Node 20+
- Docker Desktop
- Ollama
- FFmpeg
- NVIDIA GPU optional, but recommended for Whisper

## Setup

```powershell
Copy-Item .env.example .env
.\scripts\setup.ps1
```

## Run

Open separate terminals:

```powershell
.\scripts\start-qdrant.ps1
.\scripts\start-backend.ps1
.\scripts\start-frontend.ps1
.\scripts\start-docs.ps1
```

Open:

```text
http://127.0.0.1:5173
http://127.0.0.1:3000
```

## API

- `POST /api/ingestions`
- `GET /api/jobs/{job_id}`
- `GET /api/sources`
- `GET /api/sources/{source_id}`
- `DELETE /api/sources/{source_id}`
- `GET /api/videos/{video_id}/transcript`
- `POST /api/search`
- `GET /api/chat/models`
- `POST /api/conversations`
- `GET /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `DELETE /api/conversations/{conversation_id}`
- `POST /api/conversations/{conversation_id}/context`
- `DELETE /api/conversations/{conversation_id}/context/{item_id}`
- `POST /api/conversations/{conversation_id}/messages`

The full system guide lives in the Docusaurus docs under `docs-site/`.
