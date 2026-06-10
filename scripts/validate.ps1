. (Join-Path $PSScriptRoot "common.ps1")
Import-LocalEnv

$failed = $false
$python = Join-Path $script:Root ".venv\Scripts\python.exe"
$llamaExe = Get-Setting "LLAMA_SERVER_EXE" "llama-server"
$configPath = Join-Path $script:Root "config\models.json"
$presetPath = Join-Path $script:Root "config\models.ini"

if (Test-Path -LiteralPath $python) {
    Write-Host "[ok] Python environment"
} else {
    Write-Host "[missing] .venv\Scripts\python.exe"
    $failed = $true
}

if (Get-Command $llamaExe -ErrorAction SilentlyContinue) {
    Write-Host "[ok] llama-server"
} elseif (Test-Path -LiteralPath $llamaExe) {
    Write-Host "[ok] llama-server path"
} else {
    Write-Host "[missing] llama-server: $llamaExe"
    $failed = $true
}

try {
    Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json | Out-Null
    Write-Host "[ok] config\models.json"
} catch {
    Write-Host "[invalid] config\models.json"
    $failed = $true
}

if (Test-Path -LiteralPath $presetPath) {
    $modelLines = Get-Content -LiteralPath $presetPath | Where-Object { $_ -match '^model\s*=\s*(.+)$' }
    foreach ($line in $modelLines) {
        $relativePath = ($line -split '=', 2)[1].Trim()
        $resolved = [System.IO.Path]::GetFullPath((Join-Path (Split-Path $presetPath) $relativePath))
        if (Test-Path -LiteralPath $resolved) {
            Write-Host "[ok] model: $resolved"
        } else {
            Write-Host "[missing] model: $resolved"
            $failed = $true
        }
    }
}

if ($failed) { exit 1 }
Write-Host "Validation passed"
