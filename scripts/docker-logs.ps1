param(
    [ValidateSet("orchestrator", "llama-router", "all")]
    [string]$Service = "all",
    [int]$Tail = 200
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env.docker"
$arguments = @("compose", "--env-file", $envFile, "-f", (Join-Path $root "compose.yaml"), "logs", "--tail", $Tail, "-f")
if ($Service -ne "all") { $arguments += $Service }

& docker @arguments

