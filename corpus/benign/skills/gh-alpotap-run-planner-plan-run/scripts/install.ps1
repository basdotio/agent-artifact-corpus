param(
  # The project to set up. Default: the current directory.
  [string]$Project = (Get-Location).Path
)

# run-planner: puts the runner into a project, or refreshes it there.
#
#   tools/run-planner/run_plan.ps1, run_task.ps1, new_run.ps1, VERSION   always replaced
#   runs/runner.json                                                      created once, never overwritten
#   runs/PROJECT.md                                                       created once from the template
#   .gitignore                                                            gains .runlogs/ if missing

$ErrorActionPreference = "Stop"
$skillDir = Split-Path $PSScriptRoot -Parent
$Project = (Resolve-Path $Project).Path
$version = (Get-Content (Join-Path $skillDir "VERSION") -TotalCount 1).Trim()

$dest = Join-Path $Project "tools\run-planner"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
foreach ($f in "run_plan.ps1", "run_task.ps1", "new_run.ps1") {
  Copy-Item (Join-Path $PSScriptRoot $f) (Join-Path $dest $f) -Force
}
Set-Content -Path (Join-Path $dest "VERSION") -Value $version -Encoding ASCII

$runs = Join-Path $Project "runs"
New-Item -ItemType Directory -Force -Path $runs | Out-Null
foreach ($t in "runner.json", "PROJECT.md") {
  $target = Join-Path $runs $t
  if (-not (Test-Path $target)) {
    Copy-Item (Join-Path $skillDir "templates\$t") $target
    Write-Host "Created runs/$t - fill it in for this project." -ForegroundColor Yellow
  }
}

$gi = Join-Path $Project ".gitignore"
$hasIgnore = (Test-Path $gi) -and (Select-String -Path $gi -Pattern "^/?\.runlogs/?$" -Quiet)
if (-not $hasIgnore) { Add-Content -Path $gi -Value ".runlogs/" ; Write-Host "Added .runlogs/ to .gitignore." }

Write-Host "run-planner $version installed in $dest." -ForegroundColor Green
