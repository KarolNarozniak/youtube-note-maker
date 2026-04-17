import { FormEvent, useEffect, useState } from "react";
import { api, apiNoContent } from "../api";
import { DEFAULT_LOCAL_MODEL } from "../constants";
import type {
  ChatModels,
  ContextItem,
  ConversationDetail,
  ConversationSummary,
  Provider,
  SourceSummary
} from "../types";
import { formatDate } from "../utils";

type ChatViewProps = {
  setGlobalMessage: (message: string | null) => void;
};

export function ChatView({ setGlobalMessage }: ChatViewProps) {
  const [models, setModels] = useState<ChatModels>({ local: [], online: [] });
  const [sources, setSources] = useState<SourceSummary[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversation, setActiveConversation] = useState<ConversationDetail | null>(null);
  const [conversationFilter, setConversationFilter] = useState("");
  const [provider, setProvider] = useState<Provider>("ollama");
  const [modelId, setModelId] = useState(DEFAULT_LOCAL_MODEL);
  const [customModelId, setCustomModelId] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [prompt, setPrompt] = useState("");
  const [contextKind, setContextKind] = useState<"source" | "web" | "manual">("source");
  const [sourceId, setSourceId] = useState("");
  const [webUrl, setWebUrl] = useState("");
  const [manualTitle, setManualTitle] = useState("");
  const [manualText, setManualText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isAddingContext, setIsAddingContext] = useState(false);

  const providerModels = provider === "ollama" ? models.local : models.online;
  const chosenModelId = customModelId.trim() || modelId;
  const visibleConversations = conversations.filter((conversation) =>
    conversation.title.toLowerCase().includes(conversationFilter.toLowerCase())
  );

  const loadConversations = async () => {
    const next = await api<ConversationSummary[]>("/api/conversations");
    setConversations(next);
  };

  const loadConversation = async (conversationId: string) => {
    const detail = await api<ConversationDetail>(`/api/conversations/${conversationId}`);
    setActiveConversation(detail);
    setProvider(detail.model_provider);
    setModelId(detail.model_id);
  };

  useEffect(() => {
    api<ChatModels>("/api/chat/models").then(setModels).catch((error) => setGlobalMessage(error.message));
    api<SourceSummary[]>("/api/sources").then(setSources).catch((error) => setGlobalMessage(error.message));
    loadConversations().catch((error) => setGlobalMessage(error.message));
  }, []);

  useEffect(() => {
    const next = provider === "ollama" ? models.local[0]?.id : models.online[0]?.id;
    if (next && !providerModels.some((model) => model.id === modelId)) {
      setModelId(next);
    }
  }, [provider, models.local, models.online]);

  const createConversation = async () => {
    setGlobalMessage(null);
    const detail = await api<ConversationDetail>("/api/conversations", {
      method: "POST",
      body: JSON.stringify({
        model_provider: provider,
        model_id: chosenModelId
      })
    });
    setActiveConversation(detail);
    await loadConversations();
  };

  const deleteConversation = async (conversation: ConversationDetail) => {
    const ok = window.confirm(`Delete "${conversation.title}" and its chat-specific context?`);
    if (!ok) return;
    await apiNoContent(`/api/conversations/${conversation.id}`, { method: "DELETE" });
    setActiveConversation(null);
    await loadConversations();
  };

  const addContext = async (event: FormEvent) => {
    event.preventDefault();
    if (!activeConversation) return;
    setIsAddingContext(true);
    setGlobalMessage(null);
    try {
      await api<ContextItem>(`/api/conversations/${activeConversation.id}/context`, {
        method: "POST",
        body: JSON.stringify(buildContextRequest(contextKind, sourceId, webUrl, manualTitle, manualText))
      });
      setWebUrl("");
      setManualTitle("");
      setManualText("");
      await loadConversation(activeConversation.id);
      await loadConversations();
    } catch (error) {
      setGlobalMessage(error instanceof Error ? error.message : "Could not add context.");
    } finally {
      setIsAddingContext(false);
    }
  };

  const removeContext = async (item: ContextItem) => {
    if (!activeConversation) return;
    await apiNoContent(`/api/conversations/${activeConversation.id}/context/${item.id}`, { method: "DELETE" });
    await loadConversation(activeConversation.id);
  };

  const sendMessage = async (event: FormEvent) => {
    event.preventDefault();
    setGlobalMessage(null);
    let conversation = activeConversation;
    if (!conversation) {
      conversation = await api<ConversationDetail>("/api/conversations", {
        method: "POST",
        body: JSON.stringify({ model_provider: provider, model_id: chosenModelId })
      });
      setActiveConversation(conversation);
    }
    if (provider === "openai" && !apiKey.trim()) {
      setGlobalMessage("Paste an OpenAI API key for online models.");
      return;
    }
    setIsSending(true);
    try {
      await api(`/api/conversations/${conversation.id}/messages`, {
        method: "POST",
        body: JSON.stringify({
          text: prompt,
          model_provider: provider,
          model_id: chosenModelId,
          api_key: provider === "openai" ? apiKey : null,
          top_k: 8
        })
      });
      setPrompt("");
      await loadConversation(conversation.id);
      await loadConversations();
    } catch (error) {
      setGlobalMessage(error instanceof Error ? error.message : "Could not send message.");
    } finally {
      setIsSending(false);
    }
  };

  return (
    <section className="chat-layout">
      <ConversationSidebar
        activeConversation={activeConversation}
        conversations={visibleConversations}
        conversationFilter={conversationFilter}
        setConversationFilter={setConversationFilter}
        createConversation={createConversation}
        loadConversation={loadConversation}
      />
      <ChatMainPanel
        activeConversation={activeConversation}
        provider={provider}
        modelId={modelId}
        customModelId={customModelId}
        apiKey={apiKey}
        prompt={prompt}
        providerModels={providerModels}
        isSending={isSending}
        setProvider={setProvider}
        setModelId={setModelId}
        setCustomModelId={setCustomModelId}
        setApiKey={setApiKey}
        setPrompt={setPrompt}
        deleteConversation={deleteConversation}
        sendMessage={sendMessage}
      />
      <ContextRail
        activeConversation={activeConversation}
        sources={sources}
        contextKind={contextKind}
        sourceId={sourceId}
        webUrl={webUrl}
        manualTitle={manualTitle}
        manualText={manualText}
        isAddingContext={isAddingContext}
        setContextKind={setContextKind}
        setSourceId={setSourceId}
        setWebUrl={setWebUrl}
        setManualTitle={setManualTitle}
        setManualText={setManualText}
        addContext={addContext}
        removeContext={removeContext}
      />
    </section>
  );
}

function buildContextRequest(
  contextKind: "source" | "web" | "manual",
  sourceId: string,
  webUrl: string,
  manualTitle: string,
  manualText: string
) {
  if (contextKind === "source") return { type: "source", source_id: sourceId };
  if (contextKind === "web") return { type: "web", url: webUrl };
  return { type: "manual", title: manualTitle || "Manual note", text: manualText };
}

type ConversationSidebarProps = {
  activeConversation: ConversationDetail | null;
  conversations: ConversationSummary[];
  conversationFilter: string;
  setConversationFilter: (value: string) => void;
  createConversation: () => Promise<void>;
  loadConversation: (conversationId: string) => Promise<void>;
};

function ConversationSidebar({
  activeConversation,
  conversations,
  conversationFilter,
  setConversationFilter,
  createConversation,
  loadConversation
}: ConversationSidebarProps) {
  return (
    <aside className="chat-sidebar">
      <div className="panel-heading">
        <h2>Chats</h2>
        <button type="button" onClick={() => void createConversation()}>
          New
        </button>
      </div>
      <input
        value={conversationFilter}
        onChange={(event) => setConversationFilter(event.target.value)}
        placeholder="Search chats"
      />
      <div className="conversation-list">
        {conversations.map((conversation) => (
          <button
            type="button"
            className={`conversation-card ${activeConversation?.id === conversation.id ? "selected" : ""}`}
            key={conversation.id}
            onClick={() => void loadConversation(conversation.id)}
          >
            <strong>{conversation.title}</strong>
            <span>{conversation.message_count} messages</span>
            <small>{formatDate(conversation.updated_at)}</small>
          </button>
        ))}
        {conversations.length === 0 && <p className="muted">No conversations yet.</p>}
      </div>
    </aside>
  );
}

type ChatMainPanelProps = {
  activeConversation: ConversationDetail | null;
  provider: Provider;
  modelId: string;
  customModelId: string;
  apiKey: string;
  prompt: string;
  providerModels: { id: string; label: string; available: boolean }[];
  isSending: boolean;
  setProvider: (value: Provider) => void;
  setModelId: (value: string) => void;
  setCustomModelId: (value: string) => void;
  setApiKey: (value: string) => void;
  setPrompt: (value: string) => void;
  deleteConversation: (conversation: ConversationDetail) => Promise<void>;
  sendMessage: (event: FormEvent) => Promise<void>;
};

function ChatMainPanel(props: ChatMainPanelProps) {
  return (
    <section className="chat-main">
      <div className="chat-header">
        <div>
          <h2>{props.activeConversation?.title ?? "New conversation"}</h2>
          <p className="muted">Ask over attached playlists, videos, web links, and notes.</p>
        </div>
        {props.activeConversation && (
          <button type="button" className="danger" onClick={() => void props.deleteConversation(props.activeConversation!)}>
            Delete chat
          </button>
        )}
      </div>

      <ModelSelector {...props} />

      <div className="message-thread">
        {props.activeConversation?.messages.length ? (
          props.activeConversation.messages.map((message) => (
            <article className={`message ${message.role}`} key={message.id}>
              <div className="message-meta">
                <strong>{message.role === "user" ? "You" : message.model_id ?? "Assistant"}</strong>
                <span>{formatDate(message.created_at)}</span>
              </div>
              <p>{message.text}</p>
              {message.citations.length > 0 && (
                <div className="citations">
                  {message.citations.map((citation) => (
                    <a href={citation.url ?? undefined} target="_blank" rel="noreferrer" key={citation.index}>
                      [{citation.index}] {citation.title}
                    </a>
                  ))}
                </div>
              )}
            </article>
          ))
        ) : (
          <div className="empty-thread">
            <h2>Build a focused chat</h2>
            <p className="muted">Create or select a conversation, attach context, then ask a question.</p>
          </div>
        )}
      </div>

      <form className="composer" onSubmit={(event) => void props.sendMessage(event)}>
        <textarea
          value={props.prompt}
          onChange={(event) => props.setPrompt(event.target.value)}
          placeholder="Ask a question about the attached context"
          required
        />
        <button type="submit" disabled={props.isSending}>
          {props.isSending ? "Thinking..." : "Send"}
        </button>
      </form>
    </section>
  );
}

function ModelSelector(props: ChatMainPanelProps) {
  return (
    <div className="model-row">
      <label>
        Provider
        <select value={props.provider} onChange={(event) => props.setProvider(event.target.value as Provider)}>
          <option value="ollama">Ollama local</option>
          <option value="openai">OpenAI online</option>
        </select>
      </label>
      <label>
        Model
        <select value={props.modelId} onChange={(event) => props.setModelId(event.target.value)}>
          {props.providerModels.map((model) => (
            <option value={model.id} key={model.id}>
              {model.label}{model.available ? "" : " unavailable"}
            </option>
          ))}
        </select>
      </label>
      <label>
        Custom model
        <input
          value={props.customModelId}
          onChange={(event) => props.setCustomModelId(event.target.value)}
          placeholder={props.provider === "openai" ? "gpt-5.4" : "optional"}
        />
      </label>
      {props.provider === "openai" && (
        <label>
          API key
          <input
            value={props.apiKey}
            onChange={(event) => props.setApiKey(event.target.value)}
            placeholder="Session only"
            type="password"
          />
        </label>
      )}
    </div>
  );
}

type ContextRailProps = {
  activeConversation: ConversationDetail | null;
  sources: SourceSummary[];
  contextKind: "source" | "web" | "manual";
  sourceId: string;
  webUrl: string;
  manualTitle: string;
  manualText: string;
  isAddingContext: boolean;
  setContextKind: (value: "source" | "web" | "manual") => void;
  setSourceId: (value: string) => void;
  setWebUrl: (value: string) => void;
  setManualTitle: (value: string) => void;
  setManualText: (value: string) => void;
  addContext: (event: FormEvent) => Promise<void>;
  removeContext: (item: ContextItem) => Promise<void>;
};

function ContextRail(props: ContextRailProps) {
  return (
    <aside className="context-rail">
      <div className="panel-heading">
        <h2>Context</h2>
        <span className="pill">{props.activeConversation?.context_items.length ?? 0}</span>
      </div>
      <ContextForm {...props} />
      <div className="context-list">
        {props.activeConversation?.context_items.map((item) => (
          <article className="context-item" key={item.id}>
            <div>
              <strong>{item.title}</strong>
              <span>{item.type} / {item.status}</span>
              {item.error && <small>{item.error}</small>}
            </div>
            <button type="button" className="secondary" onClick={() => void props.removeContext(item)}>
              Remove
            </button>
          </article>
        ))}
        {!props.activeConversation && <p className="muted">Select or create a chat first.</p>}
      </div>
    </aside>
  );
}

function ContextForm(props: ContextRailProps) {
  return (
    <form className="context-form" onSubmit={(event) => void props.addContext(event)}>
      <label>
        Type
        <select value={props.contextKind} onChange={(event) => props.setContextKind(event.target.value as typeof props.contextKind)}>
          <option value="source">Library source</option>
          <option value="web">Web link</option>
          <option value="manual">Manual note</option>
        </select>
      </label>
      {props.contextKind === "source" && (
        <label>
          Source
          <select value={props.sourceId} onChange={(event) => props.setSourceId(event.target.value)} required>
            <option value="">Choose source</option>
            {props.sources.map((source) => (
              <option value={source.id} key={source.id}>
                {source.title}
              </option>
            ))}
          </select>
        </label>
      )}
      {props.contextKind === "web" && (
        <label>
          URL
          <input value={props.webUrl} onChange={(event) => props.setWebUrl(event.target.value)} placeholder="https://..." required />
        </label>
      )}
      {props.contextKind === "manual" && (
        <>
          <label>
            Title
            <input value={props.manualTitle} onChange={(event) => props.setManualTitle(event.target.value)} placeholder="Note title" />
          </label>
          <label>
            Text
            <textarea value={props.manualText} onChange={(event) => props.setManualText(event.target.value)} required />
          </label>
        </>
      )}
      <button type="submit" disabled={!props.activeConversation || props.isAddingContext}>
        {props.isAddingContext ? "Adding..." : "Add context"}
      </button>
    </form>
  );
}
