param(
    [switch]$Cuda,
    [switch]$Build
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env.docker"

if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Missing .env.docker. Copy .env.docker.example to .env.docker and set ORCHESTRATOR_API_KEY."
}

$arguments = @("compose", "--env-file", $envFile, "-f", (Join-Path $root "compose.yaml"))
if ($Cuda) {
    $arguments += @("-f", (Join-Path $root "compose.cuda.yaml"))
}
$arguments += @("up", "-d")
if ($Build) { $arguments += "--build" }

& docker @arguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Local LLM services started."
Write-Host "API: http://127.0.0.1:8090"
Write-Host "Docs: http://127.0.0.1:8090/docs"

