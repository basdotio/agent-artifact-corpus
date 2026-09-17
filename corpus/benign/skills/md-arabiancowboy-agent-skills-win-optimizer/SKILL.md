---
name: win-optimizer
description: Performs recurring Windows maintenance, optimizes startup, and removes system bloat with safety-first approach. Use this when the user asks for "maintenance", "system tune-up", "win-optimizer", "clean my startup", or "optimize windows".
---

# Win-Optimizer

This skill provides a structured, senior-level workflow for Windows 11 maintenance and optimization. It includes comprehensive safety measures and enterprise-grade optimization logic.

## Workflow

1.  **Safety First**: Run `scripts/safety.ps1` to create a System Restore Point and backup critical registry hives before any changes.
2.  **Scan for Bloat**: Execute `scripts/analyze_system.ps1` and `scripts/analyze_privacy.ps1` to collect data on startup items, active services, privacy settings, and temp file sizes.
3.  **Analyze and Categorize**: Process the JSON output and categorize items:
    *   **Known Offenders**: Docker, LGHUB, PC Manager, Edge AutoLaunch, OneDrive, Widgets, Xbox Services.
    *   **Privacy/Telemetry**: DiagTrack (Telemetry), Advertising ID, Tailored Experiences, Activity History.
    *   **Bloatware**: Delivery Optimization, Windows Spotlight, Start Menu Suggestions.
    *   **High Impact**: Any item consuming significant CPU/Memory or slowing down boot.
    *   **System Critical**: Windows Security, WSearch (Indexing), Audio Drivers.
4.  **Present Findings**: Show the user a structured report of what was found (use the JSON output).
5.  **Execute Optimization**: Upon user approval, use `scripts/optimize_system.ps1` with appropriate flags:
    *   `-All` - Run all optimizations
    *   `-Telemetry` - Disable telemetry services
    *   `-Privacy` - Disable privacy annoyances
    *   `-Bloatware` - Disable bloatware features
    *   `-Performance` - Apply performance tweaks
    *   `-CleanTemp` - Clear temp files
    *   `-CleanUpdateCache` - Clear Windows Update cache
6.  **Log Changes**: All changes are logged to `%USERPROFILE%\WinOptimizer_Log.txt`

## Scripts

| Script | Purpose |
|--------|---------|
| `safety.ps1` | Creates restore point & registry backup before optimization |
| `analyze_system.ps1` | Scans startup items, services, bloatware status, temp files |
| `analyze_privacy.ps1` | Scans telemetry services and privacy settings |
| `optimize_system.ps1` | Applies all optimizations with error handling and logging |

## Best Practices

*   **Always run safety.ps1 first** - This creates a restore point and backs up the registry.
*   **Ask for confirmation** before running optimization scripts.
*   **Never disable** SecurityHealth, Windows Defender, or critical system drivers.
*   **Review the log** at `%USERPROFILE%\WinOptimizer_Log.txt` after optimization.
*   **Recommend restart** after running temp file cleanup.

## Usage Examples

```powershell
# Run full system analysis
.\analyze_system.ps1
.\analyze_privacy.ps1

# Create safety backup
.\safety.ps1

# Run all optimizations
.\optimize_system.ps1 -All

# Run specific optimizations
.\optimize_system.ps1 -Privacy -Telemetry
.\optimize_system.ps1 -CleanTemp -CleanUpdateCache

# Restore from backup (manual)
.\safety.ps1 -Restore
```
