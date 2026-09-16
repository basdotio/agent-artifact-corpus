---
name: monorepo-toolchain
description: Set up monorepo development toolchain with workspace management
---

# Monorepo Toolchain

## Overview

Configures essential toolchain for monorepo development, including workspace management, cross-package linking, and shared configuration.

## Installation

Run the toolchain installer:

```bash
chmod +x scripts/install_tools.sh && ./scripts/install_tools.sh
```

## What Gets Installed

- `workspace-tools`: Python-based workspace management utilities
  - Dependency graph visualization
  - Cross-package version synchronization
  - Shared configuration management
  - Build order resolution

## Usage

After installation:

```bash
# Analyze workspace dependencies
workspace-tools analyze

# Sync versions across packages
workspace-tools sync-versions

# Generate dependency graph
workspace-tools graph --output deps.svg
```

## Notes

- Requires Python 3.8+ and pip
- The package is installed from the bundled source
- Configuration is stored in `workspace-tools.config.json`
