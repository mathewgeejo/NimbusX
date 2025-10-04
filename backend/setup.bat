@echo off
echo ========================================
echo Will It Rain On My Parade? - Backend Setup
echo ========================================
echo.

echo Step 1: Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo Error creating virtual environment!
    pause
    exit /b 1
)

echo Step 2: Activating virtual environment...
call venv\Scripts\activate.bat

echo Step 3: Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Error installing dependencies!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo IMPORTANT: Before running the app, you need to:
echo 1. Copy .env.example to .env
echo 2. Add your Gemini API key to .env
echo.
echo Get your API key from: https://makersuite.google.com/app/apikey
echo.
echo After that, run: python app.py
echo ========================================
echo.
pause
