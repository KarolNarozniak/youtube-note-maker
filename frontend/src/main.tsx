import React, { FormEvent, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Tab = "library" | "chat";
type Theme = "light" | "dark";
type Provider = "ollama" | "openai";

type Job = {
  id: string;
  url: string;
  language: string | null;
  whisper_model: string;
  force: boolean;
  status: "queued" | "running" | "completed" | "partial" | "failed";
  stage: string;
  progress: number;
  current_video: string | null;
  errors: string[];
  source_ids: string[];
  video_ids: string[];
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
};

type SourceSummary = {
  id: string;
  type: string;
  url: string;
  title: string;
  playlist_id: string | null;
  channel: string | null;
  video_count: number;
  job_id: string;
  created_at: string;
  updated_at: string;
};

type VideoSummary = {
  id: string;
  source_id: string;
  youtube_id: string;
  playlist_id: string | null;
  url: string;
  title: string;
  channel: string | null;
  duration_sec: number | null;
  audio_path: string | null;
  transcript_json_path: string | null;
  transcript_txt_path: string | null;
  transcript_srt_path: string | null;
  language: string | null;
  status: string;
  error: string | null;
  chunk_count: number;
  created_at: string;
  updated_at: string;
};

type SourceDetail = SourceSummary & {
  videos: VideoSummary[];
};

type Transcript = {
  video_id: string;
  text: string;
  language: string | null;
  segments: { id: number; start: number; end: number; text: string }[];
};

type SearchResponse = {
  query: string;
  results: unknown[];
  context: string;
};

type ChatModel = {
  provider: Provider;
  id: string;
  label: string;
  available: boolean;
};

type ChatModels = {
  local: ChatModel[];
  online: ChatModel[];
};

type ConversationSummary = {
  id: string;
  title: string;
  model_provider: Provider;
  model_id: string;
  created_at: string;
  updated_at: string;
  last_message: string | null;
  message_count: number;
};

type Citation = {
  index: number;
  title: string;
  text: string;
  score: number;
  url: string | null;
  source_id: string | null;
  video_id: string | null;
  playlist_id: string | null;
  context_item_id: string | null;
  context_type: string | null;
  start_sec: number | null;
  end_sec: number | null;
};

type ChatMessage = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  text: string;
  citations: Citation[];
  model_provider: Provider | null;
  model_id: string | null;
  created_at: string;
};

type ContextItem = {
  id: string;
  conversation_id: string;
  type: "manual" | "web" | "source" | "video" | "playlist";
  title: string;
  url: string | null;
  text: string | null;
  source_id: string | null;
  video_id: string | null;
  playlist_id: string | null;
  status: string;
  error: string | null;
  created_at: string;
  updated_at: string;
};

type ConversationDetail = ConversationSummary & {
  messages: ChatMessage[];
  context_items: ContextItem[];
};

const api = async <T,>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  return response.json() as Promise<T>;
};

const apiNoContent = async (path: string, init?: RequestInit): Promise<void> => {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
};

const timestamp = (seconds: number): string => {
  const total = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  if (hours) return `${hours}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  return `${minutes}:${String(secs).padStart(2, "0")}`;
};

const thumbnail = (youtubeId: string): string => `https://i.ytimg.com/vi/${youtubeId}/hqdefault.jpg`;

const formatDate = (value: string): string => new Date(value).toLocaleString();

function App() {
  const [tab, setTab] = useState<Tab>("library");
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem("theme") as Theme) || "light");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Local RAG workspace</p>
          <h1>Context Studio</h1>
        </div>
        <div className="topbar-actions">
          <nav className="tabs" aria-label="Main sections">
            <button className={tab === "library" ? "active" : ""} type="button" onClick={() => setTab("library")}>
              Library
            </button>
            <button className={tab === "chat" ? "active" : ""} type="button" onClick={() => setTab("chat")}>
              Chat
            </button>
          </nav>
          <button
            className="theme-toggle"
            type="button"
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
          >
            {theme === "light" ? "Dark" : "Light"}
          </button>
        </div>
      </header>

      {message && <p className="alert">{message}</p>}

      {tab === "library" ? (
        <LibraryView setGlobalMessage={setMessage} />
      ) : (
        <ChatView setGlobalMessage={setMessage} />
      )}
    </main>
  );
}

function LibraryView({ setGlobalMessage }: { setGlobalMessage: (message: string | null) => void }) {
  const [url, setUrl] = useState("");
  const [language, setLanguage] = useState("");
  const [force, setForce] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [sources, setSources] = useState<SourceSummary[]>([]);
  const [selectedSource, setSelectedSource] = useState<SourceDetail | null>(null);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState<SearchResponse | null>(null);
  const activeVideos = useMemo(() => selectedSource?.videos ?? [], [selectedSource]);

  const refreshSources = async () => {
    const nextSources = await api<SourceSummary[]>("/api/sources");
    setSources(nextSources);
  };

  useEffect(() => {
    refreshSources().catch((error) => setGlobalMessage(error.message));
  }, []);

  useEffect(() => {
    if (!activeJobId) return;
    const load = async () => {
      const nextJob = await api<Job>(`/api/jobs/${activeJobId}`);
      setJob(nextJob);
      if (["completed", "partial", "failed"].includes(nextJob.status)) {
        await refreshSources();
      }
    };
    load().catch((error) => setGlobalMessage(error.message));
    const timer = window.setInterval(() => {
      load().catch((error) => setGlobalMessage(error.message));
    }, 2000);
    return () => window.clearInterval(timer);
  }, [activeJobId]);

  const submitIngestion = async (event: FormEvent) => {
    event.preventDefault();
    setGlobalMessage(null);
    setTranscript(null);
    setSearch(null);
    const response = await api<{ job_id: string; status: string }>("/api/ingestions", {
      method: "POST",
      body: JSON.stringify({
        url,
        language: language.trim() || null,
        force
      })
    });
    setActiveJobId(response.job_id);
    setUrl("");
  };

  const openSource = async (sourceId: string) => {
    setGlobalMessage(null);
    const detail = await api<SourceDetail>(`/api/sources/${sourceId}`);
    setSelectedSource(detail);
    setTranscript(null);
  };

  const openTranscript = async (videoId: string) => {
    setGlobalMessage(null);
    const nextTranscript = await api<Transcript>(`/api/videos/${videoId}/transcript`);
    setTranscript(nextTranscript);
  };

  const deleteSource = async (source: SourceDetail) => {
    const ok = window.confirm(`Delete "${source.title}" and all local transcripts, chunks, and vectors?`);
    if (!ok) return;
    setGlobalMessage(null);
    try {
      await apiNoContent(`/api/sources/${source.id}`, { method: "DELETE" });
      setSelectedSource(null);
      setTranscript(null);
      setSearch(null);
      await refreshSources();
      setGlobalMessage("Source deleted.");
    } catch (error) {
      setGlobalMessage(error instanceof Error ? error.message : "Could not delete source.");
    }
  };

  const runSearch = async (event: FormEvent) => {
    event.preventDefault();
    setGlobalMessage(null);
    const filters = selectedSource ? { source_id: selectedSource.id } : null;
    const nextSearch = await api<SearchResponse>("/api/search", {
      method: "POST",
      body: JSON.stringify({ query, top_k: 6, filters })
    });
    setSearch(nextSearch);
  };

  return (
    <section className="library-layout">
      <section className="band">
        <form className="ingest-form" onSubmit={(event) => void submitIngestion(event)}>
          <label>
            YouTube URL
            <input
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              required
            />
          </label>
          <label>
            Language
            <input value={language} onChange={(event) => setLanguage(event.target.value)} placeholder="auto" />
          </label>
          <label className="check-row">
            <input type="checkbox" checked={force} onChange={(event) => setForce(event.target.checked)} />
            Rebuild
          </label>
          <button type="submit">Start ingestion</button>
        </form>
      </section>

      <section className="grid">
        <div className="panel">
          <div className="panel-heading">
            <h2>Job</h2>
            {job && <span className={`status ${job.status}`}>{job.status}</span>}
          </div>
          {job ? (
            <div className="job-card">
              <p>{job.stage}</p>
              <progress value={job.progress} max={1} />
              <p className="muted">{job.current_video ?? "Waiting for work"}</p>
              {job.errors.length > 0 && (
                <ul className="errors">
                  {job.errors.map((error) => (
                    <li key={error}>{error}</li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <p className="muted">No active job.</p>
          )}
        </div>

        <div className="panel">
          <div className="panel-heading">
            <h2>Search</h2>
            {selectedSource && <span className="pill">{selectedSource.title}</span>}
          </div>
          <form className="search-form" onSubmit={(event) => void runSearch(event)}>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ask for a topic, claim, or timestamp"
              required
            />
            <button type="submit">Retrieve</button>
          </form>
          {search && (
            <div className="context-box">
              <h3>Context</h3>
              <pre>{search.context}</pre>
            </div>
          )}
        </div>
      </section>

      <section className="workspace">
        <aside className="source-list">
          <div className="panel-heading">
            <h2>Sources</h2>
            <button type="button" className="secondary" onClick={() => void refreshSources()}>
              Refresh
            </button>
          </div>
          {sources.length === 0 ? (
            <p className="muted">No sources yet.</p>
          ) : (
            sources.map((source) => (
              <button
                type="button"
                className={`source-card ${selectedSource?.id === source.id ? "selected" : ""}`}
                key={source.id}
                onClick={() => void openSource(source.id)}
              >
                <strong>{source.title}</strong>
                <span>{source.video_count} video{source.video_count === 1 ? "" : "s"}</span>
              </button>
            ))
          )}
        </aside>

        <section className="detail-panel">
          {selectedSource ? (
            <>
              <div className="panel-heading">
                <div>
                  <h2>{selectedSource.title}</h2>
                  <p className="muted">{selectedSource.channel ?? selectedSource.type}</p>
                </div>
                <div className="detail-actions">
                  <a href={selectedSource.url} target="_blank" rel="noreferrer">
                    Open
                  </a>
                  <button type="button" className="danger" onClick={() => void deleteSource(selectedSource)}>
                    Delete
                  </button>
                </div>
              </div>
              <div className="video-grid">
                {activeVideos.map((video) => (
                  <article className="video-card" key={video.id}>
                    <img src={thumbnail(video.youtube_id)} alt="" loading="lazy" />
                    <div>
                      <h3>{video.title}</h3>
                      <p className="muted">
                        {video.status} / {video.chunk_count} chunks
                      </p>
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => void openTranscript(video.id)}
                        disabled={!video.transcript_json_path}
                      >
                        Transcript
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </>
          ) : (
            <p className="muted">Choose a source.</p>
          )}
        </section>
      </section>

      {transcript && (
        <section className="transcript-panel">
          <div className="panel-heading">
            <h2>Transcript</h2>
            <span className="pill">{transcript.language ?? "auto"}</span>
          </div>
          <div className="segments">
            {transcript.segments.map((segment) => (
              <p key={segment.id}>
                <span>{timestamp(segment.start)}</span>
                {segment.text}
              </p>
            ))}
          </div>
        </section>
      )}
    </section>
  );
}

function ChatView({ setGlobalMessage }: { setGlobalMessage: (message: string | null) => void }) {
  const [models, setModels] = useState<ChatModels>({ local: [], online: [] });
  const [sources, setSources] = useState<SourceSummary[]>([]);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversation, setActiveConversation] = useState<ConversationDetail | null>(null);
  const [conversationFilter, setConversationFilter] = useState("");
  const [provider, setProvider] = useState<Provider>("ollama");
  const [modelId, setModelId] = useState("qwen3:30b");
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

  const visibleConversations = conversations.filter((conversation) =>
    conversation.title.toLowerCase().includes(conversationFilter.toLowerCase())
  );
  const providerModels = provider === "ollama" ? models.local : models.online;
  const chosenModelId = customModelId.trim() || modelId;

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
      const body =
        contextKind === "source"
          ? { type: "source", source_id: sourceId }
          : contextKind === "web"
            ? { type: "web", url: webUrl }
            : { type: "manual", title: manualTitle || "Manual note", text: manualText };
      await api<ContextItem>(`/api/conversations/${activeConversation.id}/context`, {
        method: "POST",
        body: JSON.stringify(body)
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
          {visibleConversations.map((conversation) => (
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
          {visibleConversations.length === 0 && <p className="muted">No conversations yet.</p>}
        </div>
      </aside>

      <section className="chat-main">
        <div className="chat-header">
          <div>
            <h2>{activeConversation?.title ?? "New conversation"}</h2>
            <p className="muted">Ask over attached playlists, videos, web links, and notes.</p>
          </div>
          {activeConversation && (
            <button type="button" className="danger" onClick={() => void deleteConversation(activeConversation)}>
              Delete chat
            </button>
          )}
        </div>

        <div className="model-row">
          <label>
            Provider
            <select value={provider} onChange={(event) => setProvider(event.target.value as Provider)}>
              <option value="ollama">Ollama local</option>
              <option value="openai">OpenAI online</option>
            </select>
          </label>
          <label>
            Model
            <select value={modelId} onChange={(event) => setModelId(event.target.value)}>
              {providerModels.map((model) => (
                <option value={model.id} key={`${model.provider}-${model.id}`}>
                  {model.label}{model.available ? "" : " unavailable"}
                </option>
              ))}
            </select>
          </label>
          <label>
            Custom model
            <input
              value={customModelId}
              onChange={(event) => setCustomModelId(event.target.value)}
              placeholder={provider === "openai" ? "gpt-5.4" : "optional"}
            />
          </label>
          {provider === "openai" && (
            <label>
              API key
              <input
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                placeholder="Session only"
                type="password"
              />
            </label>
          )}
        </div>

        <div className="message-thread">
          {activeConversation?.messages.length ? (
            activeConversation.messages.map((message) => (
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

        <form className="composer" onSubmit={(event) => void sendMessage(event)}>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder="Ask a question about the attached context"
            required
          />
          <button type="submit" disabled={isSending}>
            {isSending ? "Thinking..." : "Send"}
          </button>
        </form>
      </section>

      <aside className="context-rail">
        <div className="panel-heading">
          <h2>Context</h2>
          <span className="pill">{activeConversation?.context_items.length ?? 0}</span>
        </div>
        <form className="context-form" onSubmit={(event) => void addContext(event)}>
          <label>
            Type
            <select value={contextKind} onChange={(event) => setContextKind(event.target.value as typeof contextKind)}>
              <option value="source">Library source</option>
              <option value="web">Web link</option>
              <option value="manual">Manual note</option>
            </select>
          </label>
          {contextKind === "source" && (
            <label>
              Source
              <select value={sourceId} onChange={(event) => setSourceId(event.target.value)} required>
                <option value="">Choose source</option>
                {sources.map((source) => (
                  <option value={source.id} key={source.id}>
                    {source.title}
                  </option>
                ))}
              </select>
            </label>
          )}
          {contextKind === "web" && (
            <label>
              URL
              <input value={webUrl} onChange={(event) => setWebUrl(event.target.value)} placeholder="https://..." required />
            </label>
          )}
          {contextKind === "manual" && (
            <>
              <label>
                Title
                <input value={manualTitle} onChange={(event) => setManualTitle(event.target.value)} placeholder="Note title" />
              </label>
              <label>
                Text
                <textarea value={manualText} onChange={(event) => setManualText(event.target.value)} required />
              </label>
            </>
          )}
          <button type="submit" disabled={!activeConversation || isAddingContext}>
            {isAddingContext ? "Adding..." : "Add context"}
          </button>
        </form>
        <div className="context-list">
          {activeConversation?.context_items.map((item) => (
            <article className="context-item" key={item.id}>
              <div>
                <strong>{item.title}</strong>
                <span>{item.type} / {item.status}</span>
                {item.error && <small>{item.error}</small>}
              </div>
              <button type="button" className="secondary" onClick={() => void removeContext(item)}>
                Remove
              </button>
            </article>
          ))}
          {!activeConversation && <p className="muted">Select or create a chat first.</p>}
        </div>
      </aside>
    </section>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
