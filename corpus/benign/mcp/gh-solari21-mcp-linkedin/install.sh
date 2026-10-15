#!/usr/bin/env bash
set -e

echo "======================================================="
echo "         INSTALADOR ASISTIDO - MCP LINKEDIN"
echo "======================================================="
echo ""

# 1. Comprobar Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 no está instalado o no se encuentra en el PATH."
    exit 1
fi

echo "[1/4] Instalando dependencias de Python..."
python3 -m pip install --upgrade pip
pip install -e . || pip install -r requirements.txt

echo ""
echo "[2/4] Instalando navegadores de Playwright..."
playwright install chromium

echo ""
echo "[3/4] Preparando archivo de configuración..."
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "[OK] Creado archivo .env a partir de .env.example"
fi

echo ""
echo "[4/4] Verificando instalación..."
python3 -c "import mcp, playwright, bs4; print('[OK] Módulos principales cargados correctamente.')"

echo ""
echo "======================================================="
echo "    INSTALACIÓN COMPLETADA EXITOSAMENTE"
echo "======================================================="
echo "Puedes iniciar el servidor ejecutando: mcp-linkedin"
