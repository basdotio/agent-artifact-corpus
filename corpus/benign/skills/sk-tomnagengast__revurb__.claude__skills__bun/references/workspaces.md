# Bun Workspaces Guide

Detailed instructions for creating, maintaining, and debugging Bun monorepos using the standard `workspaces` field in `package.json`.

## When to Load This Reference

- The repo contains a root `package.json` with a `workspaces` array/glob
- Users mention linking packages, hoisting dependencies, or cross-package scripts
- Dependency installation or script execution behaves differently across packages

## Workspace Structure

1. Create a root `package.json` at the monorepo root.
2. Define workspaces:

```json
{
  "name": "my-monorepo",
  "private": true,
  "workspaces": ["packages/*", "apps/*"]
}
```

3. Each workspace (e.g., `packages/ui`) has its own `package.json`.
4. Use `.gitignore` to exclude `node_modules` (hoisted to the root by default).

## Installing Dependencies

- `bun install` (run from the repo root) installs all workspace deps and creates a shared lockfile (`bun.lockb`).
- Add packages to a specific workspace:

```bash
bun add react --cwd packages/ui
```

- Or use the workspace flag (Bun v1.0+):

```bash
bun add react -w packages/ui
```

- Add dev dependencies globally:

```bash
bun add -d typescript
```

This hoists TypeScript to the root and makes it available to all workspaces.

## Local Package Linking

Use relative `workspace:*` specifiers to link local packages without publishing:

```json
{
  "dependencies": {
    "@acme/ui": "workspace:*"
  }
}
```

During `bun install`, Bun symlinks the local package so changes are reflected instantly.

## Running Scripts

### Run a Single Workspace Script

```bash
bun run --cwd apps/web dev
```

### Filtered Runs (Bun v1.1+)

```bash
bun run --filter apps/web test
```

Filtering respects dependency graphs (similar to `pnpm --filter`) so you can run scripts per package or package group.

### Cross-package Commands

Use `bunx` with filtering to run scaffolding or tools in a specific workspace:

```bash
bunx --cwd packages/api prisma generate
```

## Publishing or Building Packages

1. Use `bun build --compile` within each package when producing binaries.
2. For libraries, run `bun build src/index.ts --outdir dist`.
3. Use workspace scripts to orchestrate multi-package builds:

```json
{
  "scripts": {
    "build": "bun run --filter ./packages/* build"
  }
}
```

## Best Practices

1. Keep `private: true` on the root `package.json` to avoid accidental publishes.
2. Use consistent TypeScript configs—share a base `tsconfig.json` at the root and extend in each workspace.
3. Pin local package versions (e.g., `"workspace:^"`) so consumers know when semver bumps occur.
4. Run `bun install --no-save` for experiments to avoid polluting lockfiles.
5. Commit `bun.lockb`—Bun’s binary lockfile ensures reproducible installs.

## Troubleshooting

### Dependency Not Found

- Run `bun install --force` to rebuild the symlink tree.
- Confirm the workspace path matches the glob pattern.

### Script Uses Wrong Package Version

- Ensure `node_modules` at the workspace level is not committed.
- Check for duplicate `node_modules` directories; delete them so Bun hoists correctly.

### Workspace Not Detected

- Bun only recognizes workspaces defined in the root `package.json`.
- Ensure glob patterns (`packages/*`) resolve to directories with `package.json`.

### Native Modules per Workspace

- After installing native deps (e.g., Prisma, sharp), restart Bun servers in packages consuming them.
- For cross-platform builds, compile per target inside each workspace to avoid ABI mismatches.
