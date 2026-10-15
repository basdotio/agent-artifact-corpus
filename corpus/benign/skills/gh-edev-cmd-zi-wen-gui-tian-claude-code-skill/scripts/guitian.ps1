# 自刎归天: find the Claude Code process that owns this shell and kill it.
# Usage: guitian.ps1 [-DryRun]
param([switch]$DryRun)

# Native installs are claude.exe; npm installs run as node.exe ... @anthropic-ai\claude-code\cli.js
function Test-Claude($proc) {
    if ($proc.Name -ieq 'claude.exe') { return $true }
    if ($proc.Name -ieq 'node.exe' -and $proc.CommandLine -match '@anthropic-ai[\\/]claude-code') { return $true }
    return $false
}

function Kill-Claude($targetId) {
    if ($DryRun) {
        Write-Output "dry-run: would kill claude pid $targetId"
        exit 0
    }
    Stop-Process -Id $targetId -Force
    exit 0
}

# Claude Code exports its own pid to tool shells. Trust it only if that pid
# really is a Claude process (guards against a stale value / reused pid).
if ($env:CLAUDE_PID) {
    $own = Get-CimInstance Win32_Process -Filter "ProcessId=$($env:CLAUDE_PID)" -ErrorAction SilentlyContinue
    if ($own -and (Test-Claude $own)) { Kill-Claude $own.ProcessId }
}

# Fallback: walk up the parent chain. Can dead-end when an intermediate shell
# has already exited (seen under Git Bash), hence CLAUDE_PID first.
$id = $PID
for ($i = 0; $i -lt 20; $i++) {
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$id" -ErrorAction SilentlyContinue
    if (-not $proc) { break }
    $parentId = $proc.ParentProcessId
    if (-not $parentId -or $parentId -eq $id) { break }
    $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$parentId" -ErrorAction SilentlyContinue
    if (-not $parent) { break }
    if (Test-Claude $parent) { Kill-Claude $parentId }
    $id = $parentId
}

[Console]::Error.WriteLine("guitian: no claude process found above pid $PID")
exit 1
