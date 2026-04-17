# Context Studio

Local YouTube-to-RAG ingestion app.

Paste a YouTube video or playlist URL, download audio locally through a small YoutubeExplode sidecar, transcribe with local Whisper, store full transcript artifacts, chunk and embed with Ollama, save vectors in Qdrant, and expose search-context endpoints for another chatbot.

## What This Builds

- FastAPI backend on `127.0.0.1:8000`
- React/Vite dashboard on `127.0.0.1:5173`
- .NET downloader sidecar using `YoutubeExplode`
- SQLite metadata in `data/app.db`
- Audio, transcripts, and chunk files under `data/`
- Qdrant collection `youtube_notes_v1`
- Chat workspace with local Ollama models and session-only OpenAI API keys

## Prerequisites

- Python 3.11
- .NET SDK 10+
- Node 20+
- Docker
- Ollama
- FFmpeg
- NVIDIA GPU is optional but strongly recommended for Whisper

This machine already has Node, Docker, Ollama, FFmpeg, and an NVIDIA GPU. It still needs Python 3.11 before full ingestion can run.

## Setup

```powershell
Copy-Item .env.example .env
.\scripts\setup.ps1
.\scripts\start-qdrant.ps1
.\scripts\start-backend.ps1
.\scripts\start-frontend.ps1
```

Open the dashboard at:

```text
http://127.0.0.1:5173
```

## API

- `POST /api/ingestions`
- `GET /api/jobs/{job_id}`
- `GET /api/sources`
- `GET /api/sources/{source_id}`
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

The retrieval endpoint returns ranked chunks and a ready-to-use `context` string for an external chatbot.

The Chat tab stores conversations and messages in SQLite, stores manual/web context embeddings in Qdrant, can attach existing YouTube sources, and can call local Ollama models or OpenAI online models. OpenAI API keys entered in the UI are sent only for the current request and are not saved to disk.
