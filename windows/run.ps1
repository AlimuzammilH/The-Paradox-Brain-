# Sets up Paradox on Windows the first time (Python, Ollama, model, packages), then starts a conversation.
param([switch]$Brain)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
$model = if ($env:PARADOX_LLM_MODEL) { $env:PARADOX_LLM_MODEL } else { "qwen2.5:7b-instruct" }

function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Refresh-Path { $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User") }

# Find a Python 3.10 or newer that is already installed; only install 3.12 if there is none.
function Find-Python {
    $ErrorActionPreference = "Continue"   # the py launcher complains on stderr about missing versions; that's expected
    if (Have "py") {
        foreach ($v in "3.13", "3.12", "3.11", "3.10") {
            & py -$v -c "import sys" 2>$null
            if ($LASTEXITCODE -eq 0) { return ,@("py", "-$v") }
        }
    }
    if (Have "python") {
        & python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) { return ,@("python") }
    }
    return $null
}
$python = Find-Python
if (-not $python) {
    Write-Host "Installing Python 3.12..."
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    Refresh-Path
    $python = Find-Python
    if (-not $python) { throw "Python is installed but not found yet. Close this window and start again." }
}
if (-not (Have "ollama")) {
    Write-Host "Installing Ollama..."
    winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements
    Refresh-Path
}
try { Invoke-RestMethod http://localhost:11434/api/tags -TimeoutSec 3 | Out-Null }
catch { Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden; Start-Sleep 5 }
ollama pull $model

# A half-made environment from a failed first run gets rebuilt.
if ((Test-Path .venv) -and -not (Test-Path .venv\Scripts\python.exe)) { Remove-Item -Recurse -Force .venv }
if (-not (Test-Path .venv)) {
    Write-Host "Creating the Python environment with $($python -join ' ')..."
    $exe = $python[0]; $rest = @($python | Select-Object -Skip 1)
    & $exe @rest -m venv .venv
    if (-not (Test-Path .venv\Scripts\python.exe)) { throw "Could not create the Python environment." }
    .\.venv\Scripts\python -m pip install --upgrade pip
    .\.venv\Scripts\python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    .\.venv\Scripts\python -m pip install -r requirements.txt
}
$env:PYTHONIOENCODING = "utf-8"
# Keep everything inside this folder (judging models, memory), so deleting the folder removes it all
# and nothing piles up on C:. Only Python and Ollama are installed system-wide.
$env:HF_HOME = Join-Path $PWD "models"
$env:PARADOX_HOME = Join-Path $PWD "data"
if ($Brain) {
    Write-Host "Starting the brain at http://localhost:8100 (close this window to stop)"
    Start-Job { Start-Sleep 6; Start-Process "http://localhost:8100" } | Out-Null
    .\.venv\Scripts\python -m uvicorn paradox.api:app --port 8100
} else {
    .\.venv\Scripts\python -m paradox --trace @args
}
