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
- Docker Desktop on Windows, or Docker Engine on Linux
- Ollama
- FFmpeg
- NVIDIA GPU optional, but strongly recommended for Whisper

## Install On Windows

```powershell
Copy-Item .env.example .env
.\scripts\setup.ps1
```

## Install On Ubuntu

```bash
git clone https://github.com/KarolNarozniak/youtube-note-maker.git
cd youtube-note-maker
bash scripts/install-prereqs-ubuntu.sh
# If the script says it added you to the docker group, open a new terminal or run:
newgrp docker
bash scripts/setup.sh
```

The setup scripts create the Python virtual environment, install backend packages, restore/build/publish the downloader sidecar, install the frontend, install the documentation site, pull `embeddinggemma`, and pull the Qdrant image.

## Start Services

Open separate terminals:

```powershell
.\scripts\start-qdrant.ps1
.\scripts\start-backend.ps1
.\scripts\start-frontend.ps1
.\scripts\start-docs.ps1
```

Or start the stack in one command:

```powershell
.\scripts\start-all.ps1
```

On Ubuntu:

```bash
bash scripts/start-all.sh
```

## Share On Your Local Network

On an Ubuntu VM, expose the app at the VM's private-network IP through Nginx:

```bash
bash scripts/start-all.sh
sudo bash scripts/expose-lan-ubuntu.sh 10.7.183.67
```

The script installs Nginx if needed, writes a `thothscribe` site, proxies `/api` to the FastAPI backend, proxies everything else to the frontend, and adds `http://10.7.183.67` to `ALLOWED_ORIGINS` in `.env`.

Open:

```text
http://10.7.183.67/
```

For hosting multiple apps on one VM, use the subdomain deployment in [Multi-App VM](./vm-deployment.md).

Use these local URLs:

- App: `http://127.0.0.1:2001`
- Backend API: `http://127.0.0.1:2002`
- Documentation: `http://127.0.0.1:2003`
- Qdrant dashboard/API: `http://127.0.0.1:2004`
