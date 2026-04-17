---
sidebar_position: 2
title: Architecture
---

# Architecture

Thothscribe is split into small local services with one FastAPI backend coordinating the work.

```text
React/Vite UI
  |
  | HTTP /api
  v
FastAPI backend
  |-- SQLite app.db for jobs, sources, videos, conversations, messages, context items
  |-- .NET downloader sidecar using YoutubeExplode
  |-- Whisper transcriber running locally
  |-- Ollama embedding and chat APIs
  |-- Qdrant vector database
  v
data/
  |-- transcripts/
  |-- chunks/
  |-- app.db
```

## Backend

The backend binds to `127.0.0.1:2002` by default. `backend/app/main.py` only creates the FastAPI app, starts the ingestion worker, and mounts focused routers:

- `backend/app/routers/library.py` handles ingestion, sources, transcripts, deletion, and search.
- `backend/app/routers/chat.py` handles model discovery, conversations, context items, and chat messages.
- `backend/app/dependencies.py` centralizes settings, SQLite, Qdrant, Ollama, and service construction.

## Frontend

The frontend is a React/Vite app at `127.0.0.1:2001`.

- `frontend/src/App.tsx` owns the top-level tabs, branding, and theme toggle.
- `frontend/src/views/LibraryView.tsx` contains the ingestion and source browsing workspace.
- `frontend/src/views/ChatView.tsx` contains the conversation workspace.
- Shared types, API helpers, constants, and utilities live in their own files.
- Styles are split into base, library, and chat styles under `frontend/src/styles/`.

## Vector Data

Qdrant stores both library chunks and chat-specific context chunks in the same collection. Payload fields separate scope:

- `scope=library` for YouTube transcript chunks.
- `scope=chat` for manual and web context chunks attached to one conversation.

This keeps retrieval simple while preserving clean deletion rules.
