---
sidebar_position: 3
title: Setup
---

# Setup

Run the commands from the repository root.

## Requirements

- Python 3.11
- .NET SDK 10 or newer
- Node.js 20 or newer
- Docker Desktop
- Ollama
- FFmpeg
- NVIDIA GPU optional, but strongly recommended for Whisper

## Install

```powershell
Copy-Item .env.example .env
.\scripts\setup.ps1
```

The setup script creates the Python virtual environment, installs backend packages, restores and builds the downloader sidecar, installs the frontend, installs the documentation site, pulls `embeddinggemma`, and pulls the Qdrant image.

## Start Services

Open separate terminals:

```powershell
.\scripts\start-qdrant.ps1
.\scripts\start-backend.ps1
.\scripts\start-frontend.ps1
.\scripts\start-docs.ps1
```

Use these local URLs:

- App: `http://127.0.0.1:5173`
- Backend API: `http://127.0.0.1:8000`
- Documentation: `http://127.0.0.1:3000`
- Qdrant dashboard/API: `http://127.0.0.1:6333`
