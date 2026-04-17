#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=env.sh
. "$ROOT/scripts/env.sh"
load_env

FRONTEND_HOST="$(env_value FRONTEND_HOST 127.0.0.1)"
FRONTEND_PORT="$(env_value FRONTEND_PORT 2001)"
APP_HOST="$(env_value APP_HOST 127.0.0.1)"
APP_PORT="$(env_value APP_PORT 2002)"
DOCS_HOST="$(env_value DOCS_HOST 127.0.0.1)"
DOCS_PORT="$(env_value DOCS_PORT 2003)"

mkdir -p .run
bash "$ROOT/scripts/start-qdrant.sh"

nohup bash "$ROOT/scripts/start-backend.sh" > .run/backend.log 2>&1 &
echo $! > .run/backend.pid
nohup bash "$ROOT/scripts/start-frontend.sh" > .run/frontend.log 2>&1 &
echo $! > .run/frontend.pid
nohup bash "$ROOT/scripts/start-docs.sh" > .run/docs.log 2>&1 &
echo $! > .run/docs.pid

echo "Thothscribe is starting:"
echo "  Frontend: http://${FRONTEND_HOST}:${FRONTEND_PORT}"
echo "  Backend:  http://${APP_HOST}:${APP_PORT}"
echo "  Docs:     http://${DOCS_HOST}:${DOCS_PORT}"
echo "Logs are in .run/"
