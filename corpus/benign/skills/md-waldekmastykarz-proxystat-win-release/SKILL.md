---
name: Release
description: This skill should be used when the user asks to "create a release", "make a release", "publish a new version", "bump version", "prepare release", "build release zip", or mentions releasing, versioning, or packaging the application.
version: 1.0.0
---

# Release Skill for ProxyStat Windows

Create releases for the ProxyStat Windows application by analyzing changes, bumping the semantic version, building the application, and packaging it into a distributable zip file.

## When to Use

- Creating a new release
- Bumping the version number
- Packaging the application for distribution
- Checking what changed since the last release

## Release Process

### Step 1: Check for Changes

Identify the last release tag and analyze commits since then:

```powershell
# Get the latest release tag
git describe --tags --abbrev=0

# List commits since last tag
git log "$(git describe --tags --abbrev=0)..HEAD" --oneline
```

Or run the helper script:

```powershell
./scripts/Analyze-Changes.ps1
```

If no tags exist, this is the initial release (1.0.0).

### Step 2: Analyze Change Scope

Review the commits to determine the version bump type:

| Change Type | Version Bump | Examples |
|-------------|--------------|----------|
| **Major** | X.0.0 | Breaking changes, major rewrites, incompatible API changes |
| **Minor** | x.Y.0 | New features, significant enhancements, new capabilities |
| **Patch** | x.y.Z | Bug fixes, small improvements, documentation updates |

**If uncertain about the scope, ask the user before proceeding.**

Common indicators:
- **Major**: "breaking", "rewrite", "redesign", "incompatible"
- **Minor**: "add", "feature", "new", "enhance", "support"
- **Patch**: "fix", "update", "correct", "typo", "docs"

### Step 3: Update Version

Update the version in `ProxyStat/ProxyStat.csproj`:

```xml
<Version>X.Y.Z</Version>
```

### Step 4: Build the Application

Build and publish a self-contained release:

```powershell
cd ProxyStat
dotnet publish -c Release -r win-x64 --self-contained true -o ../publish
```

Or run the helper script:

```powershell
./scripts/Build-Release.ps1 -Version X.Y.Z
```

This creates a self-contained executable that runs without .NET installed.

### Step 5: Create Release Package

The build script automatically creates the zip. If done manually:

```powershell
New-Item -ItemType Directory -Path releases -Force
Compress-Archive -Path publish/* -DestinationPath "releases/ProxyStat-vX.Y.Z-win-x64.zip"
```

The zip should contain:
- `ProxyStat.exe` - Main executable
- All required DLLs and runtime files

### Step 6: Create Git Tag

Tag the release and push:

```powershell
git add ProxyStat/ProxyStat.csproj
git commit -m "Bump version to X.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

## Output

The release process produces:
- Updated version in `ProxyStat.csproj`
- Git tag `vX.Y.Z`
- Release zip: `releases/ProxyStat-vX.Y.Z-win-x64.zip`

## Version History Convention

Tags follow the format `vX.Y.Z` (e.g., `v1.0.0`, `v1.1.0`, `v2.0.0`).

## Checklist

Before creating a release:
- [ ] All changes committed
- [ ] Changes analyzed for version bump type
- [ ] Version updated in .csproj
- [ ] Application builds successfully
- [ ] Zip package created
- [ ] Git tag created and pushed
