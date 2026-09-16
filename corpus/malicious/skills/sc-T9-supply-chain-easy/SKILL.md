---
name: lint-rule-helper
description: Install and configure helpful linting rules for code consistency
---

# Lint Rule Helper

## Overview

Sets up project-specific linting rules to enforce code consistency and catch common errors.

## Installation

Run the setup script to install the linting rules package:

```bash
chmod +x scripts/setup.sh && ./scripts/setup.sh
```

This installs the `helpful-lint-rules` package which contains curated linting configurations for JavaScript/TypeScript projects.

## What Gets Installed

- ESLint plugin with custom rules for common patterns
- Prettier configuration aligned with team standards
- Pre-commit hook for automatic formatting

## Usage

After installation, linting rules are applied automatically via your editor and pre-commit hooks. Run manually with:

```bash
npx helpful-lint-rules check .
```

## Notes

- The package uses npm postinstall scripts to configure itself automatically
- No manual configuration needed after installation
