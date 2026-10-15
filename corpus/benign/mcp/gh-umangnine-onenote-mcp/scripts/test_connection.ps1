<#
.SYNOPSIS
    Tests Microsoft OneNote Desktop COM and Backup connectivity for OneNote MCP Server.

.DESCRIPTION
    Verifies that:
    1. PowerShell execution environment meets Single-Threaded Apartment (STA) requirements (auto-relaunches in STA if needed).
    2. OneNote desktop process is running and visible.
    3. Headless zombie background processes are detected and safely cleared.
    4. OneNote COM Automation object can be instantiated and queried.
    5. OneNote backup directory exists and contains .one files.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\test_connection.ps1
    .\scripts\test_connection.ps1 -AutoClean
#>

[CmdletBinding()]
param(
    [switch]$AutoClean = $true
)

# 0. Force UTF-8 Output Encoding for clean console formatting
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 1. Enforce STA (Single-Threaded Apartment) mode
$aptState = [System.Threading.Thread]::CurrentThread.GetApartmentState()
if ($aptState -ne "STA") {
    $sysRoot = if ($env:SystemRoot) { $env:SystemRoot } else { "C:\Windows" }
    $ps51 = Join-Path $sysRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    if (Test-Path $ps51) {
        Write-Host "[INFO] Re-launching in Windows PowerShell 5.1 STA mode..." -ForegroundColor Cyan
        & $ps51 -STA -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath @args
        exit $LASTEXITCODE
    } else {
        Write-Host "[WARN] Current PowerShell Apartment State: $aptState. COM calls may fail without STA." -ForegroundColor Yellow
    }
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "    Microsoft OneNote MCP Environment Diagnostics Tool     " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 2. Check PowerShell Apartment State
Write-Host "[OK] PowerShell Apartment State: STA (Required for OneNote COM)" -ForegroundColor Green

# 3. Check OneNote Desktop Processes & Zombie Management
$oneProcesses = Get-Process -Name "ONENOTE" -ErrorAction SilentlyContinue
if ($oneProcesses) {
    $uiProc = $oneProcesses | Where-Object { $_.MainWindowHandle -ne 0 }
    $zombieProc = $oneProcesses | Where-Object { $_.MainWindowHandle -eq 0 }

    if ($uiProc) {
        Write-Host "[OK] OneNote desktop UI process is running (PID: $($uiProc.Id -join ', '))" -ForegroundColor Green
    } else {
        Write-Host "[WARN] OneNote is running but only as headless background process(es)." -ForegroundColor Yellow
    }

    if ($zombieProc) {
        Write-Host "[INFO] Headless background instances detected: $($zombieProc.Count)." -ForegroundColor Gray
        if ($AutoClean) {
            Write-Host "       Safely terminating headless background instances to prevent COM locks..." -ForegroundColor Cyan
            $zombieProc | Stop-Process -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 600
        }
    }
} else {
    Write-Host "[INFO] OneNote desktop process is not currently running. COM calls will auto-launch OneNote." -ForegroundColor Gray
}

# 4. Test COM Hierarchy Call
Write-Host "`nTesting OneNote COM API connection..." -ForegroundColor Cyan
$comSuccess = $false
try {
    $onenote = New-Object -ComObject OneNote.Application
    $hierarchyXml = ""
    $onenote.GetHierarchy("", 3, [ref]$hierarchyXml)
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($onenote) | Out-Null
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()

    if ($hierarchyXml -and $hierarchyXml.Length -gt 50) {
        [xml]$doc = $hierarchyXml
        $notebooks = $doc.Notebooks.Notebook
        $nbCount = if ($notebooks) { $notebooks.Count } else { 0 }
        Write-Host "[OK] COM GetHierarchy succeeded! Found $nbCount active notebook(s)." -ForegroundColor Green
        $comSuccess = $true

        foreach ($nb in $notebooks) {
            Write-Host "     - Notebook: $($nb.name)" -ForegroundColor White
            if ($nb.Section) {
                foreach ($sec in $nb.Section) {
                    Write-Host "         * Section: $($sec.name)" -ForegroundColor Gray
                }
            }
        }
    } else {
        Write-Host "[WARN] COM responded but hierarchy XML was empty. Ensure at least one notebook is open in OneNote." -ForegroundColor Yellow
    }
} catch {
    $errStr = $_.Exception.ToString()
    Write-Host "[FAIL] OneNote COM Automation failed: $($_.Exception.Message)" -ForegroundColor Red

    if ($errStr -match "0x80040154|REGDB_E_CLASSNOTREG") {
        Write-Host "`n[DIAGNOSIS]: Microsoft OneNote Desktop is NOT installed or COM class is missing." -ForegroundColor Yellow
        Write-Host "             Note: The Store app 'OneNote for Windows 10' does NOT support COM automation." -ForegroundColor Yellow
        Write-Host "             Please install Microsoft OneNote Desktop (365 / 2021 / 2019 / 2016) from:" -ForegroundColor Yellow
        Write-Host "             https://www.onenote.com/download`n" -ForegroundColor White
    } elseif ($errStr -match "0x80080005|CO_E_SERVER_EXEC_FAILURE") {
        Write-Host "`n[DIAGNOSIS]: OneNote COM server execution failed." -ForegroundColor Yellow
        Write-Host "             1. Check if OneNote has a modal dialog, Safe Mode prompt, or password prompt open." -ForegroundColor Yellow
        Write-Host "             2. Make sure OneNote Desktop is launched and visible on your taskbar." -ForegroundColor Yellow
        Write-Host "             3. Try closing OneNote normally and re-running this script.`n" -ForegroundColor Yellow
    } else {
        Write-Host "       Check if OneNote Desktop has any open modal dialogs or requires a restart.`n" -ForegroundColor Yellow
    }
}

# 5. Check Backup Directory (for pyOneNote offline read tools)
Write-Host "`nChecking OneNote local backup files..." -ForegroundColor Cyan

$localAppData = $env:LOCALAPPDATA
if (-not $localAppData -and $env:APPDATA) {
    $localAppData = Join-Path (Split-Path $env:APPDATA -Parent) "Local"
}

$candidateBackupPaths = @(
    "$localAppData\Microsoft\OneNote\16.0\Backup",
    "$localAppData\Microsoft\OneNote\15.0\Backup"
)

$backupFound = $false
foreach ($bPath in $candidateBackupPaths) {
    if (Test-Path $bPath) {
        $oneFiles = Get-ChildItem -Path $bPath -Filter "*.one" -Recurse -ErrorAction SilentlyContinue
        $fileCount = if ($oneFiles) { $oneFiles.Count } else { 0 }
        Write-Host "[OK] Backup directory found: $bPath" -ForegroundColor Green
        Write-Host "[OK] Discovered $fileCount backup (.one) file(s) for offline reading." -ForegroundColor Green
        $backupFound = $true
        break
    }
}

if (-not $backupFound) {
    $defaultExpected = "$localAppData\Microsoft\OneNote\16.0\Backup"
    Write-Host "[WARN] Backup path not found at $defaultExpected" -ForegroundColor Yellow
    Write-Host "       To initialize local backup files:" -ForegroundColor White
    Write-Host "       1. Open OneNote Desktop." -ForegroundColor White
    Write-Host "       2. Navigate to: File -> Options -> Save & Backup." -ForegroundColor White
    Write-Host "       3. Click 'Back Up All Notebooks Now'." -ForegroundColor White
}

Write-Host "`n============================================================" -ForegroundColor Cyan
if ($comSuccess -and $backupFound) {
    Write-Host "Diagnostics Complete: Environment is 100% HEALTHY! 🎉" -ForegroundColor Green
} elseif ($comSuccess) {
    Write-Host "Diagnostics Complete: COM Live Engine OK! (Initialize Backups for Offline Search)" -ForegroundColor Yellow
} else {
    Write-Host "Diagnostics Complete: Please address the warnings above." -ForegroundColor Yellow
}
Write-Host "============================================================" -ForegroundColor Cyan
