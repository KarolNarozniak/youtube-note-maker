---
sidebar_position: 5
title: Chat
---

# Chat

The Chat tab creates per-conversation RAG workspaces.

## Context Types

- Library source: attach an ingested video or playlist source.
- Web link: fetch readable text, chunk it, embed it, and scope it to the conversation.
- Manual note: paste local context, chunk it, embed it, and scope it to the conversation.

## Model Providers

Local models use Ollama. The app discovers installed models and includes presets for:

- `qwen3:30b`
- `deepseek-r1:8b`

OpenAI online models are available through a session-only API key field. The key is sent with the request and is not written to SQLite, Qdrant, logs, or local storage by the app.

## Retrieval

For each user message, Thothscribe:

1. Embeds the question with local Ollama embeddings.
2. Searches Qdrant using filters for the conversation’s attached context.
3. Builds a compact citation block from the top results.
4. Sends conversation history and retrieved context to the selected model.
5. Stores the user message, assistant message, selected model, and citations in SQLite.

Deleting a conversation removes its messages, context items, and chat-scoped Qdrant vectors. It does not delete shared library sources.
