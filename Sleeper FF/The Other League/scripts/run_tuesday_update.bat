@echo off
:: Launcher for the Tuesday H2H update script.
:: Called by Windows Task Scheduler — runs from the repo root.

cd /d "%~dp0.."

echo [%DATE% %TIME%] Running Tuesday H2H update... >> scripts\tuesday_update.log
:: cp1252 is the default encoding here and the script prints arrows and check
:: marks, so without this the run died on its first status line. GitHub Actions
:: is UTF-8 and was unaffected, which is why this went unnoticed.
set PYTHONIOENCODING=utf-8
python scripts\tuesday_update.py >> scripts\tuesday_update.log 2>&1
echo [%DATE% %TIME%] Done. >> scripts\tuesday_update.log
