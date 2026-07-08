param(
    [string]$Prompt,
    [string]$PromptFile,
    [string]$Model = "prompt",
    [int]$MaxTokens = 700,
    [double]$Temperature = 0.15,
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env.docker"

[Console]::InputEncoding = [System.Text.UTF8Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::UTF8
$OutputEncoding = [System.Text.UTF8Encoding]::UTF8

if ([string]::IsNullOrWhiteSpace($Prompt) -and -not [string]::IsNullOrWhiteSpace($PromptFile)) {
    $Prompt = [System.Text.Encoding]::UTF8.GetString([System.IO.File]::ReadAllBytes((Resolve-Path -LiteralPath $PromptFile)))
}

if ([string]::IsNullOrWhiteSpace($Prompt)) {
    $Prompt = "Write a simple API for checking server health."
}

$keyLine = Get-Content -LiteralPath $envFile -Encoding UTF8 |
    Where-Object { $_ -match '^\s*ORCHESTRATOR_API_KEY\s*=' } |
    Select-Object -First 1

if (-not $keyLine) {
    throw "ORCHESTRATOR_API_KEY was not found in .env.docker"
}

$apiKey = ($keyLine -split "=", 2)[1].Trim()
$headers = @{
    Authorization = "Bearer $apiKey"
    "Content-Type" = "application/json; charset=utf-8"
}

$body = @{
    prompt = $Prompt.Trim()
    model = $Model
    temperature = $Temperature
    max_tokens = $MaxTokens
} | ConvertTo-Json -Depth 10

$response = Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8090/prompt/improve" `
    -Headers $headers `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($body))

if ($Json) {
    $response | ConvertTo-Json -Depth 10
} else {
    $response
}
