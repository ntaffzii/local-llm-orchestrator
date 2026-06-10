$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env.docker"

& docker compose --env-file $envFile -f (Join-Path $root "compose.yaml") ps
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

