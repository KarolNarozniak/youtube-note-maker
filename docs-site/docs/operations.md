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

For the multi-app VM deployment, backend services are managed by systemd:

```bash
systemctl status thothscribe-backend
systemctl status podpisy-backend
journalctl -u thothscribe-backend -f
journalctl -u podpisy-backend -f
```

On Ubuntu, if the LAN page does not load from another machine, verify that Nginx is running and port 80 is open:

```bash
systemctl status nginx
sudo nginx -t
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

If the downloader cannot start, rebuild the sidecar:

```powershell
dotnet build downloader\YoutubeNoteDownloader\YoutubeNoteDownloader.csproj
```

Setup now also publishes the downloader to `.local/downloader` and writes `DOWNLOADER_BIN` into `.env`. If Windows Application Control blocks the generated DLL or executable, add `.local/downloader` to your trusted/excluded path if your policy allows it; strict WDAC/App Control policies may require changing the policy rather than a Defender exclusion.

If Whisper is slow, use a smaller model through the ingestion request or set `WHISPER_MODEL` in `.env`.
