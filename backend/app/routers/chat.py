from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from backend.app.dependencies import build_conversation_detail, create_chat_service, db, settings
from backend.app.schemas import (
    ChatModelInfo,
    ChatModelsResponse,
    ChatSendRequest,
    ChatSendResponse,
    ConversationContextCreateRequest,
    ConversationContextItem,
    ConversationCreateRequest,
    ConversationDetail,
    ConversationSummary,
)
from backend.app.services.chat import LOCAL_MODEL_PRESETS, OPENAI_MODEL_PRESETS
from backend.app.services.chat_clients import OllamaChatClient


router = APIRouter(prefix="/api", tags=["chat"])


@router.get("/chat/models", response_model=ChatModelsResponse)
async def list_chat_models() -> ChatModelsResponse:
    """List local and online chat model options. Takes no input and outputs model metadata with Ollama availability when known."""
    try:
        installed = await OllamaChatClient(base_url=settings.ollama_url).list_models()
    except Exception:
        installed = []

    local_ids = list(dict.fromkeys(LOCAL_MODEL_PRESETS + installed))
    return ChatModelsResponse(
        local=[
            ChatModelInfo(
                provider="ollama",
                id=model_id,
                label=model_id,
                available=(not installed) or model_id in installed,
            )
            for model_id in local_ids
        ],
        online=[
            ChatModelInfo(provider="openai", id=model_id, label=model_id, available=True)
            for model_id in OPENAI_MODEL_PRESETS
        ],
    )


@router.post(
    "/conversations",
    response_model=ConversationDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(request: ConversationCreateRequest) -> ConversationDetail:
    """Create a new chat conversation. Input is title/provider/model data; output is the full conversation detail."""
    conversation = db.create_conversation(
        title=request.title or "New conversation",
        model_provider=request.model_provider,
        model_id=request.model_id,
    )
    detail = build_conversation_detail(conversation["id"])
    if detail is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return detail


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations() -> list[ConversationSummary]:
    """List chat conversations. Takes no input and outputs summaries with message counts."""
    return [ConversationSummary(**conversation) for conversation in db.list_conversations()]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str) -> ConversationDetail:
    """Return one conversation with messages and context. Input is a conversation id; output is detail data or a 404 error."""
    detail = build_conversation_detail(conversation_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return detail


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: str) -> None:
    """Delete a conversation and its chat-scoped vectors. Input is a conversation id; output is no response body."""
    conversation = db.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        await create_chat_service().delete_conversation(conversation_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/conversations/{conversation_id}/context",
    response_model=ConversationContextItem,
    status_code=status.HTTP_201_CREATED,
)
async def add_conversation_context(
    conversation_id: str,
    request: ConversationContextCreateRequest,
) -> ConversationContextItem:
    """Attach context to a conversation. Inputs are the conversation id and context payload; output is the stored context item."""
    conversation = db.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        item = await create_chat_service().add_context(conversation_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ConversationContextItem(**item)


@router.delete(
    "/conversations/{conversation_id}/context/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_conversation_context(conversation_id: str, item_id: str) -> None:
    """Remove one context item from a conversation. Inputs are conversation and context ids; output is no response body."""
    conversation = db.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    item = db.get_context_item(item_id)
    if item is None or item["conversation_id"] != conversation_id:
        raise HTTPException(status_code=404, detail="Context item not found")

    try:
        await create_chat_service().delete_context_item(item)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatSendResponse,
)
async def send_conversation_message(
    conversation_id: str,
    request: ChatSendRequest,
) -> ChatSendResponse:
    """Send a user message through RAG and the selected model. Inputs are conversation id and message/model data; output is saved messages and citations."""
    conversation = db.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        user_message, assistant_message, citations = await create_chat_service().send_message(
            conversation=conversation,
            text=request.text,
            model_provider=request.model_provider,
            model_id=request.model_id,
            api_key=request.api_key,
            top_k=request.top_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return ChatSendResponse(
        user_message=user_message,
        assistant_message=assistant_message,
        citations=citations,
    )
