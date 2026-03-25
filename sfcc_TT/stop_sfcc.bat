@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-Process | Where-Object { $_.ProcessName -like '*FootballClubChampions*' -or $_.ProcessName -eq 'python' -or $_.ProcessName -like '*sfcc*' } | Stop-Process -Force -ErrorAction SilentlyContinue; Remove-Item '.\sfcc_supervisor.pid','.\sfcc_child.pid' -Force -ErrorAction SilentlyContinue"

echo [OK] SFCC scripts and game stopped.
exit /b 0
