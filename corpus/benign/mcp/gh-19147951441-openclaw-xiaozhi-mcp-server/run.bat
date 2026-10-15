@echo off
chcp 65001 >nul
title 贾维斯 MCP 桥接器

echo ========================================
echo   贾维斯 MCP 桥接器
echo ========================================
echo.
echo Starting Jarvis MCP Bridge...
echo.

cd /d "%~dp0"
set PYTHONUNBUFFERED=1

:loop
echo [%date% %time%] Starting bridge.py...
python bridge.py
echo.
echo [%date% %time%] Process exited, restarting in 5 seconds...
timeout /t 5 /nobreak
echo.
goto loop
