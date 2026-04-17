<p align="center">
  <img src="./logo.png" alt="Thothscribe logo" width="140" />
</p>

# Thothscribe

Thothscribe is a local YouTube-to-RAG workspace. Paste a YouTube video or playlist URL, download audio locally through a small YoutubeExplode sidecar, transcribe with Whisper, chunk and embed with Ollama, store vectors in Qdrant, and chat over the resulting context.

## What This Builds

- React/Vite app on `127.0.0.1:2001`
- FastAPI backend on `127.0.0.1:2002`
- Docusaurus documentation on `127.0.0.1:2003`
- Qdrant REST on `127.0.0.1:2004`
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

## Setup On Windows

```powershell
Copy-Item .env.example .env
.\scripts\setup.ps1
```

## Setup On Ubuntu

```bash
git clone https://github.com/KarolNarozniak/youtube-note-maker.git
cd youtube-note-maker
bash scripts/install-prereqs-ubuntu.sh
# If the script says it added you to the docker group, open a new terminal or run:
newgrp docker
bash scripts/setup.sh
```

## Run On Windows

Open separate terminals:

```powershell
.\scripts\start-qdrant.ps1
.\scripts\start-backend.ps1
.\scripts\start-frontend.ps1
.\scripts\start-docs.ps1
```

Or start the app stack quickly:

```powershell
.\scripts\start-all.ps1
```

## Run On Ubuntu

```bash
bash scripts/start-all.sh
```

## Share On Your Local Network

On Ubuntu, keep Thothscribe bound to the VM and expose it through Nginx on port 80:

```bash
bash scripts/start-all.sh
sudo bash scripts/expose-lan-ubuntu.sh 10.7.183.67
```

Then open:

```text
http://10.7.183.67/
```

## Multi-App VM Deployment

For a single strong VM hosting multiple apps, use the subdomain deployment scripts:

```bash
cd ~
git clone https://github.com/KarolNarozniak/youtube-note-maker.git
git clone https://github.com/KarolNarozniak/Top_young_podpisy.git

cd ~/youtube-note-maker
git pull
bash scripts/install-prereqs-ubuntu.sh
sudo bash scripts/vm/deploy-all.sh 10.7.183.67 kzc.wat
```

Add this to each client hosts file:

```text
10.7.183.67 notes.kzc.wat docs.notes.kzc.wat podpisy.kzc.wat docs.podpisy.kzc.wat
```

Install `~/kzc-local-ca.crt` on client devices, then open:

```text
https://notes.kzc.wat
https://docs.notes.kzc.wat
https://podpisy.kzc.wat
https://docs.podpisy.kzc.wat
```

Open:

```text
http://127.0.0.1:2001
http://127.0.0.1:2003
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
