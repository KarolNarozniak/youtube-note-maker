---
sidebar_position: 1
title: Overview
---

<img src="/img/logo.png" alt="Thothscribe logo" width="120" />

# Thothscribe

Thothscribe is a local web application for turning YouTube videos, playlists, manual notes, and web pages into retrieval-ready context.

The first screen is the working app: ingest sources in the Library tab, then attach those sources to Chat conversations. Transcripts, chat metadata, and vector payloads stay local by default.

## What It Does

- Downloads YouTube audio through the .NET downloader sidecar.
- Transcribes audio with local Whisper.
- Stores full transcript artifacts as JSON, TXT, and SRT files.
- Chunks timestamped transcript segments and embeds them with Ollama `embeddinggemma`.
- Stores vectors and citation payloads in Qdrant.
- Keeps ingestion, source, chat, and context metadata in SQLite.
- Lets each chat attach library sources, web links, and manual notes.
- Supports local Ollama chat models and optional OpenAI online models with session-only API keys.

## Storage Promise

Audio files are temporary in the current pipeline. After a video is transcribed, chunked, embedded, and written to Qdrant, the local audio file is deleted. Transcripts, chunk metadata, SQLite rows, and Qdrant vectors remain until you delete the source or conversation.
