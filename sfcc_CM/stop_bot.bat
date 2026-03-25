@echo off
setlocal

set "SUPERVISOR_PID=logs\cm_supervisor.pid"
set "CHILD_PID=logs\cm_bot_child.pid"

call :stop_from_pid "%SUPERVISOR_PID%" supervisor
call :stop_from_pid "%CHILD_PID%" "cm_bot child"

endlocal
exit /b 0

:stop_from_pid
if not exist "%~1" (
    echo PID file not found for %~2: %~1
    goto :eof
)
for /f "usebackq delims=" %%p in ("%~1") do set "pid=%%~p"
if not defined pid (
    echo %~2 PID file is empty: %~1
    goto :eof
)
taskkill /pid %pid% /f >nul 2>&1
if errorlevel 1 (
    echo Failed to stop %~2 pid %pid% (maybe already exited)
) else (
    echo Stopped %~2 pid %pid%
)
set "pid="
goto :eof
