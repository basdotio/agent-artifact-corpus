@echo off
chcp 65001 >nul
echo ============================================================
echo   放行防火墙端口 11125（需要管理员权限）
echo ============================================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if errorlevel 1 (
    echo [提示] 需要管理员权限，正在请求提升...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\"' -Verb RunAs"
    exit /b
)

netsh advfirewall firewall delete rule name="FishingMCP_11125" >nul 2>&1
netsh advfirewall firewall add rule name="FishingMCP_11125" dir=in action=allow protocol=TCP localport=11125

echo.
echo [完成] 端口 11125 已放行！
echo 其他设备可通过 http://你的电脑IP:11125 访问面板和 MCP
echo 可在命令行运行 ipconfig 查看本机 IPv4 地址
echo.
pause
