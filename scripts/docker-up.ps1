param(
    [switch]$Cuda,
    [switch]$Build,
    [string]$ApiKey
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env.docker"

if (-not (Test-Path -LiteralPath $envFile)) {
    & (Join-Path $PSScriptRoot "set-api-key.ps1") -ApiKey $ApiKey -EnvFile $envFile
} else {
    $configuredKey = Get-Content -LiteralPath $envFile | Where-Object { $_ -match '^\s*ORCHESTRATOR_API_KEY\s*=' } | Select-Object -First 1
    $keyValue = if ($configuredKey) { ($configuredKey -split '=', 2)[1].Trim() } else { "" }
    if ($ApiKey -or [string]::IsNullOrWhiteSpace($keyValue) -or $keyValue -in @("replace-with-a-long-random-key", "change-me")) {
        & (Join-Path $PSScriptRoot "set-api-key.ps1") -ApiKey $ApiKey -EnvFile $envFile
    }
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
