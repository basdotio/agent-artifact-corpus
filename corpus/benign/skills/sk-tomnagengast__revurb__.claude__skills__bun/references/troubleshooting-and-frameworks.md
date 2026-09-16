# Bun Troubleshooting and Integrations

Issue-resolution playbooks plus supported framework integrations and external resources.

## Common Issues and Solutions

### `command not found: bun`

- Add Bun's installation directory to system `PATH`
- Defaults: `~/.bun/bin` (macOS/Linux) or `%USERPROFILE%\.bun\bin` (Windows)

### TypeScript Path Mappings Not Working

- Confirm `tsconfig.json` defines the mappings
- Bun automatically respects mappings once the config exists at the project root

### Module Compatibility Issues

- Consult Node.js compatibility references
- Advanced hooks, inspector APIs, and trace events may be incomplete

### Slow Performance on Older CPUs

- Bun selects binary variants automatically during install
- Includes baseline builds for older Nehalem-era CPUs

### Runtime Errors After Dependency Changes

- Restart the Bun server to reload native modules
- Especially important after dependency upgrades or re-installs

### Debugging Runtime Issues

- Run entry files directly for full stack traces:

```bash
bun run path/to/entry-file.ts
```

### Module Cache Problems

- As a last resort, clear Bun's module cache:

```bash
rm -rf ~/.cache/bun/*
```

Use sparingly; modules will be re-downloaded.

## Framework Integration

- **React**: `bun init --react` scaffolds templates
- **Next.js**: Runtime-compatible with Bun
- **Remix**: First-class support
- **Express**: Works via Node.js compatibility layer
- **Hono**: Native Bun support with optimal performance

Guidance: rely on framework docs plus Bun release notes for integration nuances.

## Additional Resources

- Official documentation: https://bun.sh/docs
- GitHub repository: https://github.com/oven-sh/bun
- Discord community: https://bun.sh/discord
- 100+ guides and examples in the official docs
