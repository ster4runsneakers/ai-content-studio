# Start-App.ps1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

# Αν δεν υπάρχει venv, φτιάξ' το
if (!(Test-Path .\.venv\Scripts\Activate.ps1)) {
  python -m venv .venv
}

# Ενεργοποίηση venv σε ΤΟ ΙΔΙΟ shell
. .\.venv\Scripts\Activate.ps1

# Προαιρετικά: install deps αν υπάρχει requirements.txt
if (Test-Path .\requirements.txt) {
  python -m pip install --upgrade pip
  pip install -r requirements.txt
}

# Τρέξε την εφαρμογή
python app.py

# Κράτα ανοιχτό το παράθυρο όταν κλείσει το app
Read-Host "Press Enter to close"
