@echo off
chcp 65001 >nul
cd /d "%~dp0"
title MoySklad connector - uninstall

set "PYCMD="
py -3 --version >nul 2>nul && set "PYCMD=py -3"
if not defined PYCMD (
  python --version >nul 2>nul && set "PYCMD=python"
)
if not defined PYCMD (
  echo Python 3 not found - nothing to do.
  pause
  exit /b 1
)

%PYCMD% "%~dp0setup.py" --uninstall
echo.
echo You can now delete this folder if you no longer need the connector.
echo.
pause
