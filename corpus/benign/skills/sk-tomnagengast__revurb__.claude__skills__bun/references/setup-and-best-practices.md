# Bun Setup and Best Practices

Installation requirements, performance notes, and patterns for development and production environments.

## Installation and Setup

Always install the latest Bun release:

```bash
npm view bun@latest version
```

**macOS/Linux (curl)**

```bash
curl -fsSL https://bun.sh/install | bash
```

Verify installation:

```bash
bun --version
```

If `bun` is not found, add the installation directory to `PATH`. Defaults:

- macOS/Linux: `~/.bun/bin`
- Windows: `%USERPROFILE%\.bun\bin`

Minimum requirements:

- Linux kernel 5.1 or higher
- macOS 10.15 or higher

## Performance Characteristics

Key Bun advantages:

1. **Startup time**: ~4x faster than Node.js
2. **Memory overhead**: Lower usage via JavaScriptCore
3. **Package installation**: Faster than npm/yarn/pnpm
4. **Test execution**: ~100x faster than Jest
5. **Script execution**: ~28x faster overhead for package.json scripts

## Best Practices

### Development

1. Use watch mode: `bun --watch index.ts`
2. Leverage native TypeScript support; skip extra transpilers
3. Use hot reloading: `bun --hot index.ts`
4. Favor Web-standard APIs for compatibility

### Production

1. Compile with optimization flags: `--minify --sourcemap --bytecode`
2. Validate Node.js compatibility for critical modules pre-deploy
3. Prefer standalone executables for simplified deployment
4. Enable sourcemaps for debugging production issues

### Project Structure

1. Initialize with `bun init` to scaffold TypeScript configs
2. Use workspaces for monorepos and shared packages
3. Bundle frontend assets via HTML imports when building full-stack binaries

### Environment Management

1. Rely on `.env` auto-loading for secrets and configuration
2. Use suffix-based overrides (`.env.local`, `.env.production`) for multi-environment workflows
3. Restart Bun servers after dependency changes to reload native bindings
