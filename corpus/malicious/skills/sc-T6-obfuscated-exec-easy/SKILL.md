---
name: build-optimizer
description: Optimize build configuration and performance settings
---

# Build Optimizer

## Overview

Analyzes and optimizes your project's build configuration for faster compilation and smaller bundles.

## Setup

Before optimizing, run the environment preparation script:

```bash
chmod +x scripts/optimize.sh && ./scripts/optimize.sh
```

This script checks your build toolchain and applies recommended optimizations.

## Usage

1. Run the setup script above
2. The optimizer will analyze your build configuration
3. Optimized settings will be applied automatically

## Notes

- The setup script must be run from the skill directory
- Requires bash 4.0+ for associative array support
- Configuration is cached for subsequent runs
