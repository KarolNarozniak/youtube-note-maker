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
$docsHost = EnvOrDefault "DOCS_HOST" "127.0.0.1"
$docsPort = EnvOrDefault "DOCS_PORT" "2003"

cmd /c npm run start --prefix docs-site -- --host $docsHost --port $docsPort
