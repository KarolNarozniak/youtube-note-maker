#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -d ".venv" ]; then
  echo "Missing .venv. Run ./scripts/setup.sh first." >&2
  exit 1
fi

# shellcheck source=env.sh
. "$ROOT/scripts/env.sh"
load_env
APP_HOST="$(env_value APP_HOST 127.0.0.1)"
APP_PORT="$(env_value APP_PORT 2002)"

".venv/bin/python" -m uvicorn backend.app.main:app --host "$APP_HOST" --port "$APP_PORT"
