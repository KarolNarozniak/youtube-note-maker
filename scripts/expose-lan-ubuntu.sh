#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck source=env.sh
. "$ROOT/scripts/env.sh"

LAN_HOST="${1:-}"
if [ -z "$LAN_HOST" ]; then
  LAN_HOST="$(hostname -I | awk '{print $1}')"
fi
if [ -z "$LAN_HOST" ]; then
  echo "Could not detect the LAN IP. Pass it explicitly, for example: bash scripts/expose-lan-ubuntu.sh 10.7.183.67" >&2
  exit 1
fi

if [ ! -f ".env" ]; then
  cp ".env.example" ".env"
fi

ensure_env_key "ALLOWED_ORIGINS" "http://${LAN_HOST}"
ensure_env_key "APP_HOST" "127.0.0.1"
ensure_env_key "FRONTEND_HOST" "127.0.0.1"

sudo apt-get update
sudo apt-get install -y nginx

sudo tee /etc/nginx/sites-available/thothscribe >/dev/null <<NGINX
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name ${LAN_HOST} _;

    client_max_body_size 64m;

    location /api/ {
        proxy_pass http://127.0.0.1:2002/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:2001;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/thothscribe /etc/nginx/sites-enabled/thothscribe
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx

if command -v ufw >/dev/null 2>&1; then
  sudo ufw allow 80/tcp || true
fi

echo "Thothscribe is exposed at http://${LAN_HOST}/"
echo "Keep the app stack running with: bash scripts/start-all.sh"
