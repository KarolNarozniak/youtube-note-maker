---
sidebar_position: 9
title: Multi-App VM
---

# Multi-App VM Deployment

Use this when one VM hosts Thothscribe, Signature Score Verifier, and future apps behind one Nginx reverse proxy.

## Routes

```text
https://notes.kzc.wat        -> Thothscribe frontend
https://docs.notes.kzc.wat   -> Thothscribe docs
https://podpisy.kzc.wat      -> Signature Score Verifier frontend
https://docs.podpisy.kzc.wat -> Signature Score Verifier docs
```

Nginx serves built frontend/docs files directly and proxies `/api/` to local FastAPI services.

## Deploy

Run on the VM:

```bash
cd ~
git clone https://github.com/KarolNarozniak/youtube-note-maker.git
git clone https://github.com/KarolNarozniak/Top_young_podpisy.git

cd ~/youtube-note-maker
git pull
bash scripts/install-prereqs-ubuntu.sh
sudo bash scripts/vm/deploy-all.sh 10.7.183.67 kzc.wat
```

By default, the scripts expect projects at `~/youtube-note-maker` and `~/Top_young_podpisy`. To use another parent directory, set `APPS_ROOT`:

```bash
sudo APPS_ROOT=/opt/apps bash scripts/vm/deploy-all.sh 10.7.183.67 kzc.wat
```

The script installs Nginx, generates a local CA, builds both app frontends, starts Qdrant, installs backend systemd services, and configures HTTPS routes.

It builds `Top_young_podpisy/docs-site` only if that docs site already exists. The Nginx route for `docs.podpisy.kzc.wat` is still created, so it will start working after you add and build that docs site in its own repo.

## Client Hosts

Add this line on each client device:

```text
10.7.183.67 notes.kzc.wat docs.notes.kzc.wat podpisy.kzc.wat docs.podpisy.kzc.wat
```

Linux/macOS:

```bash
sudo sh -c 'echo "10.7.183.67 notes.kzc.wat docs.notes.kzc.wat podpisy.kzc.wat docs.podpisy.kzc.wat" >> /etc/hosts'
```

Windows PowerShell as Administrator:

```powershell
Add-Content -Path "$env:SystemRoot\System32\drivers\etc\hosts" -Value "`n10.7.183.67 notes.kzc.wat docs.notes.kzc.wat podpisy.kzc.wat docs.podpisy.kzc.wat"
```

## Local CA

Copy `~/kzc-local-ca.crt` from the VM to each client.

Linux:

```bash
sudo cp kzc-local-ca.crt /usr/local/share/ca-certificates/kzc-local-ca.crt
sudo update-ca-certificates
```

Windows PowerShell as Administrator:

```powershell
certutil -addstore -f Root .\kzc-local-ca.crt
```

## Validate

```bash
systemctl status nginx
systemctl status thothscribe-backend
systemctl status podpisy-backend
sudo nginx -t
curl -k --resolve notes.kzc.wat:443:10.7.183.67 https://notes.kzc.wat/api/sources
curl -k --resolve podpisy.kzc.wat:443:10.7.183.67 https://podpisy.kzc.wat/api/health
```
