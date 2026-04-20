@echo off
setlocal
cd /d "%~dp0"
set "PWSH=C:\Program Files\PowerShell\7-preview\pwsh.exe"
if exist "%PWSH%" (
  "%PWSH%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
)
endlocal
