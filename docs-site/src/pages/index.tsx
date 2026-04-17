import Link from "@docusaurus/Link";
import Layout from "@theme/Layout";

export default function Home(): JSX.Element {
  return (
    <Layout
      title="Thothscribe Documentation"
      description="Local-first documentation for the Thothscribe YouTube-to-RAG workspace"
    >
      <main className="docs-home">
        <section className="docs-hero">
          <img src="/img/logo.png" alt="Thothscribe logo" />
          <div>
            <p className="docs-kicker">Local-first RAG workspace</p>
            <h1>Thothscribe</h1>
            <p>
              Ingest YouTube videos, playlists, notes, and web pages into a local searchable knowledge base.
              Keep model calls, embeddings, transcripts, and chat history under your control.
            </p>
            <div className="docs-actions">
              <Link className="button button--primary" to="/docs/intro">
                Start reading
              </Link>
              <Link className="button button--secondary" to="/docs/setup">
                Run locally
              </Link>
            </div>
          </div>
        </section>

        <section className="docs-grid">
          <article>
            <h2>Library</h2>
            <p>Download audio, transcribe with Whisper, chunk transcripts, and store vectors in Qdrant.</p>
          </article>
          <article>
            <h2>Chat</h2>
            <p>Attach playlists, videos, web links, and manual notes to each conversation.</p>
          </article>
          <article>
            <h2>Local by default</h2>
            <p>Use Ollama for embeddings and local chat models, with optional session-only OpenAI keys.</p>
          </article>
        </section>
      </main>
    </Layout>
  );
}
