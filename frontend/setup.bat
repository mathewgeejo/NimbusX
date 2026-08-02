@echo off
echo ========================================
echo NimbusX frontend setup
echo ========================================
echo.

echo Installing locked dependencies...
call npm ci
if errorlevel 1 (
    echo Dependency installation failed.
    pause
    exit /b 1
)

echo.
echo Setup complete.
echo Run: npm run dev
echo Set VITE_API_BASE_URL only when the control-plane API is not at http://localhost:8000.
echo.
pause