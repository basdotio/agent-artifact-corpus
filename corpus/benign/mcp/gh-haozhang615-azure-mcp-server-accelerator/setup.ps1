# Quick setup script for MCP Azure Container App deployment
# PowerShell version for Windows users

Write-Host "🚀 MCP Azure Container App - Quick Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if azd is installed
try {
    azd version | Out-Null
    Write-Host "✅ Azure Developer CLI found" -ForegroundColor Green
} catch {
    Write-Host "❌ Azure Developer CLI (azd) is not installed" -ForegroundColor Red
    Write-Host "📦 Please install it from: https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd" -ForegroundColor Yellow
    exit 1
}

# Check if user is logged in
try {
    azd auth login --check-status | Out-Null
    Write-Host "✅ Already logged into Azure" -ForegroundColor Green
} catch {
    Write-Host "🔐 Not logged into Azure. Logging in now..." -ForegroundColor Yellow
    azd auth login
}

Write-Host ""
Write-Host "✅ Setup complete! You're ready to deploy." -ForegroundColor Green
Write-Host ""
Write-Host "🚀 To deploy, simply run:" -ForegroundColor Cyan
Write-Host "   azd up" -ForegroundColor Yellow
Write-Host ""
Write-Host "💡 You will be prompted to choose:" -ForegroundColor Blue
Write-Host "   - Environment name (unique identifier for your deployment)" -ForegroundColor White
Write-Host "   - Azure region (location where resources will be created)" -ForegroundColor White
Write-Host ""
Write-Host "🎯 That's it! No other configuration needed." -ForegroundColor Green
