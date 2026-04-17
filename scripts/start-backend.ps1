$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    throw "Missing .venv. Run .\scripts\setup.ps1 first."
}

function Import-DotEnv {
    if (-not (Test-Path ".env")) { return }
    foreach ($rawLine in Get-Content ".env") {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { continue }
        $key, $value = $line.Split("=", 2)
        Set-Item -Path "Env:$($key.Trim())" -Value $value.Trim().Trim('"').Trim("'")
    }
}
function EnvOrDefault([string]$Name, [string]$Default) {
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return $value
}
Import-DotEnv
$appHost = EnvOrDefault "APP_HOST" "127.0.0.1"
$appPort = EnvOrDefault "APP_PORT" "2002"

.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host $appHost --port $appPort
