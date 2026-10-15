@echo off
chcp 65001 >nul
title 钓鱼游戏 MCP Server - Port 11125

echo ============================================================
echo   钓鱼游戏 MCP Server
echo   管理面板: http://localhost:11125
echo   MCP SSE:  http://localhost:11125/mcp
echo   MCP HTTP: http://localhost:11125/mcp-http
echo ============================================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

:: 检查依赖
echo [信息] 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [信息] 安装依赖中...
    pip install -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

python -c "from mcp.server.streamable_http_manager import StreamableHTTPSessionManager" >nul 2>&1
if errorlevel 1 (
    echo [信息] 当前 MCP SDK 版本过旧，正在升级依赖...
    pip install -r "%~dp0requirements.txt" --upgrade
    if errorlevel 1 (
        echo [错误] MCP SDK 升级失败
        pause
        exit /b 1
    )
)

echo [信息] 启动服务器...
echo.
cd /d "%~dp0"
python server.py

pause
