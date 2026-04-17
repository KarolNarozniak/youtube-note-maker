import React, { FormEvent, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

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

type SearchResult = {
  score: number;
  text: string;
  source_id: string;
  video_id: string;
  playlist_id: string | null;
  title: string;
  channel: string | null;
  url: string;
  start_sec: number;
  end_sec: number;
  chunk_index: number;
  language: string | null;
};

type SearchResponse = {
  query: string;
  results: SearchResult[];
  context: string;
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

function App() {
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
  const [message, setMessage] = useState<string | null>(null);

  const activeVideos = useMemo(() => selectedSource?.videos ?? [], [selectedSource]);

  const refreshSources = async () => {
    const nextSources = await api<SourceSummary[]>("/api/sources");
    setSources(nextSources);
  };

  useEffect(() => {
    refreshSources().catch((error) => setMessage(error.message));
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
    load().catch((error) => setMessage(error.message));
    const timer = window.setInterval(() => {
      load().catch((error) => setMessage(error.message));
    }, 2000);
    return () => window.clearInterval(timer);
  }, [activeJobId]);

  const submitIngestion = async (event: FormEvent) => {
    event.preventDefault();
    setMessage(null);
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
    setMessage(null);
    const detail = await api<SourceDetail>(`/api/sources/${sourceId}`);
    setSelectedSource(detail);
    setTranscript(null);
  };

  const openTranscript = async (videoId: string) => {
    setMessage(null);
    const nextTranscript = await api<Transcript>(`/api/videos/${videoId}/transcript`);
    setTranscript(nextTranscript);
  };

  const deleteSource = async (source: SourceDetail) => {
    const ok = window.confirm(`Delete "${source.title}" and all local transcripts, chunks, and vectors?`);
    if (!ok) return;
    setMessage(null);
    try {
      await apiNoContent(`/api/sources/${source.id}`, { method: "DELETE" });
      setSelectedSource(null);
      setTranscript(null);
      setSearch(null);
      await refreshSources();
      setMessage("Source deleted.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not delete source.");
    }
  };

  const runSearch = async (event: FormEvent) => {
    event.preventDefault();
    setMessage(null);
    const filters = selectedSource ? { source_id: selectedSource.id } : null;
    const nextSearch = await api<SearchResponse>("/api/search", {
      method: "POST",
      body: JSON.stringify({ query, top_k: 6, filters })
    });
    setSearch(nextSearch);
  };

  return (
    <main className="app-shell">
      <section className="submit-band">
        <div>
          <p className="eyebrow">Local ingestion</p>
          <h1>YouTube Note Maker</h1>
        </div>
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
            <input
              value={language}
              onChange={(event) => setLanguage(event.target.value)}
              placeholder="auto"
            />
          </label>
          <label className="check-row">
            <input type="checkbox" checked={force} onChange={(event) => setForce(event.target.checked)} />
            Rebuild existing data
          </label>
          <button type="submit">Start ingestion</button>
        </form>
      </section>

      {message && <p className="alert">{message}</p>}

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
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
