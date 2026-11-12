# Sets up Paradox on Windows the first time (Python, Ollama, model, packages), then starts a conversation.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$model = if ($env:PARADOX_LLM_MODEL) { $env:PARADOX_LLM_MODEL } else { "qwen2.5:7b-instruct" }

function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Refresh-Path { $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User") }

if (-not (Have "py") -and -not (Have "python")) {
    Write-Host "Installing Python 3.12..."
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    Refresh-Path
}
if (-not (Have "ollama")) {
    Write-Host "Installing Ollama..."
    winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements
    Refresh-Path
}
try { Invoke-RestMethod http://localhost:11434/api/tags -TimeoutSec 3 | Out-Null }
catch { Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden; Start-Sleep 5 }
ollama pull $model

if (-not (Test-Path .venv)) {
    Write-Host "Creating the Python environment..."
    if (Have "py") { py -3.12 -m venv .venv } else { python -m venv .venv }
    .\.venv\Scripts\python -m pip install --upgrade pip
    .\.venv\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    .\.venv\Scripts\python -m pip install -r requirements.txt
}
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python -m paradox --trace @args
