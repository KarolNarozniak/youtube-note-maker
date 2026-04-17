#!/usr/bin/env bash
set -euo pipefail

VM_IP="${1:-10.7.183.67}"
BASE_DOMAIN="${2:-kzc.wat}"
CERT_DIR="${CERT_DIR:-/etc/kzc-proxy/certs}"
APP_USER_FOR_ROOT="${SUDO_USER:-${USER:-root}}"
APP_HOME_FOR_ROOT="$(getent passwd "$APP_USER_FOR_ROOT" | cut -d: -f6 2>/dev/null || true)"
if [ -z "$APP_HOME_FOR_ROOT" ]; then
  APP_HOME_FOR_ROOT="$HOME"
fi
APPS_ROOT="${3:-${APPS_ROOT:-$APP_HOME_FOR_ROOT}}"

NOTES_HOST="notes.${BASE_DOMAIN}"
NOTES_DOCS_HOST="docs.notes.${BASE_DOMAIN}"
PODPISY_HOST="podpisy.${BASE_DOMAIN}"
PODPISY_DOCS_HOST="docs.podpisy.${BASE_DOMAIN}"

NOTES_ROOT="${APPS_ROOT}/youtube-note-maker"
PODPISY_ROOT="${APPS_ROOT}/Top_young_podpisy"
SITE_PATH="/etc/nginx/sites-available/kzc-apps"

if [ "$(id -u)" -ne 0 ]; then
  exec sudo CERT_DIR="$CERT_DIR" bash "$0" "$VM_IP" "$BASE_DOMAIN" "$APPS_ROOT"
fi

apt-get update
apt-get install -y nginx

cat > "$SITE_PATH" <<NGINX
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    server_name _;

    ssl_certificate ${CERT_DIR}/kzc-server.crt;
    ssl_certificate_key ${CERT_DIR}/kzc-server.key;

    return 404;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name ${NOTES_HOST};

    ssl_certificate ${CERT_DIR}/kzc-server.crt;
    ssl_certificate_key ${CERT_DIR}/kzc-server.key;
    client_max_body_size 64m;
    root ${NOTES_ROOT}/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:2002/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name ${NOTES_DOCS_HOST};

    ssl_certificate ${CERT_DIR}/kzc-server.crt;
    ssl_certificate_key ${CERT_DIR}/kzc-server.key;
    root ${NOTES_ROOT}/docs-site/build;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name ${PODPISY_HOST};

    ssl_certificate ${CERT_DIR}/kzc-server.crt;
    ssl_certificate_key ${CERT_DIR}/kzc-server.key;
    client_max_body_size 64m;
    root ${PODPISY_ROOT}/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:2012/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name ${PODPISY_DOCS_HOST};

    ssl_certificate ${CERT_DIR}/kzc-server.crt;
    ssl_certificate_key ${CERT_DIR}/kzc-server.key;
    root ${PODPISY_ROOT}/docs-site/build;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
NGINX

rm -f /etc/nginx/sites-enabled/default
ln -sf "$SITE_PATH" /etc/nginx/sites-enabled/kzc-apps
nginx -t
systemctl enable --now nginx
systemctl reload nginx

if command -v ufw >/dev/null 2>&1; then
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
fi

echo "Nginx routes are active for ${NOTES_HOST}, ${NOTES_DOCS_HOST}, ${PODPISY_HOST}, and ${PODPISY_DOCS_HOST}."
