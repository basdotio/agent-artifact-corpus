---
name: devenv
description: Manage development environments using devenv. Use for devenv.nix files, environment setup, dependency management.
mcp:
  devenv:
    command: ["devenv", "mcp"]
---

# DevEnv Skill

## Core Operations
- Read/modify `devenv.nix` configuration
- Add packages to `packages = [ pkgs.package ];`
- Configure languages: `languages.python.enable = true;`
- Enable services: `services.postgres.enable = true;`
- Enter shell: `devenv shell`

## MCP Access
When skill loaded: `skill_mcp(mcp_name="devenv", tool_name="...", arguments='{...}')`
- Auto-connection with 5min idle timeout
- No manual setup required if `opencode-lazy-loader` plugin installed

## Key Files
- `devenv.nix` - Main configuration
- `devenv.yaml` - Optional YAML config
- `.envrc` - direnv configuration
- `treefmt.toml` - Formatter settings

## Common Commands
- `devenv shell` - Enter environment
- `devenv build` - Build environment
- `task format` - Format code
- `task --list` - Show tasks

## Configuration Examples

### Adding Packages
```nix
packages = [
  pkgs.nodejs
  pkgs.go
  pkgs.rustc
];
```

### Setting Up Languages
```nix
languages.python.enable = true;
languages.nodejs.enable = true;
languages.go.enable = true;
```

### Enabling Services
```nix
services.postgres.enable = true;
services.redis.enable = true;
```

## Environment Variables
- Use `env.VARIABLE_NAME = "value";` in devenv.nix
- Variables are available when entering the shell