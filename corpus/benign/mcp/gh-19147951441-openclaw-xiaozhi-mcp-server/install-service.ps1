# install-service.ps1 - 安装 MCP 桥接器为 Windows 服务
# 以管理员权限运行

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  贾维斯 MCP 桥接器 - 服务安装程序" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查管理员权限
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "❌ 错误：需要管理员权限" -ForegroundColor Red
    Write-Host "请右键点击此脚本，选择'以管理员身份运行'" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ 管理员权限确认" -ForegroundColor Green

# 获取脚本所在目录
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$servicePath = $scriptPath
$pythonExe = (Get-Command python).Source
$bridgeScript = Join-Path $servicePath "bridge.py"

Write-Host "📁 安装目录：$servicePath"
Write-Host "🐍 Python 路径：$pythonExe"
Write-Host "📄 桥接脚本：$bridgeScript"
Write-Host ""

# 检查文件是否存在
if (-not (Test-Path $bridgeScript)) {
    Write-Host "❌ 错误：找不到 bridge.py" -ForegroundColor Red
    exit 1
}

# 服务配置
$serviceName = "JarvisMCPBridge"
$serviceDisplayName = "贾维斯 MCP 桥接服务"
$serviceDescription = "贾维斯 MCP 小智桥接器 - 让小智客户端连接到贾维斯 (OpenClaw) 处理信息"

Write-Host "🔧 服务配置:" -ForegroundColor Cyan
Write-Host "   服务名称：$serviceName"
Write-Host "   显示名称：$serviceDisplayName"
Write-Host ""

# 创建启动脚本
$startScript = Join-Path $servicePath "start-service.bat"
$batContent = @"
@echo off
chcp 65001 >nul
cd /d "$servicePath"
set PYTHONUNBUFFERED=1
echo [%date% %time%] 贾维斯 MCP 桥接器启动...
"$pythonExe" bridge.py
"@

Set-Content -Path $startScript -Value $batContent -Encoding UTF8
Write-Host "✅ 创建启动脚本：$startScript"

# 使用 NSSM 创建 Windows 服务（推荐方案）
$nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
$nssmPath = Join-Path $env:TEMP "nssm-2.24"
$nssmExe = Join-Path $nssmPath "win64\nssm.exe"

# 检查 NSSM 是否已存在
if (-not (Test-Path $nssmExe)) {
    Write-Host "📥 下载 NSSM..."
    $zipPath = Join-Path $env:TEMP "nssm.zip"
    Invoke-WebRequest -Uri $nssmUrl -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $env:TEMP -Force
}

Write-Host "✅ NSSM 准备就绪"

# 检查服务是否已存在
$existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "⚠️  服务已存在，正在删除..." -ForegroundColor Yellow
    & $nssmExe remove $serviceName confirm
    Start-Sleep -Seconds 1
}

# 安装服务
Write-Host "🔧 安装服务..."
& $nssmExe install $serviceName "$pythonExe" "$bridgeScript"
Start-Sleep -Seconds 1

# 配置服务参数
Write-Host "⚙️  配置服务参数..."
& $nssmExe set $serviceName DisplayName $serviceDisplayName
& $nssmExe set $serviceName Description $serviceDescription
& $nssmExe set $serviceName Start SERVICE_AUTO_START
& $nssmExe set $serviceName AppDirectory "$servicePath"
& $nssmExe set $serviceName AppStdout "$servicePath\service.log"
& $nssmExe set $serviceName AppStderr "$servicePath\service-error.log"
& $nssmExe set $serviceName AppRotateFiles 1
& $nssmExe set $serviceName AppRotateBytes 1048576

# 配置重启恢复
Write-Host "⚙️  配置服务恢复选项..."
sc.exe failure $serviceName reset= 86400 actions= restart/5000/restart/5000/restart/5000

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✅ 服务安装成功!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "服务名称：$serviceName" -ForegroundColor Cyan
Write-Host ""
Write-Host "常用命令:" -ForegroundColor Cyan
Write-Host "  启动服务：net start $serviceName" -ForegroundColor White
Write-Host "  停止服务：net stop $serviceName" -ForegroundColor White
Write-Host "  重启服务：net stop $serviceName && net start $serviceName" -ForegroundColor White
Write-Host "  查看状态：sc query $serviceName" -ForegroundColor White
Write-Host "  查看日志：notepad $servicePath\service.log" -ForegroundColor White
Write-Host ""

# 询问是否立即启动服务
$response = Read-Host "是否立即启动服务？(Y/N)"
if ($response -eq "Y" -or $response -eq "y") {
    Write-Host "🚀 启动服务..."
    Start-Service -Name $serviceName
    Start-Sleep -Seconds 2
    
    $status = Get-Service -Name $serviceName
    if ($status.Status -eq "Running") {
        Write-Host "✅ 服务已启动!" -ForegroundColor Green
    } else {
        Write-Host "❌ 服务启动失败，请查看日志" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
