$ErrorActionPreference = "Stop"
cd $PSScriptRoot
if (!(Test-Path .\.venv\Scripts\Activate.ps1)) {
  python -m venv .venv
}
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip wheel
if (Test-Path .\requirements.txt) { pip install -r requirements.txt }
Write-Host "Venv ready. You can now run: python app.py"
