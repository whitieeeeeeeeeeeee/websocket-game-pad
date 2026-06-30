@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==========================================
echo   WiFi SPI Controller Launcher
echo ==========================================
echo.

net session >nul 2>&1
if %errorLevel% == 0 (
    echo [Info] Running with administrator privileges.
    echo.
) else (
    echo [Info] Requesting administrator privileges...
    echo.
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

python start.py

pause
