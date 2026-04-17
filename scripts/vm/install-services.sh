#!/usr/bin/env bash
set -euo pipefail

VM_IP="${1:-10.7.183.67}"
BASE_DOMAIN="${2:-kzc.wat}"
APP_USER="${APP_USER:-${SUDO_USER:-}}"

NOTES_HOST="notes.${BASE_DOMAIN}"
PODPISY_HOST="podpisy.${BASE_DOMAIN}"
PODPISY_ENV="/etc/kzc-proxy/podpisy.env"

if [ "$(id -u)" -ne 0 ]; then
  exec sudo APP_USER="$APP_USER" APPS_ROOT="${APPS_ROOT:-}" bash "$0" "$VM_IP" "$BASE_DOMAIN" "${3:-${APPS_ROOT:-}}"
fi

if [ -z "$APP_USER" ]; then
  APP_USER="$(stat -c '%U' "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)")"
fi
APP_GROUP="$(id -gn "$APP_USER")"
APP_HOME="$(getent passwd "$APP_USER" | cut -d: -f6 2>/dev/null || true)"
if [ -z "$APP_HOME" ]; then
  APP_HOME="$HOME"
fi
APPS_ROOT="${3:-${APPS_ROOT:-$APP_HOME}}"

NOTES_ROOT="${APPS_ROOT}/youtube-note-maker"
PODPISY_ROOT="${APPS_ROOT}/Top_young_podpisy"

mkdir -p /etc/kzc-proxy
cat > "$PODPISY_ENV" <<EOF
PYTHONUNBUFFERED=1
SIGNATURE_ALLOWED_ORIGINS=https://${PODPISY_HOST}
SIGNATURE_API_TITLE=Signature Score API
SIGNATURE_API_VERSION=1.0.0
EOF
chmod 644 "$PODPISY_ENV"

cat > /etc/systemd/system/thothscribe-backend.service <<EOF
[Unit]
Description=Thothscribe FastAPI backend
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${NOTES_ROOT}
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=${NOTES_ROOT}/.env
ExecStart=${NOTES_ROOT}/.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 2002
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/podpisy-backend.service <<EOF
[Unit]
Description=Signature Score FastAPI backend
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${PODPISY_ROOT}
EnvironmentFile=${PODPISY_ENV}
ExecStart=${PODPISY_ROOT}/.venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 2012
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now thothscribe-backend.service
systemctl enable --now podpisy-backend.service
systemctl restart thothscribe-backend.service
systemctl restart podpisy-backend.service

echo "Systemd services installed for https://${NOTES_HOST} and https://${PODPISY_HOST}."
