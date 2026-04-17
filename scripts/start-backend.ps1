$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    throw "Missing .venv. Run .\scripts\setup.ps1 first."
}

.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
