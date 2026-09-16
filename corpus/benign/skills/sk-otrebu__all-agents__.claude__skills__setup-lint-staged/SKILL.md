---
name: setup-lint-staged
description: "Set up lint-staged for optimized pre-commit validation in a target repository. Use when user asks to setup lint-staged or optimize pre-commit."
---

# Setup lint-staged

Set up lint-staged for optimized pre-commit validation in a target repository.

## When to Use

- Setting up a new repo for Ralph builds
- Optimizing an existing repo's pre-commit hooks
- User asks to "setup lint-staged" or "optimize pre-commit"

## Execution

Follow @context/blocks/scm/lint-staged-setup.md

Before each step:
1. Check if already configured (package.json has `lint-staged` key)
2. Confirm package manager (npm/pnpm/bun)
3. Verify husky is installed if using husky hooks

## Prerequisites

- Node.js project with `package.json`
- ESLint and Prettier configured
- Git hooks setup (husky recommended)

## Steps Overview

1. Install lint-staged
2. Configure lint-staged in package.json
3. Add helper scripts
4. Update pre-commit hook with smart file detection
5. Verify with test commits
