@echo off
chcp 65001 >nul
cd /d "%~dp0"
title MoySklad connector - install

set "PYCMD="
py -3 --version >nul 2>nul && set "PYCMD=py -3"
if not defined PYCMD (
  python --version >nul 2>nul && set "PYCMD=python"
)
if not defined PYCMD (
  echo.
  echo Python 3 not found.
  echo Install it from https://www.python.org/downloads/
  echo IMPORTANT: check "Add python.exe to PATH" during installation, then run install.bat again.
  echo.
  pause
  exit /b 1
)

%PYCMD% "%~dp0setup.py"
echo.
pause
