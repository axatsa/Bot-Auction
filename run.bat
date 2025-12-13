@echo off
echo Starting Auction Bot...
echo.

REM Activate virtual environment
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo Virtual environment not found!
    echo Please create it with: python -m venv .venv
    pause
    exit /b 1
)

REM Run bot
python bot.py

pause
