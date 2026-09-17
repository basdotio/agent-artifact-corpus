---
name: ink-setup
description: Configure ink (React for CLI) in a Dungeonmaster package. Use when setting up a new CLI package with ink, troubleshooting ESM/bundling issues with ink, or creating ink adapters and widgets.
---

# Ink CLI Setup

This skill provides the configuration and patterns needed to use ink (React for CLI) in a Dungeonmaster architecture
package.

## Critical Version Requirement

**Use ink v3.2.0, NOT v4+**

ink v4+ is ESM-only with top-level await. Jest's `jest.mock()` hoisting does NOT work in ESM mode:

> "Since ESM evaluates static import statements before looking at the code, the hoisting of `jest.mock` calls that
> happens in CJS won't work for ESM." - [Jest ESM docs](https://jestjs.io/docs/ecmascript-modules)

ink v3.2.0 has no `"type": "module"` field, defaulting to CJS. This enables:

- Single unified Jest config
- `jest.mock()` hoisting works
- Proxy pattern works
- No ESM/CJS contamination issues

## When to Use

- Setting up a new CLI package that uses ink
- Troubleshooting Jest test failures with ink
- Creating ink component adapters
- Writing widget tests

## Key Requirements

1. **Use ink v3.2.0**: CJS-compatible
2. **Package is ESM**: `"type": "module"` (for runtime)
3. **Bundle the entry point**: Use esbuild to resolve imports
4. **Single Jest config**: CJS mode with proxy transformer
5. **Local test render utility**: Replace ink-testing-library

## Quick Reference

See the following bundled files for detailed configuration:

- [PACKAGE-CONFIG.md](PACKAGE-CONFIG.md) - package.json, tsconfig.json setup
- [JEST-CONFIG.md](JEST-CONFIG.md) - Jest configuration (single unified config)
- [ADAPTERS.md](ADAPTERS.md) - Ink adapter patterns
- [WIDGETS.md](WIDGETS.md) - Widget component patterns
- [STARTUP.md](STARTUP.md) - Entry point and bin setup
- [TESTING.md](TESTING.md) - Testing patterns with local ink-test-render
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and fixes

## File Structure

```
packages/my-cli/
├── bin/
│   └── my-cli.e2e.test.ts
├── src/
│   ├── adapters/
│   │   ├── ink/
│   │   │   ├── box/
│   │   │   │   ├── ink-box-adapter.ts
│   │   │   │   ├── ink-box-adapter.proxy.ts   # No-op proxy (real ink used)
│   │   │   │   └── ink-box-adapter.test.ts
│   │   │   ├── text/
│   │   │   │   ├── ink-text-adapter.ts
│   │   │   │   ├── ink-text-adapter.proxy.ts
│   │   │   │   └── ink-text-adapter.test.ts
│   │   │   └── use-input/
│   │   │       ├── ink-use-input-adapter.ts
│   │   │       └── ink-use-input-adapter.proxy.ts
│   │   ├── ink-testing-library/
│   │   │   └── render/
│   │   │       ├── ink-test-render.ts               # Local CJS-compatible render utility
│   │   │       ├── ink-testing-library-render-adapter.ts
│   │   │       ├── ink-testing-library-render-adapter.proxy.ts
│   │   │       └── ink-testing-library-render-adapter.test.ts
│   │   └── react/
│   │       ├── module/
│   │       │   ├── react-module-adapter.ts          # Re-exports React for JSX namespace
│   │       │   ├── react-module-adapter.proxy.ts
│   │       │   └── react-module-adapter.test.ts
│   │       └── use-state/
│   │           ├── react-use-state-adapter.ts
│   │           └── react-use-state-adapter.proxy.ts
│   ├── startup/
│   │   └── start-my-cli.ts
│   └── widgets/
│       └── my-app/
│           ├── my-app-widget.tsx                    # Main orchestrator widget
│           ├── my-app-widget.test.tsx
│           ├── my-app-widget.proxy.ts
│           ├── menu-screen-layer-widget.tsx         # Layer widgets for screens
│           ├── menu-screen-layer-widget.test.tsx
│           ├── menu-screen-layer-widget.proxy.ts
│           └── help-screen-layer-widget.tsx
├── jest.config.js           # Single unified config (ESM format)
├── package.json
└── tsconfig.json
```
