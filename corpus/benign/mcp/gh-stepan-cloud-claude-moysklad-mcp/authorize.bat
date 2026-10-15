@echo off
chcp 65001 >nul
cd /d "%~dp0"
title MoySklad connector - token

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo Run install.bat first.
  echo.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" "%~dp0authorize.py"
echo.
pause
