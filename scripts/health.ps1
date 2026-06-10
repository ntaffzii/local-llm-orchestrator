. (Join-Path $PSScriptRoot "common.ps1")
Import-LocalEnv

$llamaPort = Get-Setting "LLAMA_PORT" "8080"
$apiPort = Get-Setting "ORCHESTRATOR_PORT" "8090"
$apiKey = Get-Setting "ORCHESTRATOR_API_KEY" ""
$headers = @{}
if ($apiKey) { $headers.Authorization = "Bearer $apiKey" }

try {
    $llama = Invoke-RestMethod -Uri "http://127.0.0.1:$llamaPort/health" -TimeoutSec 5
    Write-Host "llama.cpp: healthy ($($llama.status))"
} catch {
    Write-Host "llama.cpp: unavailable"
}

try {
    $api = Invoke-RestMethod -Uri "http://127.0.0.1:$apiPort/ready" -Headers $headers -TimeoutSec 5
    Write-Host "orchestrator: ready ($($api.status))"
} catch {
    Write-Host "orchestrator: unavailable"
}

