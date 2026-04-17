$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

function Import-DotEnv {
    param([string]$Path = ".env")
    if (-not (Test-Path $Path)) { return }
    foreach ($rawLine in Get-Content $Path) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { continue }
        $key, $value = $line.Split("=", 2)
        Set-Item -Path "Env:$($key.Trim())" -Value $value.Trim().Trim('"').Trim("'")
    }
}

function Set-EnvFileValue {
    param([string]$Path, [string]$Name, [string]$Value)
    if (-not (Test-Path $Path)) { New-Item -ItemType File -Path $Path -Force | Out-Null }
    $lines = @(Get-Content $Path)
    $found = $false
    $pattern = "^\s*$([regex]::Escape($Name))\s*="
    $updated = foreach ($line in $lines) {
        if ($line -match $pattern) {
            $found = $true
            "$Name=$Value"
        } else {
            $line
        }
    }
    if (-not $found) { $updated += "$Name=$Value" }
    Set-Content -Path $Path -Value $updated
}

foreach ($rawLine in Get-Content ".env.example") {
    $line = $rawLine.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $key, $value = $line.Split("=", 2)
        if (-not (Select-String -Path ".env" -Pattern "^\s*$([regex]::Escape($key.Trim()))\s*=" -Quiet)) {
            Add-Content ".env" "$($key.Trim())=$($value.Trim())"
        }
    }
}

function Get-EnvFileValue {
    param([string]$Path, [string]$Name)
    if (-not (Test-Path $Path)) { return $null }
    $match = Select-String -Path $Path -Pattern "^\s*$([regex]::Escape($Name))\s*=(.*)$" | Select-Object -Last 1
    if ($match) {
        return $match.Matches[0].Groups[1].Value.Trim()
    }
    return $null
}

if ((Get-EnvFileValue ".env" "APP_PORT") -in @($null, "", "8000")) {
    Set-EnvFileValue -Path ".env" -Name "APP_PORT" -Value "2002"
}
if ((Get-EnvFileValue ".env" "FRONTEND_PORT") -in @($null, "", "5173")) {
    Set-EnvFileValue -Path ".env" -Name "FRONTEND_PORT" -Value "2001"
}
if ((Get-EnvFileValue ".env" "DOCS_PORT") -in @($null, "", "3000")) {
    Set-EnvFileValue -Path ".env" -Name "DOCS_PORT" -Value "2003"
}
if ((Get-EnvFileValue ".env" "QDRANT_URL") -in @($null, "", "http://localhost:6333")) {
    Set-EnvFileValue -Path ".env" -Name "QDRANT_URL" -Value "http://localhost:2004"
}
if ((Get-EnvFileValue ".env" "QDRANT_HTTP_PORT") -in @($null, "", "6333")) {
    Set-EnvFileValue -Path ".env" -Name "QDRANT_HTTP_PORT" -Value "2004"
}
if ((Get-EnvFileValue ".env" "QDRANT_GRPC_PORT") -in @($null, "", "6334")) {
    Set-EnvFileValue -Path ".env" -Name "QDRANT_GRPC_PORT" -Value "2005"
}
Import-DotEnv

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
$publishDir = Join-Path (Resolve-Path ".").Path ".local\downloader"
dotnet publish downloader\YoutubeNoteDownloader\YoutubeNoteDownloader.csproj -c Release -o $publishDir /p:PublishSingleFile=true --self-contained false
$downloaderExe = Join-Path $publishDir "YoutubeNoteDownloader.exe"
if (Test-Path $downloaderExe) {
    Set-EnvFileValue -Path ".env" -Name "DOWNLOADER_BIN" -Value $downloaderExe
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Install Node.js first."
}
cmd /c npm ci --prefix frontend
cmd /c npm ci --prefix docs-site

if (Get-Command ollama -ErrorAction SilentlyContinue) {
    ollama pull embeddinggemma
}

docker compose pull qdrant
