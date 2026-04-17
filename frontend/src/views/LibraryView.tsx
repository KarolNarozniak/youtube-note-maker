import { FormEvent, useEffect, useMemo, useState } from "react";
import { api, apiNoContent } from "../api";
import type { Job, SearchResponse, SourceDetail, SourceSummary, Transcript } from "../types";
import { thumbnail, timestamp } from "../utils";

type LibraryViewProps = {
  setGlobalMessage: (message: string | null) => void;
};

export function LibraryView({ setGlobalMessage }: LibraryViewProps) {
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
        <JobPanel job={job} />
        <LibrarySearchPanel
          query={query}
          search={search}
          selectedSource={selectedSource}
          setQuery={setQuery}
          runSearch={runSearch}
        />
      </section>

      <section className="workspace">
        <SourceSidebar
          sources={sources}
          selectedSource={selectedSource}
          refreshSources={refreshSources}
          openSource={openSource}
        />
        <SourceDetailPanel
          selectedSource={selectedSource}
          activeVideos={activeVideos}
          openTranscript={openTranscript}
          deleteSource={deleteSource}
        />
      </section>

      {transcript && <TranscriptPanel transcript={transcript} />}
    </section>
  );
}

function JobPanel({ job }: { job: Job | null }) {
  return (
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
  );
}

type LibrarySearchPanelProps = {
  query: string;
  search: SearchResponse | null;
  selectedSource: SourceDetail | null;
  setQuery: (query: string) => void;
  runSearch: (event: FormEvent) => void;
};

function LibrarySearchPanel({ query, search, selectedSource, setQuery, runSearch }: LibrarySearchPanelProps) {
  return (
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
  );
}

type SourceSidebarProps = {
  sources: SourceSummary[];
  selectedSource: SourceDetail | null;
  refreshSources: () => Promise<void>;
  openSource: (sourceId: string) => Promise<void>;
};

function SourceSidebar({ sources, selectedSource, refreshSources, openSource }: SourceSidebarProps) {
  return (
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
  );
}

type SourceDetailPanelProps = {
  selectedSource: SourceDetail | null;
  activeVideos: SourceDetail["videos"];
  openTranscript: (videoId: string) => Promise<void>;
  deleteSource: (source: SourceDetail) => Promise<void>;
};

function SourceDetailPanel({ selectedSource, activeVideos, openTranscript, deleteSource }: SourceDetailPanelProps) {
  return (
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
  );
}

function TranscriptPanel({ transcript }: { transcript: Transcript }) {
  return (
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
  );
}
