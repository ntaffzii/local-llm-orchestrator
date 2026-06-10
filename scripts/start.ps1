. (Join-Path $PSScriptRoot "common.ps1")
Import-LocalEnv
New-Item -ItemType Directory -Force -Path $script:RunDir | Out-Null

$llamaPid = Join-Path $script:RunDir "llama-router.pid"
$apiPid = Join-Path $script:RunDir "orchestrator.pid"
$llamaExe = Get-Setting "LLAMA_SERVER_EXE" "llama-server"
$llamaPort = Get-Setting "LLAMA_PORT" "8080"
$modelsMax = Get-Setting "LLAMA_MODELS_MAX" "2"
$idleSeconds = Get-Setting "LLAMA_SLEEP_IDLE_SECONDS" "900"
$preset = Join-Path $script:Root "config\models.ini"
$python = Join-Path $script:Root ".venv\Scripts\python.exe"
$llamaOut = Join-Path $script:RunDir "llama-router.out.log"
$llamaErr = Join-Path $script:RunDir "llama-router.err.log"
$apiOut = Join-Path $script:RunDir "orchestrator.out.log"
$apiErr = Join-Path $script:RunDir "orchestrator.err.log"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python environment not found. Create it with: python -m venv .venv"
}

if (-not (Test-ProcessId $llamaPid)) {
    $process = Start-Process -FilePath $llamaExe -ArgumentList @(
        "--host", (Get-Setting "LLAMA_HOST" "127.0.0.1"),
        "--port", $llamaPort,
        "--models-preset", $preset,
        "--models-max", $modelsMax,
        "--sleep-idle-seconds", $idleSeconds,
        "--metrics",
        "--no-ui"
    ) -WorkingDirectory (Join-Path $script:Root "config") -WindowStyle Hidden `
      -RedirectStandardOutput $llamaOut -RedirectStandardError $llamaErr -PassThru
    Set-Content -LiteralPath $llamaPid -Value $process.Id
    Write-Host "llama.cpp router started (PID $($process.Id), port $llamaPort)"
} else {
    Write-Host "llama.cpp router is already running"
}

if (-not (Test-ProcessId $apiPid)) {
    $apiPort = Get-Setting "ORCHESTRATOR_PORT" "8090"
    $workers = Get-Setting "ORCHESTRATOR_WORKERS" "1"
    $process = Start-Process -FilePath $python -ArgumentList @(
        "-m", "uvicorn", "services.orchestrator.main:app",
        "--host", (Get-Setting "ORCHESTRATOR_HOST" "127.0.0.1"),
        "--port", $apiPort,
        "--workers", $workers
    ) -WorkingDirectory $script:Root -WindowStyle Hidden `
      -RedirectStandardOutput $apiOut -RedirectStandardError $apiErr -PassThru
    Set-Content -LiteralPath $apiPid -Value $process.Id
    Write-Host "orchestrator started (PID $($process.Id), port $apiPort)"
} else {
    Write-Host "orchestrator is already running"
}
