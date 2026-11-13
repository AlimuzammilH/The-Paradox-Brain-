# Re-run only Paradox's answers after an engine change, then judge again.
# The plain and Hegelion answers from the last run are kept. The old Paradox answers and verdicts are
# moved into a dated folder inside bench\results, never deleted.
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path .venv\Scripts\python.exe)) { Write-Host "Run 'Start Paradox.bat' once first to set things up."; exit 1 }
$res = "bench\results"
$old = Join-Path $res ("previous-" + (Get-Date -Format "yyyy-MM-dd_HHmm"))
New-Item -ItemType Directory -Force $old | Out-Null
foreach ($f in "paradox.jsonl", "judgements.jsonl", "errors.log") { if (Test-Path "$res\$f") { Move-Item "$res\$f" $old } }
Start-Transcript -Append -Path "$res\run.log" | Out-Null
$env:PYTHONIOENCODING = "utf-8"
$env:HF_HOME = Join-Path $PWD "models"
$env:PARADOX_HOME = Join-Path $PWD "data"
try { Invoke-RestMethod http://localhost:11434/api/tags -TimeoutSec 3 | Out-Null }
catch { Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden; Start-Sleep 5 }
Add-Type -Namespace W -Name P -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[W.P]::SetThreadExecutionState([uint32]2147483649) | Out-Null

Write-Host "Previous results moved to $old"
Write-Host "Step 1 of 2: Paradox answers the 30 questions again (about an hour)."
.\.venv\Scripts\python -m bench.run generate --systems paradox
Write-Host "Step 2 of 2: blind judging (uses the judge set in .env, if any)."
.\.venv\Scripts\python -m bench.run judge
.\.venv\Scripts\python -m bench.run report
Write-Host "Done. Results are in bench\results."

$mise = Join-Path $env:USERPROFILE "Mise\Start profiling.bat"
if (Test-Path $mise) { Write-Host "Restarting Mise profiling..."; Start-Process -FilePath $mise -WorkingDirectory (Split-Path $mise) }
