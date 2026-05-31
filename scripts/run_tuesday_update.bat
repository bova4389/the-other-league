@echo off
:: Launcher for the Tuesday H2H update script.
:: Called by Windows Task Scheduler — runs from the repo root.

cd /d "%~dp0.."

echo [%DATE% %TIME%] Running Tuesday H2H update... >> scripts\tuesday_update.log
python scripts\tuesday_update.py >> scripts\tuesday_update.log 2>&1
echo [%DATE% %TIME%] Done. >> scripts\tuesday_update.log
