. (Join-Path $PSScriptRoot "common.ps1")

foreach ($name in @("llama-router", "orchestrator")) {
    $pidFile = Join-Path $script:RunDir "$name.pid"
    if (Test-ProcessId $pidFile) {
        Write-Host "${name}: running (PID $(Get-Content -LiteralPath $pidFile))"
    } else {
        Write-Host "${name}: stopped"
    }
}
