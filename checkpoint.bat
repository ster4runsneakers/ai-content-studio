@echo off
setlocal
cd /d "%~dp0"

set "MSG="
set "TAG="
set "INCFLAG="

echo.
set /p MSG=Commit message (default: checkpoint): 
if "%MSG%"=="" set "MSG=checkpoint"

echo.
set /p TAG=Tag (optional, e.g. v1.1.3) [leave blank for auto]: 

echo.
set /p ANS=Include .env in ZIP? (y/N): 
if /I "%ANS%"=="Y" set "INCFLAG=-IncludeEnv"

echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0checkpoint.ps1" -Message "%MSG%" -Tag "%TAG%" %INCFLAG%
pause
