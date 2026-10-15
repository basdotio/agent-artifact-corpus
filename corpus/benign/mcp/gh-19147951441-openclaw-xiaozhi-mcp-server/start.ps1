# start.ps1 - 启动贾维斯 MCP 桥接器
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

Write-Host "🤖 启动贾维斯 MCP 桥接器..."
Write-Host "================================"

# 检查并安装依赖
Write-Host "检查依赖..."
$requirements = Get-Content requirements.txt
foreach ($line in $requirements) {
    if ($line -match "^\s*#" -or $line -match "^\s*$") { continue }
    $package = $line.Split("=")[0].Trim()
    try {
        $null = python -c "import $package" 2>$null
        Write-Host "  ✓ $package 已安装"
    } catch {
        Write-Host "  📦 安装 $package..."
        pip install $line
    }
}

Write-Host ""
Write-Host "🚀 启动服务..."
python bridge.py
