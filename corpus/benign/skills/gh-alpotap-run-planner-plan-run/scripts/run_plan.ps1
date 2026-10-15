param(
  # A run folder under runs/ (name or path). Empty = the newest run that still has open tasks.
  [string]$Run = "",
  # Only this phase (e.g. 14). Empty = every task in the plan, in the plan's order.
  [string]$Phase = "",
  # Start at this task (e.g. 14.4); earlier tasks are skipped even if not closed.
  [string]$From = "",
  # Force one model for every task: an alias from runs/runner.json (haiku, sonnet, opus) or a
  # full model id. Empty = per task: its Model: line in the plan, else the default model.
  [string]$Model = "",
  # Let tasks stop with QUESTION FOR OWNER and wait at a menu.
  [switch]$AllowQuestions,
  # Open the plan's (ATTENDED) tasks as live sessions instead of running them headless.
  [switch]$LiveAttended,
  [int]$MaxAutoContinue = 3,
  # The project root. Default: two levels above this script (tools/run-planner/ -> project).
  [string]$Repo = ""
)

# run-planner: runs every open task of one run's plan, one after another, until all are closed.
# Nothing waits for you: usage-limit pauses are waited out (for days if need be), questions
# become recorded decisions, and a task that cannot be done is closed as blocked. The run stops
# early only when a task fails to finish after its automatic continues.
#
#   .\tools\run-planner\run_plan.ps1                          # the newest run with open tasks
#   .\tools\run-planner\run_plan.ps1 -Run 002-fixes -From 14.4
#   .\tools\run-planner\run_plan.ps1 -Phase 15 -AllowQuestions

$ErrorActionPreference = "Stop"
if (-not $Repo) { $Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path }
$runsDir = Join-Path $Repo "runs"

# Models and effort per alias. runs/runner.json may override any of them.
$models = @{ "haiku" = "claude-haiku-5-5"; "sonnet" = "claude-sonnet-5-5"; "opus" = "claude-opus-5-5" }
$efforts = @{ "haiku" = "medium"; "sonnet" = "low"; "opus" = "" }
$defaultAlias = "sonnet"
$cfgPath = Join-Path $runsDir "runner.json"
if (Test-Path $cfgPath) {
  $cfg = Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($cfg.models) { foreach ($p in $cfg.models.PSObject.Properties) { $models[$p.Name.ToLower()] = [string]$p.Value } }
  if ($cfg.effort) { foreach ($p in $cfg.effort.PSObject.Properties) { $efforts[$p.Name.ToLower()] = [string]$p.Value } }
  if ($cfg.defaultModel) { $defaultAlias = ([string]$cfg.defaultModel).ToLower() }
}

function Get-Status($ledger, $t) {
  if (-not (Test-Path $ledger)) { return "" }
  $row = Select-String -Path $ledger -Pattern "^\|\s*$([regex]::Escape($t))\s*\|" | Select-Object -Last 1
  if ($row -and $row.Line -match "^\|[^|]*\|\s*([a-z]+)\s*\|") { return $Matches[1] }
  return ""
}
# Each task heading, with what the plan says about it: (ATTENDED) in the heading, and the
# **Size:**, **Model:**, **Effort:** and **Tools:** lines before the next heading.
function Get-PlanTasks($planPath) {
  $list = @(); $cur = $null
  foreach ($line in Get-Content $planPath -Encoding UTF8) {
    if ($line -match "^### Task (\d+\.\d+)\b") {
      $cur = [pscustomobject]@{ id = $Matches[1]; attended = ($line -match "\(ATTENDED\)"); model = ""; size = "M"; effort = ""; tools = "" }
      $list += $cur
    } elseif ($line -match "^#{1,3} ") { $cur = $null }
    elseif ($cur) {
      if ($line -match "\*\*Model:\s*([\w.-]+)\s*\*\*") { $cur.model = $Matches[1].ToLower() }
      if ($line -match "\*\*Size:\s*([SML])\b") { $cur.size = $Matches[1].ToUpper() }
      if ($line -match "\*\*Effort:\s*(\w+)\s*\*\*") { $cur.effort = $Matches[1].ToLower() }
      if ($line -match "\*\*Tools:\s*([^*]+)\*\*") { $cur.tools = $Matches[1].Trim() }
    }
  }
  return $list
}
function Get-OpenCount($dir) {
  $plan = Join-Path $dir "PLAN.md"; $ledger = Join-Path $dir "PROGRESS.md"
  if (-not (Test-Path $plan)) { return 0 }
  return @(Get-PlanTasks $plan | Where-Object { (Get-Status $ledger $_.id) -notin @("done", "blocked") }).Count
}

# An archived run is closed for good, whatever its rows say: its ledger starts with the
# "Archived run" note (add it by hand to retire a run).
function Test-Archived($dir) {
  $ledger = Join-Path $dir "PROGRESS.md"
  if (-not (Test-Path $ledger)) { return $false }
  return [bool](Get-Content $ledger -TotalCount 5 -Encoding UTF8 | Where-Object { $_ -match "Archived run" })
}

if (-not $Run) {
  $dirs = @(Get-ChildItem $runsDir -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "^\d{3}-" } |
            Sort-Object Name | Where-Object { -not (Test-Archived $_.FullName) })
  $withOpen = @($dirs | Where-Object { (Get-OpenCount $_.FullName) -gt 0 })
  if ($withOpen.Count -eq 0) {
    $latest = if ($dirs.Count) { "runs/$($dirs[-1].Name) has every task closed" } else { "there is no active run" }
    Write-Host "Nothing to run: $latest. Plan the next one with the run-planner skill." -ForegroundColor Green
    exit 0
  }
  $Run = $withOpen[-1].Name
}
$runDir = if (Test-Path (Join-Path $runsDir $Run)) { Join-Path $runsDir $Run } else { Join-Path $Repo $Run }
if (Test-Archived $runDir) {
  Write-Host "runs/$(Split-Path $runDir -Leaf) is archived (its PROGRESS.md says so) - not running it." -ForegroundColor Red
  exit 1
}
$runName = Split-Path $runDir -Leaf
$runRel = "runs/$runName"
$planPath = Join-Path $runDir "PLAN.md"
$ledgerPath = Join-Path $runDir "PROGRESS.md"
if (-not (Test-Path $planPath)) {
  Write-Host "Plan not found: $planPath" -ForegroundColor Red
  exit 1
}

$all = @(Get-PlanTasks $planPath)
$tasks = @($all | Where-Object { -not $Phase -or $_.id -like "$Phase.*" } | ForEach-Object { $_.id })
if ($From) {
  $i = [array]::IndexOf($tasks, $From)
  if ($i -lt 0) { Write-Host "Task $From is not in $runRel/PLAN.md." -ForegroundColor Red; exit 1 }
  $tasks = @($tasks[$i..($tasks.Count - 1)])
}
if ($tasks.Count -eq 0) {
  Write-Host "No matching '### Task' headings in $runRel/PLAN.md - nothing was run." -ForegroundColor Red
  exit 1
}
$attended = @($all | Where-Object { $_.attended } | ForEach-Object { $_.id })
function Get-Status1($t) { return Get-Status $ledgerPath $t }
Write-Host "Run:   $runRel" -ForegroundColor Cyan

$open = @($tasks | Where-Object { (Get-Status1 $_) -notin @("done", "blocked") })
Write-Host "Tasks: $($tasks -join ', ')" -ForegroundColor Cyan
Write-Host "Open:  $(if ($open.Count) { $open -join ', ' } else { 'none' })" -ForegroundColor Cyan

# Keep Windows from sleeping while the run lasts (the display may still turn off). A closed lid
# can still suspend the machine: set "When I close the lid" to "Do nothing" for multi-day runs.
if ($env:OS -eq "Windows_NT") {
  try {
    Add-Type -Namespace RunPlan -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
    [RunPlan.Power]::SetThreadExecutionState([uint32]"0x80000001") | Out-Null   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED
  } catch { Write-Host "Could not stop the machine from sleeping: $_" -ForegroundColor DarkYellow }
}

$started = Get-Date
foreach ($t in $open) {
  $info = $all | Where-Object { $_.id -eq $t } | Select-Object -First 1
  $alias = if ($Model) { $Model.ToLower() } elseif ($info.model) { $info.model } else { $defaultAlias }
  $m = if ($models.ContainsKey($alias)) { $models[$alias] } else { $alias }   # an alias, or a full id
  $e = if ($info.effort) { $info.effort } elseif ($efforts.ContainsKey($alias)) { $efforts[$alias] } else { "" }
  Write-Host "`n=== Task $t ($(Get-Date -Format 'ddd HH:mm')) - size $($info.size), $alias$(if ($e) { ", $e effort" }) ===" -ForegroundColor Cyan
  $live = $LiveAttended -and ($attended -contains $t)
  if ($live) { Write-Host "Task $t is ATTENDED: it opens live so you can watch and check it." -ForegroundColor Cyan }
  & "$PSScriptRoot\run_task.ps1" -Task $t -Repo $Repo -Run $runRel -Model $m -Effort $e -Size $info.size `
      -Tools $info.tools -Interactive:$live -Unattended:(-not $AllowQuestions) -MaxAutoContinue $MaxAutoContinue
  if ($LASTEXITCODE -ne 0) {
    Write-Host "`nStopped at Task $t after $([math]::Round(((Get-Date) - $started).TotalHours, 1)) h. Rerun the same command to continue from it." -ForegroundColor Red
    exit 1
  }
}

# Summary: what to look at, now that everything has run.
Write-Host "`nAll tasks closed in $([math]::Round(((Get-Date) - $started).TotalHours, 1)) h." -ForegroundColor Green
$blocked = @($tasks | Where-Object { (Get-Status1 $_) -eq "blocked" })
if ($blocked.Count) { Write-Host "Blocked (reason in each note in $runRel/PROGRESS.md): $($blocked -join ', ')" -ForegroundColor Red }
$review = @($tasks | Where-Object { $attended -contains $_ })
if ($review.Count) { Write-Host "Look at these yourself: $($review -join ', ')" -ForegroundColor Yellow }
if (Test-Path (Join-Path $runDir "ADVERSARY.md")) { Write-Host "The adversary check's findings: $runRel/ADVERSARY.md" -ForegroundColor Yellow }
Write-Host "Decisions taken for you: search $runRel/PROGRESS.md for 'Decisions to review'." -ForegroundColor Yellow
$csv = Join-Path (Join-Path (Join-Path $Repo ".runlogs") $runName) "usage.csv"
if (Test-Path $csv) {
  $rows = @(Import-Csv $csv | Where-Object { $tasks -contains $_.task })
  $byTask = $rows | Group-Object task | ForEach-Object {
    [pscustomobject]@{
      task = $_.Name
      model = ($_.Group | Select-Object -Last 1).model
      minutes = [math]::Round(($_.Group | Measure-Object minutes -Sum).Sum, 0)
      turns = ($_.Group | Measure-Object turns -Sum).Sum
      context_M = [math]::Round(($_.Group | ForEach-Object { [double]$_.cache_read } | Measure-Object -Sum).Sum / 1e6, 1)
      cost_usd = [math]::Round(($_.Group | ForEach-Object { if ($_.cost_usd) { [double]$_.cost_usd } else { 0 } } | Measure-Object -Sum).Sum, 2)
    }
  }
  Write-Host "`nWhere the time and tokens went (context_M = millions of context tokens re-read):"
  $byTask | Sort-Object context_M -Descending | Format-Table -AutoSize | Out-String -Width 200 | ForEach-Object { Write-Host $_ }
}
