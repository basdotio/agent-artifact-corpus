# install-task.ps1 - 使用任务计划程序安装（备选方案）
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  贾维斯 MCP 桥接器 - 任务计划安装" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$taskName = "JarvisMCPBridge_AutoStart"
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$startScript = Join-Path $scriptPath "start-service.bat"

Write-Host "Install dir: $scriptPath"
Write-Host "Start script: $startScript"
Write-Host ""

# Check if script exists
if (-not (Test-Path $startScript)) {
    Write-Host "ERROR: start-service.bat not found" -ForegroundColor Red
    exit 1
}

# Check if task exists
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Task exists, removing..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

# Create task action
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$startScript`"" -WorkingDirectory $scriptPath

# Create trigger (at logon)
$trigger = New-ScheduledTaskTrigger -AtLogon

# Create settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Seconds 5) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)

# Create principal
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Highest

# Register task
Write-Host "Creating scheduled task..."
Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Jarvis MCP Bridge - Auto start on login"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  SUCCESS! Task installed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Task name: $taskName" -ForegroundColor Cyan
Write-Host ""
Write-Host "Commands:" -ForegroundColor Cyan
Write-Host "  Start: Start-ScheduledTask -TaskName $taskName"
Write-Host "  Stop: Stop-ScheduledTask -TaskName $taskName"
Write-Host "  Status: Get-ScheduledTask -TaskName $taskName"
Write-Host ""

# Start now
Write-Host "Starting task now..."
Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 2

$status = Get-ScheduledTask -TaskName $taskName
Write-Host "Task state: $($status.State)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Done! Service will auto-start on next login." -ForegroundColor Green
