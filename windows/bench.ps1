# Overnight benchmark: Paradox vs. plain model vs. Hegelion, then blind judging.
# When it finishes, it starts Mise profiling again (if the Mise folder is where it usually is).
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path .venv\Scripts\python.exe)) { Write-Host "Run 'Start Paradox.bat' once first to set things up."; exit 1 }
New-Item -ItemType Directory -Force bench\results | Out-Null
Start-Transcript -Append -Path bench\results\run.log | Out-Null
$env:PYTHONIOENCODING = "utf-8"
$env:HF_HOME = Join-Path $PWD "models"
$env:PARADOX_HOME = Join-Path $PWD "data"
try { Invoke-RestMethod http://localhost:11434/api/tags -TimeoutSec 3 | Out-Null }
catch { Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden; Start-Sleep 5 }

# keep the PC awake while this runs
Add-Type -Namespace W -Name P -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[W.P]::SetThreadExecutionState([uint32]2147483649) | Out-Null

Write-Host "Installing Hegelion (the comparison system)..."
.\.venv\Scripts\python -m pip install --quiet hegelion
Write-Host "Step 1 of 2: answering 30 questions with all three systems. This takes a few hours."
.\.venv\Scripts\python -m bench.run generate
Write-Host "Step 2 of 2: blind judging."
.\.venv\Scripts\python -m bench.run judge
Write-Host "Benchmark finished. Results are in bench\results."

$mise = Join-Path $env:USERPROFILE "Mise\Start profiling.bat"
if (Test-Path $mise) { Write-Host "Restarting Mise profiling..."; Start-Process -FilePath $mise -WorkingDirectory (Split-Path $mise) }
