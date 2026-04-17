#!/usr/bin/env bash
set -euo pipefail

load_env() {
  if [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    . ".env"
    set +a
  fi
}

env_value() {
  local name="$1"
  local fallback="$2"
  local value="${!name:-}"
  if [ -z "$value" ]; then
    printf '%s' "$fallback"
  else
    printf '%s' "$value"
  fi
}

ensure_env_key() {
  local key="$1"
  local value="$2"
  local file="${3:-.env}"
  if [ ! -f "$file" ]; then
    touch "$file"
  fi
  if grep -qE "^[[:space:]]*${key}[[:space:]]*=" "$file"; then
    python3 - "$file" "$key" "$value" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
lines = path.read_text(encoding="utf-8").splitlines()
path.write_text(
    "\n".join(f"{key}={value}" if line.strip().startswith(f"{key}=") else line for line in lines) + "\n",
    encoding="utf-8",
)
PY
  else
    printf '%s=%s\n' "$key" "$value" >> "$file"
  fi
}
