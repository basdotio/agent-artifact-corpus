<#
.SYNOPSIS
    Automated Setup and Configuration Script for OneNote MCP Server on Windows.

.DESCRIPTION
    1. Detects or creates the Python virtual environment (.venv) using uv or pip.
    2. Synchronizes required dependencies (mcp[cli], pyonenote).
    3. Configures Google Antigravity MCP settings and registers schemas & skills.
    4. Provides automated registration for Claude Code and Claude Desktop.
    5. Runs environment diagnostics (scripts\test_connection.ps1).

.PARAMETER Client
    Target AI assistant client: 'antigravity', 'claude', 'all' (Default: 'all').

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\scripts\setup_mcp.ps1
    .\setup_mcp.cmd
#>

[CmdletBinding()]
param(
    [ValidateSet("antigravity", "claude", "all")]
    [string]$Client = "all"
)

# Force UTF-8 Output Encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $repoRoot

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "     Microsoft OneNote MCP Automated Setup & Configurator   " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Repository Root: $repoRoot`n" -ForegroundColor White

# -----------------------------------------------------------------------------
# 1. Python Environment Setup
# -----------------------------------------------------------------------------
Write-Host "==> Step 1: Setting up Python Virtual Environment..." -ForegroundColor Cyan

$pythonExe = "$repoRoot\.venv\Scripts\python.exe"
$uvPath = Get-Command uv -ErrorAction SilentlyContinue

if ($uvPath) {
    Write-Host "[OK] Detected 'uv' package manager. Synchronizing dependencies..." -ForegroundColor Green
    & uv sync
} elseif (Test-Path $pythonExe) {
    Write-Host "[OK] Existing .venv detected at $pythonExe" -ForegroundColor Green
    & $pythonExe -m pip install --quiet --upgrade "mcp[cli]>=1.26.0" "pyonenote>=0.0.2"
} else {
    Write-Host "[INFO] Creating virtual environment using standard python..." -ForegroundColor Yellow
    $systemPython = Get-Command python -ErrorAction SilentlyContinue
    if (-not $systemPython) {
        Write-Error "[FAIL] Neither 'uv' nor 'python' was found in PATH. Please install Python 3.12+ (or uv)."
        exit 1
    }
    python -m venv "$repoRoot\.venv"
    & $pythonExe -m pip install --quiet --upgrade pip
    & $pythonExe -m pip install --quiet "mcp[cli]>=1.26.0" "pyonenote>=0.0.2"
}

if (-not (Test-Path $pythonExe)) {
    Write-Error "[FAIL] Virtual environment Python executable not found at $pythonExe"
    exit 1
}
Write-Host "[OK] Python environment ready: $pythonExe" -ForegroundColor Green

# -----------------------------------------------------------------------------
# 2. Configure Google Antigravity
# -----------------------------------------------------------------------------
if ($Client -in @("antigravity", "all")) {
    Write-Host "`n==> Step 2: Configuring Google Antigravity IDE..." -ForegroundColor Cyan
    $userProfile = $env:USERPROFILE
    $antigravityMcpConfig = "$userProfile\.gemini\antigravity\mcp_config.json"
    $antigravitySchemaDir = "$userProfile\.gemini\antigravity\mcp\onenote"
    $antigravitySkillDir = "$userProfile\.gemini\config\skills\onenote-mcp"

    # A. Update mcp_config.json
    try {
        $mcpConfigObj = @{ mcpServers = @{} }
        if (Test-Path $antigravityMcpConfig) {
            $rawJson = Get-Content $antigravityMcpConfig -Raw -Encoding UTF8
            if (-not [string]::IsNullOrWhiteSpace($rawJson)) {
                $mcpConfigObj = $rawJson | ConvertFrom-Json
                if (-not $mcpConfigObj.mcpServers) {
                    $mcpConfigObj | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value (New-Object PSObject)
                }
            }
        } else {
            $parentDir = Split-Path $antigravityMcpConfig -Parent
            if (-not (Test-Path $parentDir)) { New-Item -ItemType Directory -Path $parentDir -Force | Out-Null }
        }

        $serverPy = "$repoRoot\server.py"
        $onenoteEntry = [PSCustomObject]@{
            command = $pythonExe
            args = @($serverPy)
            env = [PSCustomObject]@{
                ONENOTE_BACKUP_DIR = "$env:LOCALAPPDATA\Microsoft\OneNote\16.0\Backup"
            }
        }

        $mcpConfigObj.mcpServers | Add-Member -MemberType NoteProperty -Name "onenote" -Value $onenoteEntry -Force
        $mcpConfigObj | ConvertTo-Json -Depth 10 | Set-Content -Path $antigravityMcpConfig -Encoding UTF8
        Write-Host "[OK] Registered 'onenote' MCP server in $antigravityMcpConfig" -ForegroundColor Green
    } catch {
        Write-Host "[WARN] Could not automatically update ${antigravityMcpConfig}: $_" -ForegroundColor Yellow
    }

    # B. Copy Tool Schemas
    if (Test-Path "$repoRoot\schemas") {
        if (-not (Test-Path $antigravitySchemaDir)) {
            New-Item -ItemType Directory -Path $antigravitySchemaDir -Force | Out-Null
        }
        Copy-Item -Path "$repoRoot\schemas\*.json" -Destination $antigravitySchemaDir -Force
        Write-Host "[OK] Installed $( (Get-ChildItem "$repoRoot\schemas\*.json").Count ) tool schemas to $antigravitySchemaDir" -ForegroundColor Green
    }

    # C. Copy Agent Skill
    if (Test-Path "$repoRoot\skills\onenote-mcp") {
        if (-not (Test-Path $antigravitySkillDir)) {
            New-Item -ItemType Directory -Path $antigravitySkillDir -Force | Out-Null
        }
        Copy-Item -Path "$repoRoot\skills\onenote-mcp\*" -Destination $antigravitySkillDir -Recurse -Force
        Write-Host "[OK] Installed OneNote Agent Skill to $antigravitySkillDir" -ForegroundColor Green
    }
}

# -----------------------------------------------------------------------------
# 3. Configure Claude Code CLI
# -----------------------------------------------------------------------------
if ($Client -in @("claude", "all")) {
    Write-Host "`n==> Step 3: Configuring Claude Code CLI..." -ForegroundColor Cyan
    $claudeCmd = Get-Command claude -ErrorAction SilentlyContinue
    if ($claudeCmd) {
        Write-Host "[INFO] Detected 'claude' CLI. Registering MCP server..." -ForegroundColor Cyan
        try {
            & claude mcp add --transport stdio onenote -- "$pythonExe" "$repoRoot\server.py"
            Write-Host "[OK] Claude Code MCP server registered successfully." -ForegroundColor Green
        } catch {
            Write-Host "[WARN] 'claude mcp add' encountered an issue: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[INFO] 'claude' CLI not installed in PATH. (If you use Claude Code later, run:)" -ForegroundColor Gray
        Write-Host "       claude mcp add --transport stdio onenote -- `"$pythonExe`" `"$repoRoot\server.py`"" -ForegroundColor Gray
    }
}

# -----------------------------------------------------------------------------
# 4. Run Environment Diagnostics
# -----------------------------------------------------------------------------
Write-Host "`n==> Step 4: Running Environment Diagnostics..." -ForegroundColor Cyan
& powershell -STA -NoProfile -ExecutionPolicy Bypass -File "$repoRoot\scripts\test_connection.ps1"

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "             OneNote MCP Setup Completed! 🎉                " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "You can now interact with Microsoft OneNote via your AI Assistant!" -ForegroundColor Green
