$root = Split-Path -Parent $PSScriptRoot

$envPath = Join-Path $root ".env"
$envDockerPath = Join-Path $root ".env.docker"

function Get-ApiKeyFromFile([string]$filePath) {
    if (-not (Test-Path -LiteralPath $filePath)) {
        return $null
    }
    foreach ($line in Get-Content -LiteralPath $filePath) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) { continue }
        $parts = $trimmed.Split("=", 2)
        if ($parts.Count -eq 2 -and $parts[0].Trim() -eq "ORCHESTRATOR_API_KEY") {
            return $parts[1].Trim()
        }
    }
    return $null
}

Write-Host "--- Local LLM Orchestrator API Keys ---"

$localKey = Get-ApiKeyFromFile $envPath
if ($localKey) {
    Write-Host "Local API Key (.env):" -ForegroundColor Green
    Write-Host "  $localKey"
} else {
    Write-Host "Local API Key (.env): Not set or .env file not found" -ForegroundColor Yellow
}

$dockerKey = Get-ApiKeyFromFile $envDockerPath
if ($dockerKey) {
    Write-Host "Docker API Key (.env.docker):" -ForegroundColor Green
    Write-Host "  $dockerKey"
} else {
    Write-Host "Docker API Key (.env.docker): Not set or .env.docker file not found" -ForegroundColor Yellow
}

Write-Host "---------------------------------------"
