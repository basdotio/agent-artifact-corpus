@echo off
REM ============================================================================
REM OneNote MCP - Environment Diagnostics Launcher
REM Bypasses PowerShell Execution Policy restrictions and enforces STA mode
REM ============================================================================

set "PS_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS_EXE%" set "PS_EXE=powershell.exe"

"%PS_EXE%" -STA -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\test_connection.ps1" %*
exit /b %ERRORLEVEL%
