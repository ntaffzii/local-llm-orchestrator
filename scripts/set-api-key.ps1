param(
    [string]$ApiKey,
    [string]$EnvFile
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

if ([string]::IsNullOrWhiteSpace($EnvFile)) {
    $EnvFile = Join-Path $root ".env.docker"
}

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    $bytes = [byte[]]::new(32)
    $random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $random.GetBytes($bytes)
    } finally {
        $random.Dispose()
    }
    $ApiKey = [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

if ($ApiKey.Length -lt 32) {
    throw "ORCHESTRATOR_API_KEY must contain at least 32 characters."
}

if (-not (Test-Path -LiteralPath $EnvFile)) {
    $template = if ($EnvFile.EndsWith(".env.docker")) {
        Join-Path $root ".env.docker.example"
    } else {
        Join-Path $root ".env.example"
    }
    Copy-Item -LiteralPath $template -Destination $EnvFile
}

$lines = @(Get-Content -LiteralPath $EnvFile)
$replacement = "ORCHESTRATOR_API_KEY=$ApiKey"
$found = $false
$updated = foreach ($line in $lines) {
    if ($line -match '^\s*ORCHESTRATOR_API_KEY\s*=') {
        $found = $true
        $replacement
    } else {
        $line
    }
}
if (-not $found) {
    $updated = @($replacement) + $updated
}

Set-Content -LiteralPath $EnvFile -Value $updated -Encoding utf8
Write-Host "ORCHESTRATOR_API_KEY updated in $EnvFile"
Write-Host "API key: $ApiKey"
