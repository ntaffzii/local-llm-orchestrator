$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env.docker"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI is not installed or not in PATH."
}
if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Missing .env.docker. Copy .env.docker.example to .env.docker first."
}

docker info | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker daemon is not running. Start Docker Desktop and wait until the engine is ready."
}

docker compose --env-file $envFile -f (Join-Path $root "compose.yaml") config --quiet
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$preset = Join-Path $root "config\models.ini"
$missing = @()
Get-Content -LiteralPath $preset | Where-Object { $_ -match '^model\s*=\s*(.+)$|^mmproj\s*=\s*(.+)$' } | ForEach-Object {
    $relativePath = ($_ -split '=', 2)[1].Trim()
    $resolved = [System.IO.Path]::GetFullPath((Join-Path (Split-Path $preset) $relativePath))
    if (-not (Test-Path -LiteralPath $resolved)) { $missing += $resolved }
}

if ($missing.Count) {
    $missing | ForEach-Object { Write-Host "[missing] $_" }
    throw "One or more model files are missing."
}

Write-Host "Docker configuration and model mounts are valid."
