# activate_env.ps1
Write-Host "🔹 Activating virtual environment..."
$venvPath = ".\.venv\Scripts\Activate.ps1"

if (Test-Path $venvPath) {
    & $venvPath
    Write-Host "✅ Virtual environment activated!"
} else {
    Write-Host "❌ Δεν βρέθηκε το .venv. Δημιούργησέ το πρώτα με: python -m venv .venv"
