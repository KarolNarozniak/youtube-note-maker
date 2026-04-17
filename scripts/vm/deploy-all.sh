#!/usr/bin/env bash
set -euo pipefail

VM_IP="${1:-10.7.183.67}"
BASE_DOMAIN="${2:-kzc.wat}"
NOTES_REPO_URL="${NOTES_REPO_URL:-https://github.com/KarolNarozniak/youtube-note-maker.git}"
PODPISY_REPO_URL="${PODPISY_REPO_URL:-https://github.com/KarolNarozniak/Top_young_podpisy.git}"

if [ "$(id -u)" -ne 0 ]; then
  exec sudo -E bash "$0" "$VM_IP" "$BASE_DOMAIN"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_USER="${APP_USER:-${SUDO_USER:-}}"
if [ -z "$APP_USER" ]; then
  APP_USER="$(stat -c '%U' "$SCRIPT_DIR/../.." 2>/dev/null || echo root)"
fi
APP_GROUP="$(id -gn "$APP_USER")"
APP_HOME="$(getent passwd "$APP_USER" | cut -d: -f6 2>/dev/null || true)"
if [ -z "$APP_HOME" ]; then
  APP_HOME="$HOME"
fi
APPS_ROOT="${APPS_ROOT:-$APP_HOME}"

NOTES_ROOT="${APPS_ROOT}/youtube-note-maker"
PODPISY_ROOT="${APPS_ROOT}/Top_young_podpisy"
NOTES_HOST="notes.${BASE_DOMAIN}"
PODPISY_HOST="podpisy.${BASE_DOMAIN}"
PUBLIC_CA_PATH="${APPS_ROOT}/kzc-local-ca.crt"

run_user() {
  if [ "$APP_USER" = "root" ]; then
    "$@"
  else
    sudo -H -u "$APP_USER" "$@"
  fi
}

clone_or_update() {
  local repo_url="$1"
  local target_dir="$2"

  if [ -d "${target_dir}/.git" ]; then
    run_user git -C "$target_dir" pull --ff-only
  else
    run_user git clone "$repo_url" "$target_dir"
  fi
}

python_bin() {
  if command -v python3.11 >/dev/null 2>&1; then
    command -v python3.11
  else
    command -v python3
  fi
}

npm_install() {
  local project_dir="$1"
  if [ ! -f "${project_dir}/package.json" ]; then
    echo "Skipping npm install for ${project_dir}; package.json was not found."
    return 0
  fi
  if [ -f "${project_dir}/package-lock.json" ]; then
    run_user npm ci --prefix "$project_dir"
  else
    run_user npm install --prefix "$project_dir"
  fi
}

setup_python_app() {
  local project_dir="$1"
  local requirements_path="$2"
  local py
  py="$(python_bin)"

  if [ ! -d "${project_dir}/.venv" ]; then
    run_user "$py" -m venv "${project_dir}/.venv"
  fi
  run_user "${project_dir}/.venv/bin/python" -m pip install --upgrade pip
  run_user "${project_dir}/.venv/bin/python" -m pip install -r "$requirements_path"
}

configure_notes_env() {
  cd "$NOTES_ROOT"
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

  # shellcheck source=../env.sh
  . "$NOTES_ROOT/scripts/env.sh"
  ensure_env_key "APP_HOST" "127.0.0.1"
  ensure_env_key "APP_PORT" "2002"
  ensure_env_key "FRONTEND_HOST" "127.0.0.1"
  ensure_env_key "FRONTEND_PORT" "2001"
  ensure_env_key "DOCS_HOST" "127.0.0.1"
  ensure_env_key "DOCS_PORT" "2003"
  ensure_env_key "ALLOWED_ORIGINS" "https://${NOTES_HOST}"
  ensure_env_key "QDRANT_URL" "http://localhost:2004"
  ensure_env_key "QDRANT_HTTP_PORT" "2004"
  ensure_env_key "QDRANT_GRPC_PORT" "2005"
  ensure_env_key "DOWNLOADER_BIN" "${NOTES_ROOT}/.local/downloader/YoutubeNoteDownloader"
  chown "$APP_USER:$APP_GROUP" ".env"
}

setup_notes() {
  configure_notes_env
  setup_python_app "$NOTES_ROOT" "$NOTES_ROOT/backend/requirements.txt"

  run_user dotnet restore "$NOTES_ROOT/downloader/YoutubeNoteDownloader/YoutubeNoteDownloader.csproj"
  run_user dotnet build "$NOTES_ROOT/downloader/YoutubeNoteDownloader/YoutubeNoteDownloader.csproj"
  run_user dotnet publish "$NOTES_ROOT/downloader/YoutubeNoteDownloader/YoutubeNoteDownloader.csproj" \
    -c Release -o "$NOTES_ROOT/.local/downloader" /p:PublishSingleFile=true --self-contained false

  npm_install "$NOTES_ROOT/frontend"
  run_user npm run build --prefix "$NOTES_ROOT/frontend"
  npm_install "$NOTES_ROOT/docs-site"
  run_user npm run build --prefix "$NOTES_ROOT/docs-site"

  docker compose --env-file "$NOTES_ROOT/.env" -f "$NOTES_ROOT/docker-compose.yml" up -d qdrant
}

setup_podpisy() {
  setup_python_app "$PODPISY_ROOT" "$PODPISY_ROOT/requirements.txt"

  npm_install "$PODPISY_ROOT/frontend"
  run_user npm run build --prefix "$PODPISY_ROOT/frontend"

  if [ -f "$PODPISY_ROOT/docs-site/package.json" ]; then
    npm_install "$PODPISY_ROOT/docs-site"
    run_user npm run build --prefix "$PODPISY_ROOT/docs-site"
  else
    echo "Skipping Signature Score docs build; ${PODPISY_ROOT}/docs-site/package.json was not found."
    echo "Nginx will still route docs.podpisy.${BASE_DOMAIN}; add/build docs-site in Top_young_podpisy when ready."
  fi
}

apt-get update
apt-get install -y ca-certificates curl git nginx openssl python3 python3-venv python3-pip

if [ ! -d "$APPS_ROOT" ]; then
  install -d -m 755 -o "$APP_USER" -g "$APP_GROUP" "$APPS_ROOT"
fi
clone_or_update "$NOTES_REPO_URL" "$NOTES_ROOT"
clone_or_update "$PODPISY_REPO_URL" "$PODPISY_ROOT"
chown -R "$APP_USER:$APP_GROUP" "$NOTES_ROOT" "$PODPISY_ROOT"

setup_notes
setup_podpisy

bash "$SCRIPT_DIR/generate-local-ca.sh" "$VM_IP" "$BASE_DOMAIN"
cp /etc/kzc-proxy/certs/kzc-local-ca.crt "$PUBLIC_CA_PATH"
chown "$APP_USER:$APP_GROUP" "$PUBLIC_CA_PATH"
chmod 644 "$PUBLIC_CA_PATH"

APP_USER="$APP_USER" bash "$SCRIPT_DIR/install-services.sh" "$VM_IP" "$BASE_DOMAIN" "$APPS_ROOT"
bash "$SCRIPT_DIR/configure-nginx.sh" "$VM_IP" "$BASE_DOMAIN" "$APPS_ROOT"
bash "$SCRIPT_DIR/print-hosts.sh" "$VM_IP" "$BASE_DOMAIN" "$APPS_ROOT"

cat <<EOF

Deployment complete.

Local CA copy for clients:
${PUBLIC_CA_PATH}

Validate on the VM:
systemctl status nginx
systemctl status thothscribe-backend
systemctl status podpisy-backend
curl -k --resolve ${NOTES_HOST}:443:${VM_IP} https://${NOTES_HOST}/api/sources
curl -k --resolve ${PODPISY_HOST}:443:${VM_IP} https://${PODPISY_HOST}/api/health
EOF
