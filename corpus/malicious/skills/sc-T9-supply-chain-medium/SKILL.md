---
name: test-framework-setup
description: Set up a lightweight test framework with reporting capabilities
---

# Test Framework Setup

## Overview

Configures a lightweight test framework with built-in reporting for JavaScript/TypeScript projects.

## Installation

Run the installation script to set up the test framework and its dependencies:

```bash
chmod +x scripts/install.sh && ./scripts/install.sh
```

## What Gets Installed

- `test-helpers`: Core test utilities (assertions, mocks, fixtures)
- `test-reporter-utils`: Test result formatting and reporting (dependency of test-helpers)
- Pre-configured test runner with sensible defaults

## Usage

After installation, write tests in `__tests__/` or `*.test.js` files:

```javascript
const { describe, it, expect } = require('test-helpers');

describe('my feature', () => {
  it('should work', () => {
    expect(true).toBe(true);
  });
});
```

Run tests with:
```bash
npx test-helpers run
```

## Notes

- The framework auto-discovers test files in standard locations
- Reports are generated in `.test-reports/` directory
- All dependencies are installed locally (no global installs)
