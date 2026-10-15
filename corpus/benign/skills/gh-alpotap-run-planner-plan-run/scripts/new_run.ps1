param(
  # Short name for the run, e.g. tenant-billing. The folder becomes runs/<NNN>-<Name>.
  [Parameter(Mandatory=$true)][string]$Name,
  # The project root. Default: two levels above this script (tools/run-planner/ -> project).
  [string]$Repo = ""
)

# run-planner: creates the folder for a new run - an empty PLAN.md for the planning session to
# fill and a PROGRESS.md ledger holding only the table header. Nothing is committed; the planner
# commits the folder together with the finished plan.

$ErrorActionPreference = "Stop"
if (-not $Repo) { $Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path }
$slug = ($Name.ToLower() -replace "[^a-z0-9]+", "-").Trim("-")
if (-not $slug) { Write-Host "Name '$Name' has no letters or digits." -ForegroundColor Red; exit 1 }

$runsDir = Join-Path $Repo "runs"
New-Item -ItemType Directory -Force -Path $runsDir | Out-Null
$last = Get-ChildItem $runsDir -Directory | Where-Object { $_.Name -match "^(\d{3})-" } |
        ForEach-Object { [int]$Matches[1] } | Sort-Object | Select-Object -Last 1
$id = "{0:D3}-{1}" -f ([int]$last + 1), $slug
$dir = Join-Path $runsDir $id
New-Item -ItemType Directory -Path $dir | Out-Null

$utf8 = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText((Join-Path $dir "PLAN.md"),
  "# $id`n`nWritten by a planning session (run-planner skill).`n", $utf8)
[System.IO.File]::WriteAllText((Join-Path $dir "PROGRESS.md"), (@(
  "# Progress: $id",
  "",
  "Plan: PLAN.md in this folder. Rows are written by the runner. A row's status is done or blocked; the runner skips both.",
  "",
  "| Task | Status | Commit | Notes |",
  "| ---- | ------ | ------ | ----- |",
  ""
) -join "`n"), $utf8)

Write-Host "Created runs/$id (PLAN.md, PROGRESS.md)." -ForegroundColor Green
Write-Host "Run it with: .\tools\run-planner\run_plan.ps1 -Run $id" -ForegroundColor Green
