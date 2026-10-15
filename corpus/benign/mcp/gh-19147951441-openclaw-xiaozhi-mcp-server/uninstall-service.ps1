# uninstall-service.ps1 - 卸载 MCP 桥接器 Windows 服务
# 以管理员权限运行

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  贾维斯 MCP 桥接器 - 服务卸载程序" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查管理员权限
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "❌ 错误：需要管理员权限" -ForegroundColor Red
    Write-Host "请右键点击此脚本，选择'以管理员身份运行'" -ForegroundColor Yellow
    exit 1
}

$serviceName = "JarvisMCPBridge"
$nssmPath = Join-Path $env:TEMP "nssm-2.24"
$nssmExe = Join-Path $nssmPath "win64\nssm.exe"

Write-Host "🔍 检查服务状态..."

$existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if (-not $existingService) {
    Write-Host "⚠️  服务不存在" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "按任意键退出..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 0
}

Write-Host "✅ 找到服务：$serviceName"

# 停止服务
if ($existingService.Status -eq "Running") {
    Write-Host "🛑 停止服务..."
    Stop-Service -Name $serviceName -Force
    Start-Sleep -Seconds 2
}

# 删除服务
Write-Host "🗑️  删除服务..."
if (Test-Path $nssmExe) {
    & $nssmExe remove $serviceName confirm
} else {
    sc.exe delete $serviceName
}

Start-Sleep -Seconds 1

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✅ 服务已卸载!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
