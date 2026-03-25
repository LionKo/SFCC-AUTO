@echo off
setlocal
cd /d "%~dp0"

if not exist ".\.venv\Scripts\python.exe" (
  echo [ERROR] Python virtual environment not found: .\.venv\Scripts\python.exe
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-Process | Where-Object { $_.ProcessName -like '*FootballClubChampions*' -or $_.ProcessName -eq 'python' -or $_.ProcessName -like '*sfcc*' } | Stop-Process -Force -ErrorAction SilentlyContinue; Remove-Item '.\sfcc_supervisor.pid','.\sfcc_child.pid' -Force -ErrorAction SilentlyContinue; Start-Process -FilePath 'C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe' -ArgumentList '-NoProfile -ExecutionPolicy Bypass -Command ""Set-Location ''%cd%''; & ''%cd%\.venv\Scripts\python.exe'' ''%cd%\sfcc_supervisor.py'' *> ''%cd%\sfcc_supervisor.log''""' -WindowStyle Hidden"

echo [OK] SFCC supervisor started in background.
exit /b 0
