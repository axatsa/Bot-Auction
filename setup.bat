@echo off
echo Auction Bot - Setup Script
echo ==========================
echo.

REM Create virtual environment
echo [1/3] Creating virtual environment...
python -m venv .venv
if %errorlevel% neq 0 (
    echo Failed to create virtual environment!
    pause
    exit /b 1
)
echo Virtual environment created successfully.
echo.

REM Activate virtual environment
echo [2/3] Activating virtual environment...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Failed to activate virtual environment!
    pause
    exit /b 1
)
echo Virtual environment activated.
echo.

REM Install dependencies
echo [3/3] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install dependencies!
    pause
    exit /b 1
)
echo Dependencies installed successfully.
echo.

echo ==========================
echo Setup completed!
echo ==========================
echo.
echo Next steps:
echo 1. Edit .env file with your bot token and settings
echo 2. Run the bot with: run.bat
echo.
pause
