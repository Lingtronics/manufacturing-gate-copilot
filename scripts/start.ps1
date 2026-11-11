param([switch]$Dev, [switch]$Ollama)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) { throw 'Run the README setup commands first.' }
if (-not (Test-Path -LiteralPath 'frontend/dist/index.html')) {
    npm.cmd run build --prefix frontend
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
}
if ($Ollama) {
    $env:LLM_ENABLED = 'true'
    if (-not $env:LLM_MODEL) { $env:LLM_MODEL = 'llama3.2:1b' }
    if (-not $env:LLM_TIMEOUT_SECONDS) { $env:LLM_TIMEOUT_SECONDS = '30' }
}
$serverArgs = @('-m','uvicorn','app.main:app','--app-dir','backend','--host','127.0.0.1','--port','8000')
if ($Dev) { $serverArgs += '--reload' }
& .venv/Scripts/python.exe @serverArgs
