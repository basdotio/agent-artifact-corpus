---
name: publish
description: Publish ÆtherLight releases to npm and GitHub. Use when the user wants to publish, release, or deploy a new version. Automatically handles version bumping, compilation, verification, and publishing.
---

# ÆtherLight Publishing Skill

## What This Skill Does

Automates the complete release process for ÆtherLight:
- Bumps version across all packages
- Compiles TypeScript and verifies build
- Packages VS Code extension (.vsix)
- Builds desktop app installers (.exe and .msi)
- Publishes to npm registry
- Creates git tag and GitHub release with all artifacts

## When Claude Should Use This

Use this skill when the user:
- Says "publish this" or "let's publish" or "release a new version"
- Wants to deploy changes to npm
- Mentions creating a release
- Asks to bump the version and publish

## How to Use

### Pre-Release Workflow Check

1. **Verify proper Git workflow**:
   - Should be on `master` branch after PR merge
   - If not on master, guide user through proper workflow:
     ```
     1. Create PR from feature branch
     2. Get review and merge to master
     3. Checkout master and pull latest
     4. Then run publish script
     ```

2. **Ask for version type** (if not specified):
   ```
   Which version type?
   - patch: Bug fixes (0.13.20 → 0.13.21)
   - minor: New features (0.13.20 → 0.14.0)
   - major: Breaking changes (0.13.20 → 1.0.0)
   ```

3. **Run the automated publishing script**:
   ```bash
   node scripts/publish-release.js [patch|minor|major]
   ```

4. **Monitor output** - The script will (IN THIS ORDER):
   - ✓ Verify npm authentication (must be `aelor`)
   - ✓ Verify Git workflow (branch, clean, up-to-date)
   - ✓ Check GitHub CLI authentication (required)
   - ✓ Bump version across all packages
   - ✓ Compile TypeScript
   - ✓ Verify compiled artifacts exist
   - ✓ Package .vsix extension
   - ✓ Build desktop app installers (if configured)
   - ✓ Commit version bump
   - ✓ Create git tag
   - ✓ Push to GitHub (FIRST)
   - ✓ Create GitHub release with .vsix and installers
   - ✓ Verify GitHub release has all artifacts
   - ✓ Publish to npm registry (LAST)
   - ✓ Verify all packages published correctly

5. **Report completion**:
   ```
   ✅ Version X.X.X published successfully!
   - npm: https://www.npmjs.com/package/aetherlight
   - GitHub: https://github.com/AEtherlight-ai/lumina/releases/tag/vX.X.X
   ```

## Error Handling

If the script fails, help the user:

**Not logged in to npm:**
```bash
npm login
# Username: aelor
```

**GitHub CLI not installed:**
```bash
# Windows (winget)
winget install --id GitHub.cli

# Mac (homebrew)
brew install gh
```

**Not logged in to GitHub CLI:**
```bash
gh auth login
# Follow prompts to authenticate
```

**Uncommitted git changes:**
```bash
git status
# User needs to commit or stash changes
```

**Compilation errors:**
Show the TypeScript errors from the output

**VSIX not created:**
Check the package.json scripts

**Desktop app build fails:**
```bash
cd products/lumina-desktop
npm run tauri build
# Check for Rust compilation errors or missing dependencies
```

**Installers not found after build:**
```bash
# Desktop installers should be at:
find ./products/lumina-desktop/src-tauri/target/release/bundle -name "*.exe" -o -name "*.msi"

# Copy to vscode-lumina directory:
cp ./products/lumina-desktop/src-tauri/target/release/bundle/msi/*.msi ./vscode-lumina/
cp ./products/lumina-desktop/src-tauri/target/release/bundle/nsis/*.exe ./vscode-lumina/
```

**GitHub release creation fails:**
This is CRITICAL - users install from GitHub releases. The script will:
- Exit immediately if gh CLI not installed
- Exit if not authenticated to GitHub
- Verify the release was created with .vsix and installers
- Fail loudly if any step doesn't work

## Important Rules

**ALWAYS use the automated script** (`scripts/publish-release.js`)

**NEVER manually run individual publish steps** - this caused the v0.13.20 bug where users saw wrong versions after updating.

**Why the script is critical:**
- Prevents version mismatches
- Ensures everything is compiled before publishing
- No timing issues or partial deploys
- Verifies all artifacts before publishing anything
- Includes desktop app installers in GitHub release
- .npmignore prevents bloated npm packages (was 246MB, now 251KB)

## Related Files

- `scripts/publish-release.js` - The automation script
- `scripts/bump-version.js` - Version synchronization
- `.claude/commands/publish.md` - User-invoked command
- `PUBLISHING.md` - Publishing documentation
- `UPDATE_FIX_SUMMARY.md` - Why we use this approach
- `vscode-lumina/.npmignore` - Excludes binaries from npm package
- `products/lumina-desktop/` - Desktop app source (Tauri + Rust)

## Known Issues Fixed

### v0.13.28: Manual publish caused version mismatch
**Issue:** npm showed 0.13.26, GitHub release had v0.13.28, auto-update didn't work
**Cause:** Automated script was bypassed - manual version bump, manual git tag, manual GitHub release
**Result:** TypeScript compilation skipped, npm publish skipped, all verification skipped
**Fix:** v0.13.29 published using complete automated process with desktop installers

### v0.13.29: npm package bloat
**Issue:** npm publish failed with "413 Payload Too Large" (246MB)
**Cause:** All old .vsix files (0.13.11-0.13.28) included in npm package
**Fix:** Created .npmignore to exclude *.vsix, *.exe, *.msi files
**Result:** Package size reduced to 251KB (1000x smaller)

### v0.13.29: Sub-packages not published (CRITICAL)
**Issue:** Users couldn't install or update - "No matching version found for aetherlight-analyzer@^0.13.29"
**Cause:** Publish script only published main package, not sub-packages (analyzer, SDK, node bindings)
**Impact:**
- Main package published: aetherlight@0.13.29 ✅
- Sub-packages still at 0.13.28 ❌
- npm install failed for ALL users
- Update notifications worked but installs failed silently
**Fix:** Updated publish script to publish ALL 4 packages in dependency order
**Prevention:** Script now:
1. Publishes sub-packages FIRST (analyzer, SDK, node)
2. Publishes main package LAST (depends on sub-packages)
3. Verifies each package at correct version
4. Fails loudly if any package verification fails
**Files:** `scripts/publish-release.js:270-322`

**Key lesson:** ALWAYS use the automated script. Manual steps WILL cause bugs.
