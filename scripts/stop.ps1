. (Join-Path $PSScriptRoot "common.ps1")

foreach ($name in @("orchestrator", "llama-router")) {
    $pidFile = Join-Path $script:RunDir "$name.pid"
    if (Test-ProcessId $pidFile) {
        $processId = Get-Content -LiteralPath $pidFile
        Stop-Process -Id $processId
        Write-Host "$name stopped (PID $processId)"
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

