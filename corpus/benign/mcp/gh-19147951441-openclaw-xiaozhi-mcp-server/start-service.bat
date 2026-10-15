@echo off
chcp 65001 >nul
REM ========================================
REM   贾维斯 MCP 桥接器 - 开机启动脚本
REM   (任务计划程序版本 - 备选方案)
REM ========================================

cd /d "%~dp0"
set PYTHONUNBUFFERED=1

echo [%date% %time%] 贾维斯 MCP 桥接器启动...

:loop
python bridge.py
echo [%date% %time%] 进程意外退出，5 秒后重启...
timeout /t 5 /nobreak >nul
goto loop
