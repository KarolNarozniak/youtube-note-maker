$ErrorActionPreference = "Stop"

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
$frontendHost = EnvOrDefault "FRONTEND_HOST" "127.0.0.1"
$frontendPort = EnvOrDefault "FRONTEND_PORT" "2001"
$appHost = EnvOrDefault "APP_HOST" "127.0.0.1"
$appPort = EnvOrDefault "APP_PORT" "2002"
$docsHost = EnvOrDefault "DOCS_HOST" "127.0.0.1"
$docsPort = EnvOrDefault "DOCS_PORT" "2003"

.\scripts\start-qdrant.ps1

$root = (Resolve-Path ".").Path
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; .\scripts\start-backend.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; .\scripts\start-frontend.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; .\scripts\start-docs.ps1"

Write-Host "Thothscribe is starting:"
Write-Host "  Frontend: http://$($frontendHost):$($frontendPort)"
Write-Host "  Backend:  http://$($appHost):$($appPort)"
Write-Host "  Docs:     http://$($docsHost):$($docsPort)"
