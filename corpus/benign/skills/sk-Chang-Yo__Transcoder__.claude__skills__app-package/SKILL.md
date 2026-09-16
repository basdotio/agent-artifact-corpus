---
name: app-package
description: Windows Tauri application packaging skill. Summarizes code changes, updates documentation, commits and merges to main with tag, then creates distribution zip package.
license: MIT
metadata:
  author: Transcoder
  version: "2.0.0"
---

# App Package Skill

Packages the Transcoder Windows application for distribution.

## When to Use

Call this skill when:
- User wants to create a release build
- User wants to package the app for distribution
- User invokes `/app-package` command

## Packaging Process

### Phase 1: Pre-Build Documentation

1. **Summarize code changes**
   - Review recent commits and changes since last release
   - Present summary to user for confirmation

2. **Gather release info (single source of truth)**
   - Use `src-tauri/Cargo.toml` as the only place to set the version
   - Confirm release summary before proceeding

3. **Update documentation**
   - `README.md` - update version info from `src-tauri/Cargo.toml` if needed
   - `CHANGELOG.md` - add new release entry with changes summary
   - `docs/gh-pages/` - update documentation site if applicable
   - Ask user to confirm any uncertain information

### Phase 2: Git Operations

4. **Commit changes**
   ```bash
   git add .
   git commit -m "Release v{version}"
   ```
   Note: Never add Claude Code to co-author list

5. **Switch to main branch and merge**
   ```bash
   git checkout main
   git merge {current-branch}
   ```

6. **Create release tag**
   ```bash
   git tag v{version}
   ```

### Phase 3: Build & Package

7. **Build release binary**
   ```bash
   npm run tauri build
   ```

8. **Update dist-release folder**
   - The `dist-release/` folder already exists with `ffmpeg/` subdirectory
   - Only update these files:
     - Replace `transcoder.exe` with newly built binary from `src-tauri/target/release/`
     - Replace `README.md` if it has changed
   - The `ffmpeg/` folder and its contents remain unchanged

9. **Update files + create zip (single command)**
   - `{version}` is read from `src-tauri/Cargo.toml`
   ```powershell
   powershell -Command "$version=(Get-Content src-tauri\Cargo.toml | Select-String -Pattern '^version\s*=\s*""(.+)""' | ForEach-Object { $_.Matches[0].Groups[1].Value } | Select-Object -First 1); if (-not $version) { throw 'Version not found in src-tauri/Cargo.toml' }; Copy-Item -Force src-tauri\target\release\transcoder.exe dist-release\transcoder.exe; Copy-Item -Force README.md dist-release\README.md; Compress-Archive -Force -Path dist-release\transcoder.exe,dist-release\README.md,dist-release\ffmpeg -DestinationPath dist-release\transcoder-v$version-windows.zip"
   ```

10. **Cleanup old archives**
    - Delete old zip files (e.g., `transcoder-v0.5.1-windows.zip`)
    - Keep only the newest release

11. **Verify package**
    - Check zip file size (should be 100-200 MB range)
    - Confirm all required files are included

### Phase 4: Completion

12. **Report to user**
    - Summarize what was done
    - Show zip file size
    - Ask user if they want to push to remote:
      - Push commits: `git push origin main`
      - Push tag: `git push origin v{version}`

## Output Structure

```
dist-release/
├── transcoder.exe          (5-6 MB, from release build)
├── ffmpeg/
│   ├── ffmpeg.exe          (static, unchanged)
│   └── ffprobe.exe         (static, unchanged)
├── README.md               (may be updated)
└── transcoder-v{version}-windows.zip
```

### The uncompressed zip structure
```
dist-release/
├── transcoder.exe  
├── ffmpeg/
│   ├── ffmpeg.exe 
│   └── ffprobe.exe
└── README.md 
```

## Files Modified

- `src-tauri/Cargo.toml` - version (if changed)
- `src-tauri/tauri.conf.json` - version (if changed)
- `README.md` - documentation updates
- `CHANGELOG.md` - release notes
- `docs/gh-pages/*` - site documentation (if applicable)

## Files Created

- `dist-release/transcoder-v{version}-windows.zip` - distribution package
- `v{version}` git tag
