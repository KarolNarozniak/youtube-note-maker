#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -f ".env" ]; then
  cp ".env.example" ".env"
else
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    case "$line" in \#*) continue ;; esac
    key="${line%%=*}"
    if ! grep -qE "^[[:space:]]*${key}[[:space:]]*=" ".env"; then
      printf '%s\n' "$line" >> ".env"
    fi
  done < ".env.example"
fi

# shellcheck source=env.sh
. "$ROOT/scripts/env.sh"

current_env_value() {
  local key="$1"
  if [ ! -f ".env" ]; then
    return 0
  fi
  grep -E "^[[:space:]]*${key}[[:space:]]*=" ".env" | tail -n 1 | cut -d= -f2- || true
}

current="$(current_env_value APP_PORT)"
if [ -z "$current" ] || [ "$current" = "8000" ]; then
  ensure_env_key "APP_PORT" "2002"
fi
current="$(current_env_value FRONTEND_PORT)"
if [ -z "$current" ] || [ "$current" = "5173" ]; then
  ensure_env_key "FRONTEND_PORT" "2001"
fi
current="$(current_env_value DOCS_PORT)"
if [ -z "$current" ] || [ "$current" = "3000" ]; then
  ensure_env_key "DOCS_PORT" "2003"
fi
current="$(current_env_value QDRANT_URL)"
if [ -z "$current" ] || [ "$current" = "http://localhost:6333" ]; then
  ensure_env_key "QDRANT_URL" "http://localhost:2004"
fi
current="$(current_env_value QDRANT_HTTP_PORT)"
if [ -z "$current" ] || [ "$current" = "6333" ]; then
  ensure_env_key "QDRANT_HTTP_PORT" "2004"
fi
current="$(current_env_value QDRANT_GRPC_PORT)"
if [ -z "$current" ] || [ "$current" = "6334" ]; then
  ensure_env_key "QDRANT_GRPC_PORT" "2005"
fi

load_env

PYTHON_BIN="${PYTHON_BIN:-}"
if [ -z "$PYTHON_BIN" ]; then
  if command -v python3.11 >/dev/null 2>&1; then
    PYTHON_BIN="python3.11"
  else
    PYTHON_BIN="python3"
  fi
fi

"$PYTHON_BIN" --version
if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv ".venv"
fi

".venv/bin/python" -m pip install --upgrade pip
".venv/bin/python" -m pip install -r backend/requirements.txt

dotnet restore downloader/YoutubeNoteDownloader/YoutubeNoteDownloader.csproj
dotnet build downloader/YoutubeNoteDownloader/YoutubeNoteDownloader.csproj
dotnet publish downloader/YoutubeNoteDownloader/YoutubeNoteDownloader.csproj -c Release -o "$ROOT/.local/downloader" /p:PublishSingleFile=true --self-contained false
if [ -x "$ROOT/.local/downloader/YoutubeNoteDownloader" ]; then
  ensure_env_key "DOWNLOADER_BIN" "$ROOT/.local/downloader/YoutubeNoteDownloader"
fi

npm ci --prefix frontend
npm ci --prefix docs-site

if command -v ollama >/dev/null 2>&1; then
  if ! ollama list >/dev/null 2>&1 && command -v systemctl >/dev/null 2>&1; then
    sudo systemctl start ollama >/dev/null 2>&1 || true
    sleep 2
  fi
  ollama pull embeddinggemma
fi

docker compose pull qdrant
