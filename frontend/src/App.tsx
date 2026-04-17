import { useEffect, useState } from "react";
import { APP_NAME, THEME_STORAGE_KEY } from "./constants";
import { ChatView } from "./views/ChatView";
import { LibraryView } from "./views/LibraryView";
import type { Tab, Theme } from "./types";
import "./styles/index.css";

export function App() {
  const [tab, setTab] = useState<Tab>("library");
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem(THEME_STORAGE_KEY) as Theme) || "light");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_STORAGE_KEY, theme);
  }, [theme]);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <img src="/logo.png" alt="" />
          <div>
            <p className="eyebrow">Local RAG workspace</p>
            <h1>{APP_NAME}</h1>
          </div>
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
