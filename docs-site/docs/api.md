---
sidebar_position: 6
title: API
---

# API

The backend exposes a local JSON API under `/api`.

## Library

```http
POST /api/ingestions
GET /api/jobs/{job_id}
GET /api/sources
GET /api/sources/{source_id}
DELETE /api/sources/{source_id}
GET /api/videos/{video_id}/transcript
POST /api/search
```

`POST /api/search` returns ranked chunks plus a ready-to-use `context` string for external chatbots.

## Chat

```http
GET /api/chat/models
POST /api/conversations
GET /api/conversations
GET /api/conversations/{conversation_id}
DELETE /api/conversations/{conversation_id}
POST /api/conversations/{conversation_id}/context
DELETE /api/conversations/{conversation_id}/context/{item_id}
POST /api/conversations/{conversation_id}/messages
```

## Search Request

```json
{
  "query": "What did the speaker say about retrieval?",
  "top_k": 8,
  "filters": {
    "source_id": "source-video-example"
  }
}
```

## Chat Message Request

```json
{
  "text": "Summarize the attached context.",
  "model_provider": "ollama",
  "model_id": "qwen3:30b",
  "top_k": 8
}
```

For OpenAI models, include `api_key` in the request. The backend uses it for that call only.
