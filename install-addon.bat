@echo off
REM Install Forever Companion into the Forever client's AddOns folder.
REM
REM   install-addon.bat                     uses the default install path
REM   install-addon.bat "D:\Games\WoW\..."  uses a custom AddOns folder
REM
REM Uses the newest release\ForeverCompanion-*.zip next to this file.

setlocal enabledelayedexpansion

set "ZIP="
for /f "delims=" %%f in ('dir /b /o-n "%~dp0release\ForeverCompanion-*.zip" 2^>nul') do (
    if not defined ZIP set "ZIP=%~dp0release\%%f"
)

if not defined ZIP (
    echo [x] No zip found in "%~dp0release".
    echo     Run: python scripts\build_addon_zip.py
    exit /b 1
)

set "ADDONS=%~1"
if not defined ADDONS set "ADDONS=%ProgramFiles(x86)%\World of Warcraft\_forever_\Interface\AddOns"

if not exist "%ADDONS%" (
    echo [x] AddOns folder not found: "%ADDONS%"
    echo     Pass the correct path, e.g.:
    echo     install-addon.bat "C:\Program Files (x86)\World of Warcraft\_forever_\Interface\AddOns"
    exit /b 1
)

echo Installing "!ZIP!" into
echo   "%ADDONS%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Expand-Archive -LiteralPath '!ZIP!' -DestinationPath '%ADDONS%' -Force"

if errorlevel 1 (
    echo [x] Extract failed.
    exit /b 1
)

echo.
echo [ok] Installed to "%ADDONS%\ForeverCompanion"
echo      Restart World of Warcraft (a .toc change needs a full restart, not /reload).
echo      In game: /fw   ·   /fw diag
