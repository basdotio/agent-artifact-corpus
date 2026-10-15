@echo off
chcp 65001 >nul
REM ========================================
REM   贾维斯 MCP 桥接器 - 开机启动安装
REM ========================================

echo ========================================
echo   贾维斯 MCP 桥接器 - 开机启动安装
echo ========================================
echo.

set SCRIPT_DIR=%~dp0
set START_BAT=%SCRIPT_DIR%start-service.bat
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

echo Installing to: %STARTUP_FOLDER%
echo.

REM Create shortcut
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%STARTUP_FOLDER%\JarvisMCP.lnk'); $Shortcut.TargetPath = '%START_BAT%'; $Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $Shortcut.IconLocation = 'cmd.exe'; $Shortcut.Description = 'Jarvis MCP Bridge - Auto Start'; $Shortcut.Save()"

echo.
echo ========================================
echo   SUCCESS!
echo ========================================
echo.
echo The service will auto-start on next login.
echo.
echo To start now, run: start-service.bat
echo.
echo Press any key to exit...
pause >nul
