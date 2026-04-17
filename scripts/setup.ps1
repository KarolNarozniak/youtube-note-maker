$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.11 first."
}

py -3.11 --version
if (-not (Test-Path ".venv")) {
    py -3.11 -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    throw ".NET SDK was not found. Install .NET SDK 10+ and rerun setup."
}
dotnet restore downloader\YoutubeNoteDownloader\YoutubeNoteDownloader.csproj
dotnet build downloader\YoutubeNoteDownloader\YoutubeNoteDownloader.csproj

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Install Node.js first."
}
cmd /c npm ci --prefix frontend

if (Get-Command ollama -ErrorAction SilentlyContinue) {
    ollama pull embeddinggemma
}

docker compose pull qdrant
