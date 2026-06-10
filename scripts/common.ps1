$ErrorActionPreference = "Stop"

$script:Root = Split-Path -Parent $PSScriptRoot
$script:RunDir = Join-Path $script:Root "run"
$script:EnvFile = Join-Path $script:Root ".env"

function Import-LocalEnv {
    if (-not (Test-Path -LiteralPath $script:EnvFile)) { return }
    foreach ($line in Get-Content -LiteralPath $script:EnvFile) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) { continue }
        $parts = $trimmed.Split("=", 2)
        if ($parts.Count -eq 2) {
            [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
        }
    }
}

function Get-Setting([string]$Name, [string]$Default) {
    $value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($value)) { return $Default }
    return $value
}

function Test-ProcessId([string]$PidFile) {
    if (-not (Test-Path -LiteralPath $PidFile)) { return $false }
    $processId = Get-Content -LiteralPath $PidFile -ErrorAction SilentlyContinue
    return $null -ne (Get-Process -Id $processId -ErrorAction SilentlyContinue)
}

