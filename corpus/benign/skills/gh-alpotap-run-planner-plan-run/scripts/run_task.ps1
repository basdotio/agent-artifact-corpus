param(
  [Parameter(Mandatory=$true)][string]$Task,
  # The run folder, relative to the repo: its PLAN.md is the plan, its PROGRESS.md the ledger.
  [Parameter(Mandatory=$true)][string]$Run,
  # The project root. Default: two levels above this script (tools/run-planner/ -> project).
  [string]$Repo = "",
  [string]$Model = "claude-sonnet-5-5",
  # Passed as --effort when set (low, medium, high, xhigh, max). Empty = the model's default.
  [string]$Effort = "",
  # S, M or L, from the task's Size line. Sets the turn budget and the ledger note length.
  [string]$Size = "M",
  # Comma-separated tool list for --tools, or "default" for every built-in tool.
  [string]$Tools = "",
  # Run the whole task in a live terminal session instead of headless.
  [switch]$Interactive,
  # Nobody is at the keyboard (run_plan.ps1 sets this): the agent decides instead of asking,
  # usage-limit pauses are waited out, and the script never stops at a menu.
  [switch]$Unattended,
  # How many times a headless task that stops without finishing (and without asking a question)
  # is told to carry on. Waiting out a usage limit or an API outage does not count.
  [int]$MaxAutoContinue = 3
)

# run-planner: runs one task of a run's PLAN.md in a fresh session.
#
#   .\tools\run-planner\run_task.ps1 -Task 15.3 -Run runs/002-correction
#
# The task's own section and the plan's "Rules for every task" section are sent with the prompt,
# so the session does not spend turns finding them. The session commits its code and ends its
# reply with a RESULT block; this script writes the ledger row and commits it.
#
# Exit codes: 0 finished (row done or blocked); 1 stopped by you; 2 gave up.

$ErrorActionPreference = "Stop"
if (-not $Repo) { $Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path }
Set-Location $Repo
$Run = $Run.TrimEnd("/", "\")
$runName = Split-Path $Run -Leaf
# Forward slashes: these paths go into the agent's prompt and work in both Bash and PowerShell.
$Plan = "$Run/PLAN.md".Replace("\", "/")
$Ledger = "$Run/PROGRESS.md".Replace("\", "/")
if (-not (Test-Path $Plan)) { Write-Host "No plan at $Plan" -ForegroundColor Red; exit 2 }

# The stream below is UTF-8, and so is the prompt piped into claude; Windows PowerShell 5.1 would
# otherwise use the OEM code page for one and ASCII for the other.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = New-Object System.Text.UTF8Encoding $false

# Project settings: runs/runner.json (see the skill's references/project-profile.md).
$cfg = $null
$cfgPath = Join-Path $Repo "runs\runner.json"
if (Test-Path $cfgPath) { $cfg = Get-Content $cfgPath -Raw -Encoding UTF8 | ConvertFrom-Json }
$addDirs = @()
if ($cfg -and $cfg.addDirs) {
  foreach ($d in $cfg.addDirs) {
    $p = if ([System.IO.Path]::IsPathRooted($d)) { $d } else { Join-Path $Repo $d }
    if (Test-Path $p) { $addDirs += (Resolve-Path $p).Path }
  }
}
if (-not $Tools) { $Tools = if ($cfg -and $cfg.tools) { ($cfg.tools -join ",") } else { "Bash,PowerShell,Read,Edit,Write,Grep,Glob" } }
if ($cfg -and $cfg.pathAdd) {
  foreach ($p in $cfg.pathAdd) { if ((Test-Path $p) -and ($env:Path -notlike "*$p*")) { $env:Path += ";$p" } }
}

# A headless session ends the moment the agent ends its reply, so a command sent to the
# background never reports back. Turn background tasks off and let foreground commands run long
# enough for image builds and test suites (default 10 min, at most 30 min per command).
$env:CLAUDE_CODE_DISABLE_BACKGROUND_TASKS = "1"
$env:BASH_DEFAULT_TIMEOUT_MS = "600000"
$env:BASH_MAX_TIMEOUT_MS = "1800000"
# Every turn re-sends the whole conversation, so one 200 KB test log is paid for on every later
# turn of the task. Cap what a single command can put into the context.
$env:BASH_MAX_OUTPUT_LENGTH = "20000"
$env:DISABLE_NON_ESSENTIAL_MODEL_CALLS = "1"

# Per-call usage, the raw event stream and the prompt, for finding where the tokens went.
$logDir = Join-Path (Join-Path $Repo ".runlogs") $runName
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$usageCsv = Join-Path $logDir "usage.csv"
if (-not (Test-Path $usageCsv)) {
  "time,task,session,model,turns,minutes,input,output,cache_read,cache_write,cost_usd,end" | Set-Content $usageCsv
}
$eventLog = Join-Path $logDir "$Task.jsonl"
$promptFile = Join-Path $logDir "$Task.prompt.md"

function Get-Row {
  if (-not (Test-Path $Ledger)) { return $null }
  return Select-String -Path $Ledger -Pattern "^\|\s*$([regex]::Escape($Task))\s*\|" | Select-Object -Last 1
}
function Test-RowClosed { $r = Get-Row; return [bool]($r -and $r.Line -match "^\|[^|]*\|\s*(done|blocked)\s*\|") }

if (Test-RowClosed) {
  Write-Host "Task $Task is already closed in $Ledger - nothing to do." -ForegroundColor DarkGray
  exit 0
}

# Windows PowerShell 5.1 turns native stderr into a terminating error under "Stop", and a repo
# with no commits makes git write to stderr - so relax the preference around git calls.
function Invoke-Git([string]$dir, [string[]]$gitArgs) {
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $o = & git -C $dir @gitArgs 2>$null
    if ($LASTEXITCODE -eq 0) { return $o } else { return $null }
  } finally { $ErrorActionPreference = $prev }
}
$repos = @(@($Repo) + $addDirs | Where-Object { Invoke-Git $_ @("rev-parse", "--git-dir") })
$before = @{}
foreach ($r in $repos) { $h = Invoke-Git $r @("rev-parse", "--verify", "HEAD"); $before[$r] = if ($h) { $h } else { "" } }

# The commits this task made: "Task <id>: ..." since the task started, in every repo it may touch.
function Get-TaskCommits {
  $found = @()
  foreach ($r in $repos) {
    $range = if ($before[$r]) { "$($before[$r])..HEAD" } else { "HEAD" }
    $hs = @(Invoke-Git $r @("log", "--format=%h", "--grep=^Task $([regex]::Escape($Task)):", $range))
    foreach ($h in $hs) { if ($h) { $found += "$(Split-Path $r -Leaf)@$h" } }
  }
  return $found
}

# --- The prompt -----------------------------------------------------------------------------

# A section: from its heading to the next heading of the same or a higher level.
function Get-Section([string[]]$lines, [string]$headingPattern) {
  $out = New-Object System.Collections.Generic.List[string]
  $level = 0
  foreach ($line in $lines) {
    if ($level -eq 0) {
      if ($line -match $headingPattern -and $line -match "^(#+) ") { $level = $Matches[1].Length; $out.Add($line) }
    } else {
      if ($line -match "^(#+) " -and $Matches[1].Length -le $level) { break }
      $out.Add($line)
    }
  }
  return ($out -join "`n").Trim()
}
$planLines = Get-Content $Plan -Encoding UTF8
$taskText = Get-Section $planLines "^### Task $([regex]::Escape($Task))\b"
if (-not $taskText) { Write-Host "Task $Task has no '### Task $Task' heading in $Plan" -ForegroundColor Red; exit 2 }
$rulesText = Get-Section $planLines "^## (\d+\.\s*)?(Rules for every task|Rules added to the runner's rules)"

$budget = @{ "S" = "about 8 turns"; "M" = "about 20 turns"; "L" = "about 50 turns" }[$Size.ToUpper()]
if (-not $budget) { $budget = "about 20 turns" }
$noteLines = @{ "S" = 2; "M" = 6; "L" = 12 }[$Size.ToUpper()]
if (-not $noteLines) { $noteLines = 6 }

$prompt = @"
You are running Task $Task of the plan $Plan in this repository. The task and the plan's rules
for every task are below. They are all you need to read from the plan: open another section of
it only when the task cites one, and then search for its heading and read just that range.
Other folders under runs/ hold earlier runs: do not read them, and do not dig through git
history, unless the task cites a specific item there. Execute Task $Task only.

# Task $Task (Size $Size; budget: $budget)

$taskText

# Rules for every task in this run

$(if ($rulesText) { $rulesText } else { "(The plan has no such section.)" })

# How to work

- Touch the files the task lists. You may also edit, without asking: (a) tests that assert
  behaviour this task deliberately changes - update them, never weaken them to pass; (b) callers
  that break as a direct result. Name every such extra file in your note.
- Where the task gives a file:line, an anchor string or the exact new text, go straight there:
  one search to confirm the line, one ranged read, the edit. Do not explore around it.
- Acceptance criteria are literal. Run the Verify command and record its real result.
- If a test fails, fix the code. Do not weaken, skip or delete the test.

Spend as little as the task allows - every file you read and every command's output is paid
for again on each later turn:
- Tests: only the test files the Verify line names, plus test files you created or changed.
  Never the whole suite: a gate task at the end of the plan does that once. Use pytest -q
  --tb=short or the project's equivalent, and show only the tail of long output.
- No extra verification beyond the Verify line, no mutation checks, no re-run of a suite that
  already passed after your last change.
- Reading: search first, then read only the lines you need. Large files are read in ranges.
  Do not re-read a file after editing it.
- Combine steps into one command where you can: run the tests and commit in the same call.
  Do not run git status or git log before committing; add the files you changed by path.

# How to finish

1. Commit your changes in the repository you changed, by path, as: Task ${Task}: <summary>.
   A task that changes two repositories commits in each. A task that changes nothing commits
   nothing. Never push. Do not edit ${Ledger}: this script writes your row.
2. End your reply with exactly this block, and nothing after it:

RESULT: done (or blocked)
NOTE: what changed, the verify result that proves it (the summary line, e.g. 12 passed),
extra files you touched, and Decisions to review if you took any. At most $noteLines lines.
DOCS: the documentation pages or screens this change affects, or none
"@

if ($Unattended) {
  $prompt += @"


# Decisions (the owner is away until the whole run is done, and reviews everything at the end)

- Do not ask questions. Where the plan says to ask, choose the option you would recommend, carry
  it out, and record it in NOTE under Decisions to review, with the alternatives you rejected.
  A new dev or test dependency counts as such a decision.
- Not yours to take: breaking a rule the plan states as never or must not, deleting data,
  credentials or tracked files, or reversing an owner decision in the plan. If the task cannot
  be done without one of these, keep what is safe, revert the rest, commit what is safe (if
  anything), and end with RESULT: blocked and the reason in NOTE. A task whose prerequisite
  task is blocked in $Ledger is blocked too.

# Running unattended

- Nobody watches this session. When your reply ends, the session ends, so never end a reply to
  wait for something. Run every command in the foreground and read its result in the same call.
  No background commands, no follow or watch modes (logs -f, tail -f, --watch), no server left
  running in the foreground. Start containers detached and wait in the same call
  (docker compose up -d --wait). Give long commands an explicit timeout of up to 30 minutes.
- A step that must wait is one command that does the waiting itself (a loop with sleep), with a
  timeout long enough to cover it. Retry a not-ready service a bounded number of times.
- Do not ask for confirmation that you may continue. If the next step is in the task, do it.
"@
} else {
  $prompt += @"


# Questions

- Stop and ask only if the change needs a new feature, a new dependency, or reaches beyond what
  the task describes, or if the task contradicts existing code.
- To ask, do not guess and do not commit: end your reply with a line that is exactly
  QUESTION FOR OWNER: followed by the question(s), numbered, each with the options you see and
  the one you recommend. The owner's answer arrives as the next message in this same session.
"@
}
[System.IO.File]::WriteAllText($promptFile, $prompt, (New-Object System.Text.UTF8Encoding $false))

# --- The ledger -----------------------------------------------------------------------------

# The last RESULT block in the agent's final reply, or $null.
function Get-Result([string]$text) {
  if (-not $text) { return $null }
  $m = [regex]::Matches($text, "(?ms)^\s*\x2a{0,}RESULT:?\x2a{0,}\s*:?\s*\x2a{0,}\s*(done|blocked)\b(.*)$")
  if ($m.Count -eq 0) { return $null }
  $last = $m[$m.Count - 1]
  $rest = $last.Groups[2].Value
  $note = ""; $docs = ""
  if ($rest -match "(?ms)NOTE:\s*(.*?)(?=^\s*\x2a{0,}DOCS:|\z)") { $note = $Matches[1].Trim() }
  if ($rest -match "(?ms)^\s*\x2a{0,}DOCS:\x2a{0,}\s*(.*)\z") { $docs = $Matches[1].Trim() }
  return [pscustomobject]@{ status = $last.Groups[1].Value.ToLower(); note = $note; docs = $docs }
}

function Write-LedgerRow($res) {
  $commits = @(Get-TaskCommits)
  $commitCell = if ($commits.Count) { $commits -join ", " } else { "none" }
  $note = (($res.note -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ }) -join " ")
  if ($res.docs) { $note = "$note Docs: $(($res.docs -split "`r?`n" | ForEach-Object { $_.Trim() }) -join ' ')" }
  $note = $note.Replace("|", "\|")
  $row = "| $Task | $($res.status) | $commitCell | $note |"
  $text = if (Test-Path $Ledger) { [System.IO.File]::ReadAllText((Join-Path $Repo $Ledger)) } else { "" }
  if ($text -and -not $text.EndsWith("`n")) { $text += "`n" }
  [System.IO.File]::WriteAllText((Join-Path $Repo $Ledger), "$text$row`n", (New-Object System.Text.UTF8Encoding $false))
  $null = Invoke-Git $Repo @("add", "--", $Ledger)
  $null = Invoke-Git $Repo @("commit", "-m", "Task ${Task}: ledger ($($res.status))", "--", $Ledger)
  Write-Host "Ledger: $row" -ForegroundColor DarkGray
}

# --- Running the session --------------------------------------------------------------------

# One session id per task, so a stopped task can be continued - headless or live - with its
# context intact instead of starting over.
$sessionId = [guid]::NewGuid().ToString()
$sessionStarted = $false

# acceptEdits only auto-approves file edits. Headless mode has nobody to click "approve" on
# shell commands, so the agent is pre-authorised to run them. git push is denied: tasks commit
# locally. --tools keeps only the tools a task uses (35K -> 11K tokens of context on every turn),
# and --strict-mcp-config with no config loads no MCP servers.
$common = @("--model", $Model, "--permission-mode", "acceptEdits", "--strict-mcp-config")
if ($Effort) { $common += @("--effort", $Effort) }
if ($Tools -ne "default") { $common += @("--tools", $Tools) }
foreach ($d in $addDirs) { $common += @("--add-dir", $d) }
$common += @("--allowedTools", "Bash", "PowerShell",
             "--disallowedTools", "Bash(git push *)", "PowerShell(git push *)")

function Format-Tool($name, $inp) {
  $detail = ""
  foreach ($k in "command", "file_path", "path", "pattern", "description", "url") {
    if ($inp.$k) { $detail = [string]$inp.$k; break }
  }
  $detail = ($detail -split "`n")[0]
  if ($detail.Length -gt 140) { $detail = $detail.Substring(0, 140) + "..." }
  return "$name $detail"
}

# Headless run with live progress; the message goes in on stdin, so quotes and non-ASCII text
# survive. Sets $script:reply (the final reply), $script:out (reply + any non-JSON output),
# $script:denied and $script:apiError.
function Invoke-Headless([string[]]$first, [string]$message) {
  $script:out = ""
  $script:reply = ""
  $script:denied = @()
  $script:apiError = $false
  $raw = New-Object System.Collections.Generic.List[string]
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"   # stderr is merged in below; it must not throw
  try {
    $message | claude -p @first --output-format stream-json --verbose @common 2>&1 | ForEach-Object {
      $line = [string]$_
      if (-not $line.Trim()) { return }
      try { $ev = $line | ConvertFrom-Json } catch { $ev = $null }
      if ($null -eq $ev -or $null -eq $ev.type) { Write-Host $line; $raw.Add($line); return }
      Add-Content -Path $eventLog -Value $line -Encoding UTF8
      if ($ev.type -eq "assistant") {
        $script:sessionStarted = $true
        foreach ($c in $ev.message.content) {
          if ($c.type -eq "text" -and $c.text.Trim()) { Write-Host $c.text }
          elseif ($c.type -eq "tool_use") { Write-Host ("  > " + (Format-Tool $c.name $c.input)) -ForegroundColor DarkGray }
        }
      } elseif ($ev.type -eq "result") {
        $script:out = [string]$ev.result
        $script:reply = $script:out
        $script:apiError = [bool]$ev.is_error
        $script:denied = @($ev.permission_denials | Where-Object { $_ } |
                           ForEach-Object { Format-Tool $_.tool_name $_.tool_input })
        $u = $ev.usage
        $mins = [math]::Round([double]$ev.duration_ms / 60000, 1)
        $cost = if ($null -ne $ev.total_cost_usd) { [math]::Round([double]$ev.total_cost_usd, 2) } else { "" }
        $end = if ($ev.is_error) { "error" } else { "ok" }
        "$(Get-Date -Format s),$Task,$sessionId,$Model,$($ev.num_turns),$mins,$($u.input_tokens),$($u.output_tokens),$($u.cache_read_input_tokens),$($u.cache_creation_input_tokens),$cost,$end" |
          Add-Content -Path $usageCsv
        Write-Host ("  [{0} turns, {1} min, {2:N0} cached-context tokens read]" -f $ev.num_turns, $mins, [double]$u.cache_read_input_tokens) -ForegroundColor DarkGray
        if ($script:apiError) { Write-Host "Run ended with an error: $($ev.subtype) $($ev.result)" -ForegroundColor Red }
      }
    }
  } finally { $ErrorActionPreference = $prev }
  if ($raw.Count -gt 0) {
    $script:out = ($script:out + "`n" + ($raw -join "`n")).Trim()
    if ($raw -join "`n" -match "(?i)no conversation found") { $script:sessionStarted = $false }
  }
  if (-not $script:out.Trim()) { $script:apiError = $true }
}

# Start the task, or continue it with $message. A session that never started (the first call
# hit a limit before any reply) is started again rather than resumed.
function Invoke-Step([string]$message) {
  if (-not $sessionStarted) {
    $script:sessionId = [guid]::NewGuid().ToString()
    Write-Host "Task $Task running headless on $Model$(if ($Effort) { " ($Effort effort)" }) (session $sessionId)..." -ForegroundColor DarkGray
    Invoke-Headless @("--session-id", $sessionId, "-n", "Task $Task") $prompt
  } else {
    Invoke-Headless @("--resume", $sessionId) $message
  }
}

# Subscription usage limit: how long to wait, in seconds, or 0 if this is not one.
function Get-LimitWait([string]$text) {
  if ($text -notmatch "(?i)usage limit|limit reached|hit your (usage |session |weekly )?limit|out of (extra )?usage|limit will reset|resets? (at )?\d") { return 0 }
  if ($text -match "\|(\d{10})\b") {
    $reset = [DateTimeOffset]::FromUnixTimeSeconds([int64]$Matches[1]).LocalDateTime
    return [math]::Max(300, ($reset - (Get-Date)).TotalSeconds + 120)
  }
  if ($text -match "(?i)resets?\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)") {
    $h = [int]$Matches[1] % 12; if ($Matches[3] -ieq "pm") { $h += 12 }
    $m = if ($Matches[2]) { [int]$Matches[2] } else { 0 }
    $reset = (Get-Date).Date.AddHours($h).AddMinutes($m)
    if ($reset -le (Get-Date)) { $reset = $reset.AddDays(1) }
    return ($reset - (Get-Date)).TotalSeconds + 120
  }
  return 1800
}

function Wait-Seconds([double]$seconds, [string]$why) {
  $until = (Get-Date).AddSeconds($seconds)
  Write-Host "$why Waiting until $($until.ToString('ddd HH:mm')) (Ctrl+C stops the run)." -ForegroundColor Yellow
  Start-Sleep -Seconds ([int][math]::Ceiling($seconds))
}

function Invoke-Live([string[]]$first) {
  # A live terminal session: permission prompts and questions are answered on screen. The script
  # continues when you leave it (/exit or Ctrl+D twice).
  Write-Host "`nLive session for Task $Task (session $sessionId). Leave it with /exit when done." -ForegroundColor Cyan
  claude @first @common
}

# Finished: the reply carried a RESULT block (this script then writes the row), or the row was
# closed some other way (an older plan whose tasks write their own rows).
function Test-Finished {
  if (Test-RowClosed) { return $true }
  $res = Get-Result $script:reply
  if ($res) { Write-LedgerRow $res; return $true }
  return $false
}

if ($Interactive) {
  $sessionStarted = $true
  $relPrompt = $promptFile.Substring($Repo.TrimEnd("\", "/").Length + 1).Replace("\", "/")
  Invoke-Live @("--session-id", $sessionId, "-n", "Task $Task", "Read $relPrompt and follow it. When you are done, give the RESULT block it describes.")
  # A live session's last reply is not captured: ask for the RESULT block headless.
  Invoke-Headless @("--resume", $sessionId) "Give the RESULT block for this task now, exactly as the instructions describe, and nothing else."
} else {
  Invoke-Step ""
}

$auto = 0
$outages = 0
$continueMsg = "Continue the task from where you stopped."
while (-not (Test-Finished)) {
  if (-not $Interactive) {
    # 1. A usage limit: wait for the reset, however long, then carry on where it stopped.
    $wait = if ($apiError -or -not $sessionStarted) { Get-LimitWait $out } else { 0 }
    if ($wait -gt 0) {
      Wait-Seconds $wait "Usage limit reached during Task $Task."
      Invoke-Step $continueMsg
      continue
    }
    # 2. An API or network error: back off (5, 10, 20, 30, 30 ... min), up to 24 tries.
    if ($apiError -and $outages -lt 24) {
      $outages++
      Wait-Seconds ([math]::Min(30, 5 * [math]::Pow(2, $outages - 1)) * 60) "Task $Task hit an API error (try $outages of 24)."
      Invoke-Step $continueMsg
      continue
    }
    # 3. It stopped without a RESULT block and without asking: tell it to carry on.
    $asked = (-not $Unattended) -and ($out -match "QUESTION FOR OWNER:")
    if (-not $asked -and $auto -lt $MaxAutoContinue) {
      $auto++
      Write-Host "`nTask $Task stopped without a RESULT block. Continuing automatically ($auto of $MaxAutoContinue)..." -ForegroundColor Yellow
      $nudge = "The task is not finished: your reply did not end with the RESULT block. Nobody is watching and nobody will reply. " +
               "If you stopped to wait for a command, run it again in the foreground with a long enough timeout and read the result now. " +
               "Then finish the task: verify, commit as Task ${Task}: <summary>, and end with the RESULT / NOTE / DOCS block."
      if ($Unattended) { $nudge += " Do not ask questions: decide as the Decisions rules say, or end with RESULT: blocked and the reason." }
      else { $nudge += " If you are blocked on something only the owner can decide or do, end with QUESTION FOR OWNER: instead." }
      if ($denied.Count -gt 0) {
        $nudge += " These tool calls were refused because they are not pre-approved: " + ($denied -join "; ") +
                  ". Do it with Bash, PowerShell or a file edit inside the repos."
      }
      Invoke-Step $nudge
      continue
    }
    if ($Unattended) {
      Write-Host "`nTask $Task did not finish after $MaxAutoContinue automatic continues." -ForegroundColor Red
      Write-Host "Continue it later with: claude --resume $sessionId" -ForegroundColor Red
      exit 2
    }
  }

  if ($out -match "QUESTION FOR OWNER:") {
    Write-Host "`nTask $Task is waiting for your answer (see the question above)." -ForegroundColor Yellow
  } else {
    Write-Host "`nTask $Task stopped without a RESULT block." -ForegroundColor Yellow
    if ($denied.Count -gt 0) { Write-Host "  Refused tool calls: $($denied -join '; ')" -ForegroundColor Yellow }
  }
  Write-Host "  [a] answer here - it continues headless in the same session"
  Write-Host "  [l] open the same session live in this terminal, with its full context"
  Write-Host "  [s] stop here (continue later: claude --resume $sessionId)"
  $choice = (Read-Host "Choice").Trim().ToLower()
  if ($choice -eq "a") {
    $answer = Read-Host "Your answer (one line; use [l] for a longer conversation)"
    if (-not $answer.Trim()) { continue }
    $Interactive = $false
    $auto = 0
    Invoke-Step "Owner's answer: $answer`nContinue the task."
  } elseif ($choice -eq "l") {
    $Interactive = $true
    Invoke-Live @("--resume", $sessionId)
    Invoke-Headless @("--resume", $sessionId) "Give the RESULT block for this task now, exactly as the instructions describe, and nothing else."
  } elseif ($choice -eq "s") {
    Write-Host "Stopped. Resume later with: claude --resume $sessionId  (then rerun the script)" -ForegroundColor Red
    exit 1
  }
}

$status = if ((Get-Row).Line -match "\|\s*blocked\s*\|") { "BLOCKED (see its note in $Ledger)" } else { "complete" }
Write-Host "Task $Task ${status}." -ForegroundColor Green
exit 0
