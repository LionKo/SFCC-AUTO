@echo off
setlocal

cd /d "%~dp0"

if not exist "logs" mkdir "logs"

if not "%~1"=="" (
    set "SFCC_GAME_EXE_PATH=%~1"
    shift
)

python cm_bot.py --log-level DEBUG %*

endlocal
