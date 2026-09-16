param(
    [string]$Version,
    [string]$FromTag,
    [string]$ChangelogPath = "docs/CHANGELOG.md",
    [switch]$Apply,
    [switch]$IncludeMerges,
    [string]$OutputPath,
    [switch]$NoConsolidation,
    [switch]$IncludeHashes
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Require-GitRepository {
    $repoRoot = git rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($repoRoot)) {
        throw "Not inside a git repository."
    }

    return $repoRoot.Trim()
}

function Resolve-Version([string]$RepoRoot, [string]$RequestedVersion) {
    if (-not [string]::IsNullOrWhiteSpace($RequestedVersion)) {
        if ($RequestedVersion -notmatch '^\d+\.\d+\.\d+$') {
            throw "Version '$RequestedVersion' is invalid. Expected X.Y.Z."
        }

        return $RequestedVersion
    }

    $propsPath = Join-Path $RepoRoot "Directory.Build.props"
    if (-not (Test-Path $propsPath)) {
        throw "Directory.Build.props not found at repository root."
    }

    $match = Select-String -Path $propsPath -Pattern '<Version>\s*(?<v>\d+\.\d+\.\d+)\s*</Version>' | Select-Object -First 1
    if ($null -eq $match) {
        throw "Could not resolve <Version> from Directory.Build.props."
    }

    return $match.Matches[0].Groups["v"].Value
}

function Resolve-FromTag([string]$RequestedTag) {
    if (-not [string]::IsNullOrWhiteSpace($RequestedTag)) {
        return $RequestedTag
    }

    $tag = git describe --tags --abbrev=0 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($tag)) {
        return $null
    }

    return $tag.Trim()
}

function Resolve-GitHubRepositoryUrl {
    $remote = git remote get-url origin 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($remote)) {
        return "https://github.com/ShareX/XerahS"
    }

    $remote = $remote.Trim()
    if ($remote -match '^git@github\.com:(?<repo>[^/]+/[^/]+?)(\.git)?$') {
        return "https://github.com/$($Matches["repo"])"
    }

    if ($remote -match '^https://github\.com/(?<repo>[^/]+/[^/]+?)(\.git)?$') {
        return "https://github.com/$($Matches["repo"])"
    }

    return "https://github.com/ShareX/XerahS"
}

function Resolve-TagUrl([string]$Version) {
    $repoUrl = Resolve-GitHubRepositoryUrl
    return "$repoUrl/releases/tag/v$Version"
}

function Test-ReleaseTagExists([string]$Version) {
    $tagName = "v$Version"

    git show-ref --verify --quiet "refs/tags/$tagName"
    if ($LASTEXITCODE -eq 0) {
        return $true
    }

    git ls-remote --exit-code --tags origin "refs/tags/$tagName" *> $null
    return $LASTEXITCODE -eq 0
}

function Resolve-VersionHeading([string]$Version) {
    if (Test-ReleaseTagExists -Version $Version) {
        $tagUrl = Resolve-TagUrl -Version $Version
        return "## [v$Version]($tagUrl)"
    }

    return "## v$Version"
}

function Normalize-ChangelogText([string]$Text) {
    $arrowBad = [string][char]0x00E2 + [char]0x2020 + [char]0x2019
    $emDashBad = [string][char]0x00E2 + [char]0x20AC + [char]0x201D
    $enDashBad = [string][char]0x00E2 + [char]0x20AC + [char]0x201C
    $sectionBad = [string][char]0x00C2 + [char]0x00A7

    $Text = $Text.Replace($arrowBad, [string][char]0x2192)
    $Text = $Text.Replace($emDashBad, [string][char]0x2014)
    $Text = $Text.Replace($enDashBad, [string][char]0x2013)
    $Text = $Text.Replace($sectionBad, [string][char]0x00A7)
    $Text = $Text -replace "\r?\n", "`n"
    $Text = $Text -replace "`n{3,}", "`n`n"
    return $Text -replace "`n", "`r`n"
}

function Normalize-Component([string]$RawComponent) {
    $component = $RawComponent.Trim()
    if ([string]::IsNullOrWhiteSpace($component)) {
        return "Core"
    }

    $component = $component -replace '[_-]+', ' '
    $component = $component -replace '\s+', ' '
    $words = $component.Split(' ')
    for ($i = 0; $i -lt $words.Length; $i++) {
        if ($words[$i].Length -gt 0) {
            $words[$i] = $words[$i].Substring(0, 1).ToUpperInvariant() + $words[$i].Substring(1)
        }
    }

    return ($words -join ' ')
}

function Categorize-Commit([string]$Subject) {
    $versionedMatch = [regex]::Match($Subject, '^\[v\d+\.\d+\.\d+\]\s+\[(?<type>[^\]]+)\]\s+(?<desc>.+)$')
    if ($versionedMatch.Success) {
        $type = $versionedMatch.Groups["type"].Value.Trim().ToLowerInvariant()
        $desc = $versionedMatch.Groups["desc"].Value.Trim()
        $component = "Core"

        $descPrefixMatch = [regex]::Match($desc, '^(?<component>[A-Za-z0-9\/ .&+\-]+):\s*(?<rest>.+)$')
        if ($descPrefixMatch.Success) {
            $component = Normalize-Component $descPrefixMatch.Groups["component"].Value
            $desc = $descPrefixMatch.Groups["rest"].Value.Trim()
        }

        return @{
            Category = switch ($type) {
                "feat" { "Features"; break }
                "feature" { "Features"; break }
                "fix" { "Fixes"; break }
                "refactor" { "Refactor"; break }
                "build" { "Build"; break }
                "ci" { "Build"; break }
                "chore" { "Build"; break }
                "infra" { "Build"; break }
                "infrastructure" { "Build"; break }
                "docs" { "Documentation"; break }
                "doc" { "Documentation"; break }
                "test" { "Testing"; break }
                "testing" { "Testing"; break }
                "perf" { "Performance"; break }
                "performance" { "Performance"; break }
                default { "Changed" }
            }
            Component = $component
            Description = $desc
        }
    }

    $conventionalMatch = [regex]::Match($Subject, '^(?<type>[a-zA-Z]+)(\((?<scope>[^)]+)\))?(!)?:\s*(?<desc>.+)$')
    if ($conventionalMatch.Success) {
        $type = $conventionalMatch.Groups["type"].Value.ToLowerInvariant()
        $scope = $conventionalMatch.Groups["scope"].Value
        $desc = $conventionalMatch.Groups["desc"].Value.Trim()

        return @{
            Category = switch ($type) {
                "feat" { "Features"; break }
                "feature" { "Features"; break }
                "fix" { "Fixes"; break }
                "refactor" { "Refactor"; break }
                "build" { "Build"; break }
                "ci" { "Build"; break }
                "chore" { "Build"; break }
                "docs" { "Documentation"; break }
                "doc" { "Documentation"; break }
                "test" { "Testing"; break }
                "tests" { "Testing"; break }
                "perf" { "Performance"; break }
                "performance" { "Performance"; break }
                default { "Changed" }
            }
            Component = if ([string]::IsNullOrWhiteSpace($scope)) { "Core" } else { Normalize-Component $scope }
            Description = $desc
        }
    }

    $prefixMatch = [regex]::Match($Subject, '^(?<component>[A-Za-z0-9\/ .&+\-]+):\s*(?<desc>.+)$')
    if ($prefixMatch.Success) {
        $component = Normalize-Component $prefixMatch.Groups["component"].Value
        $desc = $prefixMatch.Groups["desc"].Value.Trim()
        return @{
            Category = "Changed"
            Component = $component
            Description = $desc
        }
    }

    return @{
        Category = "Changed"
        Component = "Core"
        Description = $Subject.Trim()
    }
}

function Test-SkipChangelogCommit([string]$Subject) {
    if ($Subject -match '(?i)^\[v\d+\.\d+\.\d+\]\s+\[CI\]\s+Release\s+v\d+\.\d+\.\d+$') {
        return $true
    }

    # Agent workflow meta — not user-facing release notes.
    if ($Subject -match '(?i)hourly[_ ]review|hourly sweep|review tracker|review_state|next_candidates|derive-goal-from-session|Finalize hourly review tracker|sync tracker from prior|queue \d+ clawpatch|correct xerahs sweep test totals|log 20\d{2}-\d{2}-\d{2} \d{2}:\d{2} AWST') {
        return $true
    }

    if ($Subject -match '(?i)^(Record|record|Append|update hourly review|Update hourly review|update hourly_review|Hourly sweep tracker)') {
        return $true
    }

    if ($Subject -match '(?i)\b(Record|record|Append)\b.*\b(tracker|state|sweep|review)\b') {
        return $true
    }

    if ($Subject -match '(?i)Require XIP batch push|editor save overwrite sweep|editor sidecar save review') {
        return $true
    }

    # Version-only churn between prerelease bumps.
    if ($Subject -match '(?i)^(\[v[\d.]+\]\s+\[[^\]]+\]\s+)?(Bump version|Bump app version|Start minor release for)') {
        return $true
    }

    return $false
}

function Get-PlatformXipLabel([string]$Subject) {
    if ($Subject -notmatch '(?i)XIP(\d{4})') {
        return $null
    }

    $xipNum = $Matches[1]
    $xip = "XIP$xipNum"
    $priority = if ($Subject -match '(?i)\bP(\d+)\b') { " P$($Matches[1])" } else { '' }

    $platform = switch -Regex ($Subject) {
        '(?i)macOS|MacOS|Carbon|ScreenCaptureKit|Info\.plist|codesign|notarize|CGWindowList|sck_capture' { 'macOS'; break }
        '(?i)Linux|Wayland|wl-copy|xclip|portal|notify-send|rpm|\.deb' { 'Linux'; break }
        default {
            switch ($xipNum) {
                '0078' { 'macOS' }
                '0079' { 'Linux' }
                default { $null }
            }
        }
    }

    if ($null -eq $platform) {
        return $null
    }

    $topic = switch -Regex ($Subject) {
        '(?i)hotkey' { 'Hotkeys'; break }
        '(?i)notification|notify-send' { 'Notifications'; break }
        '(?i)clipboard|wl-copy|xclip' { 'Clipboard'; break }
        '(?i)monitor|mixed-DPI|DPI|normalizer' { 'Mixed-DPI'; break }
        '(?i)Info\.plist|bundle' { 'App bundle'; break }
        '(?i)permission|Screen Recording' { 'Permissions'; break }
        '(?i)window|CGWindowList|sck_capture' { 'Window capture'; break }
        '(?i)ScreenCaptureKit' { 'ScreenCaptureKit'; break }
        '(?i)codesign|notarize|DMG|package-mac' { 'Packaging'; break }
        '(?i)INSTALL|KNOWN_ISSUES|documentation|docs' { 'Documentation'; break }
        default { 'Platform' }
    }

    return "$platform — $topic ($xip$priority)"
}

function Get-ConsolidationBucket {
    param(
        [string]$Subject,
        [string]$Category,
        [string]$Component
    )

    if ($Subject -match '(?i)(pipe-drain|pipe-fill|stderr).*(deadlock|timeout)') {
        $platform = if ($Subject -match '(?i)Linux|Wayland|wl-|xclip|grim|slurp|gsettings|xdotool|xrandr|PulseAudio') { 'Linux' }
                    elseif ($Subject -match '(?i)macOS|MacOS|osascript|pbpaste|pbcopy') { 'macOS' }
                    else { $Component }
        return @{
            GroupKey = "$Category|$platform|__consolidate_pipe_drain__"
            Summary  = "$platform service helpers: drain stderr and bound subprocess waits to prevent pipe-fill deadlocks"
            ComponentOverride = $platform
        }
    }

    $xipLabel = Get-PlatformXipLabel -Subject $Subject
    if ($null -ne $xipLabel) {
        $cleanDesc = $Subject -replace '^\[v\d+\.\d+\.\d+\]\s+\[[^\]]+\]\s+', ''
        $cleanDesc = $cleanDesc -replace '(?i)^XIP\d{4}\s+P\d+:\s*', ''
        return @{
            GroupKey = "$Category|$xipLabel|__xip_platform__"
            Summary  = $cleanDesc.Trim()
            ComponentOverride = $xipLabel
        }
    }

    if ($Subject -match '(?i)ShareX\.ImageEditor|Update ImageEditor to ShareX@') {
        return @{
            GroupKey = "$Category|$Component|__consolidate_sharex_imageeditor__"
            Summary  = "ShareX.ImageEditor submodule updates"
        }
    }

    if ($Category -eq 'Documentation') {
        if ($Subject -match '(?i)(Add|Update|Refresh)\s+20\d{2}-\d{2}-\d{2}.*blog') {
            return @{
                GroupKey = "Documentation|__blog_series__|__consolidate_blog_drafts__"
                Summary  = "Blog drafts (2026 series)"
            }
        }
        if ($Subject -match '(?i)RELIABILITY-PLAN') {
            return @{
                GroupKey = "Documentation|__reliability_plan__|__consolidate_reliability_plan__"
                Summary  = "Reliability upgrade plan (observed state, failure modes, U1-U10 upgrades, simulations, sign-off)"
            }
        }
        if ($Subject -match '(?i)(Linux|MacOS) Improvement Plan|KNOWN_ISSUES.*macOS|Move improvement plans into XIP') {
            return @{
                GroupKey = "Documentation|__platform_improvement_plans__|__consolidate_platform_plans__"
                Summary  = "Linux and macOS improvement plans (XIP0077-XIP0079) and KNOWN_ISSUES updates"
            }
        }
        if ($Subject -match '(?i)\b(XIP\d+|IEIP\d+|KFIP\d+)') {
            return @{
                GroupKey = "Documentation|__xip_ieip_kfip__|__consolidate_proposal_docs__"
                Summary  = "XIP, IEIP, and KFIP proposals and related documentation"
            }
        }
        if ($Subject -match '(?i)AGENTS wrapper|CONTRIBUTING\.md') {
            return @{
                GroupKey = "Documentation|__contributor_policy__|__consolidate_contributor_docs__"
                Summary  = "Contributor workflow docs (AGENTS wrapper policy, CONTRIBUTING.md)"
            }
        }
        if ($Component -eq 'Linux') {
            return @{
                GroupKey = "Documentation|Linux|__consolidate_linux_docs__"
                Summary  = "Linux install and capture documentation"
            }
        }
    }

    if ($Category -eq 'Changed' -and $Subject -match '(?i)(Create|Update)\s+(IEIP|XIP|KFIP)\d+|(IEIP|XIP|KFIP)\d+[^\n]*\.md\b') {
        return @{
            GroupKey = "Changed|__proposal_md__|__consolidate_proposal_md__"
            Summary  = "Proposal documents (create/update)"
        }
    }

    if ($Category -eq 'Changed' -and $Subject -match '(?i)Update hourly review|hourly review tracker|hourly_review_state') {
        return $null
    }

    if (($Category -eq 'Changed' -or $Category -eq 'Features') -and $Subject -match '(?i)multipart(\s+upload)?|S3\s+multipart') {
        return @{
            GroupKey = "$Category|$Component|__consolidate_multipart__"
            Summary  = "Multipart upload support (S3, abstractions, coverage)"
        }
    }

    if ($Category -eq 'Testing' -or $Subject -match '(?i)guardrail test|Headless\.NUnit|coverlet\.collector|McpServer\.Tests') {
        return @{
            GroupKey = "Testing|Core|__consolidate_guardrail_tests__"
            Category = "Testing"
            Summary  = "Guardrail and test-coverage improvements (Headless.NUnit, McpServer.Tests, FFmpeg regression tests)"
        }
    }

    if ($Category -eq 'Fixes') {
        if ($Subject -match '(?i)openclaw|bootstrap uploader|CLI/OpenClaw|CLI plugins for agent|Bundle CLI plugins') {
            return @{
                GroupKey = "Fixes|CLI|__consolidate_openclaw_cli__"
                Summary  = "OpenClaw/CLI upload pipeline: text upload, JSON validation and diagnostics, path normalization, bootstrap uploader JSON, manifest parity, plugin bundling, macOS plugin discovery, S3 keychain credentials"
            }
        }
        if ($Subject -match '(?i)\bMCP\b|mcp history|IsHistorySearchResourceUri|ResolveHistoryBlobPath|CreateHistoryDetailsAsync|HandlePromptsGetAsync|RunTaskAsync task identity|thumbnail_resource|history blob|history/search query') {
            return @{
                GroupKey = "Fixes|MCP|__consolidate_mcp_history__"
                Summary  = "MCP history search and resources: query parsing, URI matching, thumbnail/blob paths, stale and oversized diagnostics, task identity race, error-shape alignment"
            }
        }
        if ($Subject -match '(?i)ocr.*language|onboarding.*ocr|OcrStep|OCROptions\.PreferredLanguages|ocr regional|ocr fallback|ocr selected|ocr failure status|onboarding ocr|refreshed ocr|Apply onboarding OCR') {
            return @{
                GroupKey = "Fixes|OCR|__consolidate_ocr_languages__"
                Summary  = "OCR onboarding language lifecycle: regional defaults, refresh and persistence, fallback when enumeration fails, null guards, failure message normalization"
            }
        }
        if ($Subject -match '(?i)command palette') {
            return @{
                GroupKey = "Fixes|Core|__consolidate_command_palette__"
                Summary  = "Command palette UX: keyboard selection wrap, blank-escape close, search whitespace normalization"
            }
        }
        if ($Subject -match '(?i)editor.*save|sidecar save|annotation.*Persist|HandleCopyRequested|send-to editor|editor copy|editor dirty|editor save overwrite|Fix Editor Save|Recreate embedded editor|truncate editor save') {
            return @{
                GroupKey = "Fixes|Editor|__consolidate_editor_save__"
                Summary  = "Editor save and integration: sidecar/image failure handling, dirty-state preservation, overwrite truncation, bitmap disposal, annotation persist-after-continue"
            }
        }
        if ($Subject -match '(?i)ffmpeg|CombineScreenshots|VideoThumbnailer|Kill FFmpeg') {
            return @{
                GroupKey = "Fixes|Media|__consolidate_ffmpeg__"
                Summary  = "FFmpeg and media pipeline: path escaping, cancellation, process-tree kill, CombineScreenshots guards, probe argument quoting, workflow override wiring"
            }
        }
        if ($Subject -match '(?i)FileDownloader') {
            return @{
                GroupKey = "Fixes|Core|__consolidate_filedownloader__"
                Summary  = "FileDownloader reliability: cancellation tokens, chunked encoding, early-EOF hang on Content-Length mismatch"
            }
        }
        if ($Subject -match '(?i)pipe-drain|pipe-fill|stderr.*drain|timeout-stretching|Drain stderr') {
            return @{
                GroupKey = "Fixes|Linux|__consolidate_pipe_drain__"
                Summary  = "Linux/macOS CLI subprocess reliability: stderr drain and bounded waits to prevent pipe-fill and timeout-stretching deadlocks (clipboard, theme, capture, input, audio, Wayland tools)"
            }
        }
        if ($Subject -match '(?i)WaylandCliCapture|LinuxCliToolRunner|LinuxThemeService|LinuxScreenService|LinuxInputService|PulseAudioHelper|Linux hotkey|Linux Deb Packaging|Wayland active-window') {
            return @{
                GroupKey = "Fixes|Linux|__consolidate_linux_platform__"
                Summary  = "Linux platform: Wayland/X11 capture routing, hotkey mapping (Oem102), deb packaging clipboard recommends (wl-clipboard, xclip), active-window fallbacks"
            }
        }
        if ($Subject -match '(?i)macos.*(Dock|upload file picker|front-window|update prompt|clipboard)|Hide macOS Dock|Unblock macOS update') {
            return @{
                GroupKey = "Fixes|macOS|__consolidate_macos__"
                Summary  = "macOS: tray Dock icon hidden (#252), upload file picker fallback, front-window parsing, update prompts with manual action, clipboard path whitespace"
            }
        }
        if ($Subject -match '(?i)default instance|default uploader|uploader routing|auto uploader fallback|Ignore unavailable|plugin assembly version|upload drag-drop|honor cli upload|RemoveInstance stale|GetDefaultInstance|IsDefaultInstance') {
            return @{
                GroupKey = "Fixes|Uploaders|__consolidate_uploader_defaults__"
                Summary  = "Uploader default-instance lifecycle: non-mutating checks, stale cleanup, category validation, routing conflicts, auto fallback within category, drag-drop normalization"
            }
        }
        if ($Subject -match '(?i)BackupFile|settings backup|SettingsBackupFailed|restore settings|await async settings|BackupFileWeekly|BackupFileZip|FileHelpers.*Backup|weekly backup|settings from backup|Prune old settings backup|Prune empty plugin') {
            return @{
                GroupKey = "Fixes|Settings|__consolidate_settings_backup__"
                Summary  = "Settings and backup reliability: async saves, atomic zip replacement, weekly backup TOCTOU handling, restore from backups, empty-destination guards, user-visible failure toasts"
            }
        }
        if ($Subject -match '(?i)HistoryOcrIndex|indexer enumeration|CountIndexedContents|Handle PathTooLong') {
            return @{
                GroupKey = "Fixes|History|__consolidate_history_indexer__"
                Summary  = "History and indexer: OCR index cleanup on delete, enumeration resilience for long paths and I/O errors"
            }
        }
        if ($Subject -match '(?i)toast|ToastWindow') {
            return @{
                GroupKey = "Fixes|UI|__consolidate_toast__"
                Summary  = "Toast notifications: fade opacity, multi-monitor bounds, context-menu close resume"
            }
        }
        if ($Subject -match '(?i)ScrollingCapture') {
            return @{
                GroupKey = "Fixes|Capture|__consolidate_scrolling_capture__"
                Summary  = "Scrolling capture: ReferenceEquals guard when closing old capture window"
            }
        }
        if ($Subject -match '(?i)mobile s3') {
            return @{
                GroupKey = "Fixes|Mobile|__consolidate_mobile_s3__"
                Summary  = "Mobile S3 configuration: file-scoped config and imports"
            }
        }
    }

    if ($Category -eq 'Build' -and $Subject -match '(?i)Avalonia|SkiaSharp|SQLite bundle') {
        return @{
            GroupKey = "Build|Core|__consolidate_dependencies__"
            Summary  = "Dependency updates: Avalonia 12.0.5, SkiaSharp 3.119.4, SQLite bundle pins"
        }
    }

    if ($Category -eq 'Build' -and $Subject -match '(?i)macOS Info\.plist|hardened-runtime') {
        return @{
            GroupKey = "Build|macOS|__consolidate_macos_packaging__"
            Summary  = "macOS Info.plist template and hardened-runtime entitlements (not yet wired into packaging)"
        }
    }

    if ($Category -eq 'Changed' -and $Subject -match '(?i)\[Docs\]|\[CI\]|Flathub verification|release workflow complete|sync-only sweep|Fedora VS Code updater|Directory\.Packages\.props') {
        return @{
            GroupKey = "Changed|Core|__consolidate_release_meta__"
            Summary  = "Release and CI maintenance: prerelease defaults, v0.22.256 workflow docs, Flathub verification, Fedora updater script, package pins"
        }
    }

    return $null
}

function Get-CommitRows([string]$FromTag, [bool]$IncludeMerges) {
    $range = if ([string]::IsNullOrWhiteSpace($FromTag)) { "HEAD" } else { "$FromTag..HEAD" }
    $logArgs = @("log", $range, "--pretty=format:%h%x1f%s%x1f%an")
    if (-not $IncludeMerges) {
        $logArgs += "--no-merges"
    }

    $raw = git @logArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to read commits from git log."
    }

    if ([string]::IsNullOrWhiteSpace($raw)) {
        return @()
    }

    $rows = @()
    $lines = $raw -split "`r?`n"
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        $parts = $line.Split([char]0x1f)
        if ($parts.Length -lt 3) {
            continue
        }

        $rows += [pscustomobject]@{
            Hash = $parts[0].Trim()
            Subject = $parts[1].Trim()
            Author = $parts[2].Trim()
        }
    }

    return $rows
}

function Merge-EntriesByComponent {
    param(
        [Parameter(Mandatory = $true)]
        [System.Collections.IEnumerable]$Entries
    )

    $merged = @{}
    foreach ($entry in $Entries) {
        $component = $entry.Component
        if (-not $merged.ContainsKey($component)) {
            $merged[$component] = [pscustomobject]@{
                Category = $entry.Category
                Component = $component
                Descriptions = New-Object System.Collections.Generic.List[string]
                Hashes = New-Object System.Collections.Generic.List[string]
            }
        }

        $desc = $entry.Description.Trim()
        if (-not [string]::IsNullOrWhiteSpace($desc) -and -not $merged[$component].Descriptions.Contains($desc)) {
            $merged[$component].Descriptions.Add($desc)
        }

        foreach ($hash in $entry.Hashes) {
            if (-not $merged[$component].Hashes.Contains($hash)) {
                $merged[$component].Hashes.Add($hash)
            }
        }
    }

    $result = @()
    foreach ($item in $merged.Values) {
        $text = if ($item.Descriptions.Count -le 1) {
            $item.Descriptions[0]
        }
        elseif ($item.Descriptions.Count -le 3) {
            ($item.Descriptions | Sort-Object) -join '; '
        }
        else {
            (($item.Descriptions | Sort-Object | Select-Object -First 2) -join '; ') + '; and related changes'
        }

        $result += [pscustomobject]@{
            Category = $item.Category
            Component = $item.Component
            Description = $text
            Hashes = $item.Hashes
        }
    }

    return $result
}

function Build-ChangelogSection([string]$Version, [object[]]$CommitRows, [bool]$ConsolidateSimilar, [bool]$EmitHashes) {
    $grouped = @{}
    foreach ($row in $CommitRows) {
        if (Test-SkipChangelogCommit -Subject $row.Subject) {
            continue
        }

        $parsed = Categorize-Commit $row.Subject
        $description = $parsed.Description
        $component = $parsed.Component
        $key = $null

        if ($ConsolidateSimilar) {
            $bucket = Get-ConsolidationBucket -Subject $row.Subject -Category $parsed.Category -Component $parsed.Component
            if ($null -ne $bucket) {
                $key = $bucket.GroupKey
                $description = $bucket.Summary
                if ($bucket.ContainsKey('ComponentOverride') -and -not [string]::IsNullOrWhiteSpace($bucket.ComponentOverride)) {
                    $component = $bucket.ComponentOverride
                }
                if ($bucket.ContainsKey('Category') -and -not [string]::IsNullOrWhiteSpace($bucket.Category)) {
                    $parsed.Category = $bucket.Category
                }
                if ($bucket.ContainsKey('Component') -and -not [string]::IsNullOrWhiteSpace($bucket.Component)) {
                    $parsed.Component = $bucket.Component
                }
            }
        }

        if ($null -eq $key) {
            $key = "{0}|{1}|{2}" -f $parsed.Category, $component, $parsed.Description
        }

        if (-not $grouped.ContainsKey($key)) {
            $grouped[$key] = [pscustomobject]@{
                Category = $parsed.Category
                Component = $component
                Description = $description
                Hashes = New-Object System.Collections.Generic.List[string]
            }
        }

        if (-not $grouped[$key].Hashes.Contains($row.Hash)) {
            $grouped[$key].Hashes.Add($row.Hash)
        }
    }

    $categoryOrder = @("Features", "Fixes", "Refactor", "Build", "Documentation", "Testing", "Performance", "Changed")
    $byCategory = @{}
    foreach ($entry in $grouped.Values) {
        if (-not $byCategory.ContainsKey($entry.Category)) {
            $byCategory[$entry.Category] = New-Object System.Collections.Generic.List[object]
        }

        $byCategory[$entry.Category].Add($entry)
    }

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add((Resolve-VersionHeading -Version $Version))
    $lines.Add("")

    foreach ($category in $categoryOrder) {
        if (-not $byCategory.ContainsKey($category)) {
            continue
        }

        $entries = @(Merge-EntriesByComponent -Entries $byCategory[$category] | Sort-Object Component, Description)
        if ($entries.Count -eq 0) {
            continue
        }

        $lines.Add("### $category")
        foreach ($entry in $entries) {
            if ($EmitHashes) {
                $hashes = ($entry.Hashes | Sort-Object) -join ", "
                $lines.Add("- **$($entry.Component)**: $($entry.Description) `($hashes`)")
            }
            else {
                $lines.Add("- **$($entry.Component)**: $($entry.Description)")
            }
        }
        $lines.Add("")
    }

    if ($lines.Count -eq 2) {
        $lines.Add("### Changed")
        $lines.Add("- No user-facing commits were detected in this range.")
        $lines.Add("")
    }

    $lines.Add("---")
    $lines.Add("")

    return ($lines -join "`n").TrimEnd() + "`n"
}

function Ensure-ChangelogPreamble([string]$Content) {
    if ($Content -match '(?ms)^#\s*Changelog\s*$') {
        return $Content
    }

    $preamble = @"
# Changelog

All notable changes to XerahS will be documented in this file.

The format follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html):

- **MAJOR** (x): Breaking changes (0 while unreleased)
- **MINOR** (y): New features and enhancements
- **PATCH** (z): Bug fixes and patches

---

"@

    return $preamble + $Content.TrimStart()
}

function Upsert-ChangelogSection([string]$Content, [string]$Version, [string]$Section) {
    $escapedVersion = [regex]::Escape($Version)
    $currentHeading = "##\s+(?:v$escapedVersion|\[v$escapedVersion\]\([^)]+\))"
    $anyVersionHeading = "##\s+(?:v\d+\.\d+\.\d+(?:\s+-[^\r\n]*)?|\[v\d+\.\d+\.\d+\]\([^)]+\)(?:\s+-[^\r\n]*)?)"
    $existingPattern = "(?ms)^$currentHeading\s*$.*?(?=^$anyVersionHeading\s*$|\z)"
    if ([regex]::IsMatch($Content, $existingPattern)) {
        return [regex]::Replace($Content, $existingPattern, $Section.TrimEnd() + "`n`n")
    }

    $unreleasedMatch = [regex]::Match($Content, '(?m)^## Unreleased\s*$')
    if ($unreleasedMatch.Success) {
        $insertIndex = $unreleasedMatch.Index + $unreleasedMatch.Length
        $insertion = "`n`n" + $Section.TrimEnd() + "`n"
        return $Content.Insert($insertIndex, $insertion)
    }

    $preambleBreak = [regex]::Match($Content, '(?m)^---\s*$')
    if ($preambleBreak.Success) {
        $insertIndex = $preambleBreak.Index + $preambleBreak.Length
        $insertion = "`n`n" + $Section.TrimEnd() + "`n"
        return $Content.Insert($insertIndex, $insertion)
    }

    return $Section.TrimEnd() + "`n`n" + $Content
}

$repoRoot = Require-GitRepository
Set-Location $repoRoot

$resolvedVersion = Resolve-Version -RepoRoot $repoRoot -RequestedVersion $Version
$resolvedFromTag = Resolve-FromTag -RequestedTag $FromTag
$commits = @(Get-CommitRows -FromTag $resolvedFromTag -IncludeMerges:$IncludeMerges)
$consolidate = -not $NoConsolidation
$section = Build-ChangelogSection -Version $resolvedVersion -CommitRows $commits -ConsolidateSimilar:$consolidate -EmitHashes:$IncludeHashes

if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
    $resolvedOutput = if ([System.IO.Path]::IsPathRooted($OutputPath)) { $OutputPath } else { Join-Path $repoRoot $OutputPath }
    $outText = Normalize-ChangelogText -Text $section
    [System.IO.File]::WriteAllText($resolvedOutput, $outText, [System.Text.UTF8Encoding]::new($false))
}

if ($Apply) {
    $resolvedChangelog = if ([System.IO.Path]::IsPathRooted($ChangelogPath)) { $ChangelogPath } else { Join-Path $repoRoot $ChangelogPath }
    if (-not (Test-Path $resolvedChangelog)) {
        throw "Changelog file not found: $resolvedChangelog"
    }

    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    $existingBytes = [System.IO.File]::ReadAllBytes($resolvedChangelog)
    if ($existingBytes.Length -ge 3 -and $existingBytes[0] -eq 0xEF -and $existingBytes[1] -eq 0xBB -and $existingBytes[2] -eq 0xBF) {
        $existingBytes = $existingBytes[3..($existingBytes.Length - 1)]
    }
    $existing = $utf8NoBom.GetString($existingBytes)
    $existing = Ensure-ChangelogPreamble -Content $existing
    $updated = Upsert-ChangelogSection -Content $existing -Version $resolvedVersion -Section $section

    $updated = Normalize-ChangelogText -Text $updated

    [System.IO.File]::WriteAllText($resolvedChangelog, $updated, $utf8NoBom)
}

Write-Host "Target version : v$resolvedVersion"
$fromTagLabel = if ([string]::IsNullOrWhiteSpace($resolvedFromTag)) { "(none)" } else { $resolvedFromTag }
Write-Host "From tag       : $fromTagLabel"
Write-Host "Commits parsed : $($commits.Count)"
Write-Host "Consolidation  : $(if ($consolidate) { 'on (similar commits merged)' } else { 'off (-NoConsolidation)' })"
Write-Host "Hash output    : $(if ($IncludeHashes) { 'on (-IncludeHashes)' } else { 'off (default)' })"
if ($Apply) {
    Write-Host "Applied to     : $ChangelogPath"
}
if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
    Write-Host "Draft output   : $OutputPath"
}
Write-Host ""
Write-Output $section
Write-Host ""
Write-Host "Rewrite pass: compress categories, merge trivial patch versions, polish platform/XIP bullets before publishing." -ForegroundColor DarkYellow
