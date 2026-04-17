#!/usr/bin/env bash
set -euo pipefail

VM_IP="${1:-10.7.183.67}"
BASE_DOMAIN="${2:-kzc.wat}"
CERT_DIR="${CERT_DIR:-/etc/kzc-proxy/certs}"
APPS_ROOT="${3:-}"

HOSTS_LINE="${VM_IP} notes.${BASE_DOMAIN} docs.notes.${BASE_DOMAIN} podpisy.${BASE_DOMAIN} docs.podpisy.${BASE_DOMAIN}"
if [ -n "$APPS_ROOT" ]; then
  PUBLIC_CA="${APPS_ROOT}/kzc-local-ca.crt"
else
  PUBLIC_CA="${CERT_DIR}/kzc-local-ca.crt"
fi

cat <<EOF
Add this line to each client hosts file:

${HOSTS_LINE}

Linux/macOS client:
sudo sh -c 'echo "${HOSTS_LINE}" >> /etc/hosts'

Windows PowerShell as Administrator:
Add-Content -Path "\$env:SystemRoot\\System32\\drivers\\etc\\hosts" -Value "\`n${HOSTS_LINE}"

Copy this local CA certificate from the VM and install it on client devices:
${PUBLIC_CA}

Linux client:
sudo cp kzc-local-ca.crt /usr/local/share/ca-certificates/kzc-local-ca.crt
sudo update-ca-certificates

Windows PowerShell as Administrator:
certutil -addstore -f Root .\\kzc-local-ca.crt

Open:
https://notes.${BASE_DOMAIN}
https://docs.notes.${BASE_DOMAIN}
https://podpisy.${BASE_DOMAIN}
https://docs.podpisy.${BASE_DOMAIN}
EOF
