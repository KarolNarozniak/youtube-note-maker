#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=env.sh
. "$ROOT/scripts/env.sh"
load_env
FRONTEND_HOST="$(env_value FRONTEND_HOST 127.0.0.1)"
FRONTEND_PORT="$(env_value FRONTEND_PORT 2001)"

npm run dev --prefix frontend -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
