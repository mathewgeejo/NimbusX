@echo off
echo ========================================
echo Starting Will It Rain Backend Server
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Virtual environment not found!
    echo Please run setup.bat first.
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if .env exists
if not exist ".env" (
    echo .env file not found!
    echo Please copy .env.example to .env and add your Gemini API key.
    pause
    exit /b 1
)

echo Starting Flask server...
echo Backend will run at: http://localhost:5000
echo Press Ctrl+C to stop the server
echo.

python app.py
