#!/usr/bin/env bash
set -euo pipefail

VM_IP="${1:-10.7.183.67}"
BASE_DOMAIN="${2:-kzc.wat}"
CERT_DIR="${CERT_DIR:-/etc/kzc-proxy/certs}"

NOTES_HOST="notes.${BASE_DOMAIN}"
NOTES_DOCS_HOST="docs.notes.${BASE_DOMAIN}"
PODPISY_HOST="podpisy.${BASE_DOMAIN}"
PODPISY_DOCS_HOST="docs.podpisy.${BASE_DOMAIN}"

if [ "$(id -u)" -ne 0 ]; then
  exec sudo CERT_DIR="$CERT_DIR" bash "$0" "$VM_IP" "$BASE_DOMAIN"
fi

mkdir -p "$CERT_DIR"
chmod 755 "$(dirname "$CERT_DIR")" "$CERT_DIR"

CA_KEY="$CERT_DIR/kzc-local-ca.key"
CA_CERT="$CERT_DIR/kzc-local-ca.crt"
SERVER_KEY="$CERT_DIR/kzc-server.key"
SERVER_CSR="$CERT_DIR/kzc-server.csr"
SERVER_CERT="$CERT_DIR/kzc-server.crt"
SERVER_EXT="$CERT_DIR/kzc-server.ext"

if [ ! -f "$CA_KEY" ] || [ ! -f "$CA_CERT" ]; then
  openssl genrsa -out "$CA_KEY" 4096
  openssl req -x509 -new -nodes -key "$CA_KEY" -sha256 -days 3650 \
    -subj "/CN=kzc local development CA" \
    -out "$CA_CERT"
fi

cat > "$SERVER_EXT" <<EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=@alt_names

[alt_names]
DNS.1=${NOTES_HOST}
DNS.2=${NOTES_DOCS_HOST}
DNS.3=${PODPISY_HOST}
DNS.4=${PODPISY_DOCS_HOST}
IP.1=${VM_IP}
EOF

openssl genrsa -out "$SERVER_KEY" 2048
openssl req -new -key "$SERVER_KEY" -subj "/CN=${NOTES_HOST}" -out "$SERVER_CSR"
openssl x509 -req -in "$SERVER_CSR" -CA "$CA_CERT" -CAkey "$CA_KEY" -CAcreateserial \
  -out "$SERVER_CERT" -days 825 -sha256 -extfile "$SERVER_EXT"

chmod 600 "$CA_KEY" "$SERVER_KEY"
chmod 644 "$CA_CERT" "$SERVER_CERT" "$SERVER_EXT"

echo "Local CA: $CA_CERT"
echo "Server certificate: $SERVER_CERT"
