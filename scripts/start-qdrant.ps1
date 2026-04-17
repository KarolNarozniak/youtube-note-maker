$ErrorActionPreference = "Stop"

function Test-DockerReady {
    docker info *> $null
    return $LASTEXITCODE -eq 0
}

if (-not (Test-DockerReady)) {
    $dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerDesktop) {
        Write-Host "Docker daemon is not ready. Starting Docker Desktop..."
        Start-Process $dockerDesktop
        for ($i = 0; $i -lt 30; $i++) {
            Start-Sleep -Seconds 3
            if (Test-DockerReady) {
                break
            }
            Write-Host "Waiting for Docker Desktop..."
        }
    }
}

if (-not (Test-DockerReady)) {
    throw @"
Docker is installed, but the Docker daemon is not reachable.

Open Docker Desktop manually and wait until it says the engine is running, then rerun:
  .\scripts\start-qdrant.ps1

If Docker Desktop is running and you still get 'permission denied', add your Windows user to the local 'docker-users' group and sign out/in.
"@
}

docker compose up -d qdrant
