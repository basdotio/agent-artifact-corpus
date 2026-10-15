@echo off
REM ============================================================================
REM OneNote MCP - One-Click Automated Setup & Configuration Launcher
REM ============================================================================

set "PS_EXE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PS_EXE%" set "PS_EXE=powershell.exe"

"%PS_EXE%" -STA -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_mcp.ps1" %*
pause
