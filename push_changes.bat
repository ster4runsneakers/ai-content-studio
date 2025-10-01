@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM -----------------------------------------------------------------
REM push_changes.bat  —  Double-click to add/commit/pull --rebase/push
REM Works on Windows. Place this file in your repo's root folder.
REM Optional: pass a custom commit message as arguments.
REM Example: push_changes.bat "Fix cloud-only bug"
REM -----------------------------------------------------------------

REM 1) Move to this script's folder (repo root)
cd /d "%~dp0"

REM 2) Basic checks
if not exist ".git" (
  echo [ERROR] This folder is not a Git repository (no .git found).
  echo Place this .bat in your repo root and try again.
  pause
  exit /b 1
)

REM 3) Check Git availability
git --version >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Git is not installed or not in PATH.
  echo Install Git for Windows: https://git-scm.com/download/win
  pause
  exit /b 1
)

REM 4) Detect current branch
for /f "usebackq tokens=* delims=" %%b in (`git rev-parse --abbrev-ref HEAD`) do set BR=%%b
if "%BR%"=="" (
  echo [ERROR] Could not detect current branch.
  pause
  exit /b 1
)

REM 5) Check for changes
for /f "usebackq tokens=* delims=" %%s in (`git status --porcelain`) do set CHANGED=1
if not defined CHANGED (
  echo [INFO] No changes to commit. Pulling latest from origin/%BR% just in case...
  git fetch origin
  git pull --rebase origin %BR%
  echo [OK] Up to date. Nothing to push.
  timeout /t 2 >nul
  exit /b 0
)

REM 6) Build commit message: use args if provided, else timestamp
set MSG=%*
if "%MSG%"=="" (
  for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString(\"yyyy-MM-dd_HH-mm-ss\")"') do set TS=%%i
  set MSG=Auto-commit %TS%
)

echo [STEP] Adding changes...
git add -A

echo [STEP] Committing: %MSG%
git commit -m "%MSG%"
if errorlevel 1 (
  echo [WARN] Commit failed (maybe nothing to commit?). Continuing...
)

echo [STEP] Pull --rebase from origin/%BR%...
git fetch origin
git pull --rebase origin %BR%
if errorlevel 1 (
  echo.
  echo [WARN] Rebase failed. Attempting to abort rebase...
  git rebase --abort >nul 2>&1
  echo [HINT] Resolve conflicts manually if they exist, then re-run this script.
  pause
  exit /b 1
)

echo [STEP] Pushing to origin/%BR%...
git push origin %BR%
if errorlevel 1 (
  echo [ERROR] Push failed. Check your credentials or remote permissions.
  echo If this is the first push for this branch, try:
  echo   git push --set-upstream origin %BR%
  pause
  exit /b 1
)

echo [OK] Push completed successfully on branch %BR%.
timeout /t 2 >nul
exit /b 0
