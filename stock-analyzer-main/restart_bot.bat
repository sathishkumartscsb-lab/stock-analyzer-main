@echo off
echo Stopping any existing bot processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *telegram*" 2>nul
timeout /t 2 /nobreak >nul

echo Starting Telegram Bot...
cd /d "%~dp0"
python start_bot.py
pause

