@echo off
setlocal enabledelayedexpansion
title Instalador MCP LinkedIn

echo =======================================================
echo          INSTALADOR ASISTIDO - MCP LINKEDIN
echo =======================================================
echo.

:: 1. Comprobar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no se encuentra en el PATH.
    echo Por favor, instala Python 3.10 o superior desde https://www.python.org/
    pause
    exit /b 1
)

echo [1/4] Instalando dependencias del proyecto...
python -m pip install --upgrade pip
pip install -e .
if %errorlevel% neq 0 (
    echo [AVISO] Fallo al instalar en modo editable, intentando con requirements.txt...
    pip install -r requirements.txt
)

echo.
echo [2/4] Instalando navegadores de Playwright...
playwright install chromium

echo.
echo [3/4] Preparando archivo de configuracion local...
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [OK] Creado archivo .env a partir de .env.example
    )
) else (
    echo [INFO] Archivo .env ya existente.
)

echo.
echo [4/4] Verificando instalacion de MCP...
python -c "import mcp, playwright, bs4; print('[OK] Modulos principales cargados correctamente.')"

echo.
echo =======================================================
echo     INSTALACION COMPLETADA EXITOSAMENTE
echo =======================================================
echo.
echo Puedes iniciar el servidor ejecutando:
echo   mcp-linkedin
echo.
echo O configurarlo en Claude Desktop / Cursor / Antigravity
echo siguiendo las instrucciones de README.md.
echo.
pause
