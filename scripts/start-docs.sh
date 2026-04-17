#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=env.sh
. "$ROOT/scripts/env.sh"
load_env
DOCS_HOST="$(env_value DOCS_HOST 127.0.0.1)"
DOCS_PORT="$(env_value DOCS_PORT 2003)"

npm run start --prefix docs-site -- --host "$DOCS_HOST" --port "$DOCS_PORT"
