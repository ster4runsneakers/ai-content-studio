param(
  [string]$Message = "checkpoint",
  [string]$Tag = "",
  [switch]$IncludeEnv
)

$ErrorActionPreference = "Stop"

# 0) Ensure we are inside a git repo
$null = & git rev-parse --is-inside-work-tree 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host "ERROR: Not a git repository. Open PowerShell in the repo folder (where .git exists)." -ForegroundColor Red
  exit 1
}

# 1) Create ZIP in _backups\
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$backupDir = Join-Path (Get-Location) "_backups"
if (-not (Test-Path $backupDir)) {
  New-Item -ItemType Directory -Path $backupDir | Out-Null
}
$zipPath = Join-Path $backupDir ("ai-content-studio_$ts.zip")

# Collect files (safe: exclude .env unless -IncludeEnv is supplied)
$items = Get-ChildItem -Recurse -File | Where-Object {
  $_.FullName -notmatch "\\\.git(\\|$)" -and
  $_.FullName -notmatch "\\\.venv(\\|$)" -and
  $_.FullName -notmatch "\\__pycache__(\\|$)" -and
  $_.Extension -notin @(".pyc", ".pyo", ".zip")
}
if (-not $IncludeEnv) {
  $items = $items | Where-Object { $_.Name -ne ".env" }
}
if ($items.Count -gt 0) {
  Compress-Archive -Path ($items | ForEach-Object { $_.FullName }) -DestinationPath $zipPath -Force
  Write-Host "ZIP created: $zipPath"
} else {
  Write-Host "No files found to include in ZIP."
}

# 2) git add/commit if there are changes
$null = & git add -A
$porcelain = & git status --porcelain
$hasChanges = -not [string]::IsNullOrWhiteSpace($porcelain)
if ($hasChanges) {
  $null = & git commit -m "$Message ($ts)"
  if ($LASTEXITCODE -eq 0) {
    Write-Host "Commit created."
  } else {
    Write-Host "WARNING: git commit failed, continuing..."
  }
} else {
  Write-Host "No changes to commit."
}

# 3) Tag (if none provided, generate save-YYYYMMDD-HHmmss)
if ([string]::IsNullOrWhiteSpace($Tag)) {
  $Tag = "save-$ts"
}
$existingTag = (& git tag -l $Tag)
if ($existingTag -eq $Tag) {
  Write-Host "Tag '$Tag' already exists. Skipping tag creation."
} else {
  $null = & git tag -a $Tag -m "$Message ($ts)"
  Write-Host "Tag created: $Tag"
}

# 4) Push branch and tag
$null = & git push
$null = & git push origin $Tag

Write-Host "Done."
