# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) based SSH connection tool that enables large language models to connect to remote servers via SSH and perform file operations. It's built using Python 3.12+ with the MCP protocol and paramiko for SSH functionality.

## Development Commands

### Setup and Installation
```bash
# Install dependencies
uv sync

# Run the MCP server
uv run src/main.py
```

### Development and Testing
```bash
# Debug with MCP inspector
./inspector.sh
```

The `inspector.sh` script uses the MCP inspector to debug the server: `npx @modelcontextprotocol/inspector uv --directory "$SCRIPT_DIR" run src/main.py`

## Architecture

### Core Components

**MCP Server (`src/main.py`)**
- FastMCP-based server with 6 main tools: `connect`, `disconnect`, `list_sessions`, `execute`, `upload`, `download`
- Handles SSH connection management and command execution
- Uses environment variables for default SSH parameters
- Implements output truncation (default 5000 chars) and session timeouts (default 30 minutes)

**Session Management (`src/session.py`)**
- `Session` dataclass: Manages individual SSH connections with auto-cleanup and activity tracking
- `SessionManager` class: Thread-safe session lifecycle management with automatic cleanup of inactive sessions
- Sessions are identified by 8-character random IDs

### Key Features

- **Authentication**: Supports both password and SSH key authentication
- **Session Persistence**: Maintains active SSH sessions with configurable timeouts
- **File Transfer**: SFTP support for upload/download operations
- **Command Execution**: Remote command execution with stdin support and timeout control
- **Auto-cleanup**: Background thread removes inactive sessions

### Environment Variables

Configure SSH defaults via environment variables:
- `SSH_HOST`, `SSH_PORT`, `SSH_USERNAME`, `SSH_PASSWORD`
- `SSH_KEY_PATH`, `SSH_KEY_PASSPHRASE`
- `SESSION_TIMEOUT` (minutes, default 30)
- `MAX_OUTPUT_LENGTH` (characters, default 5000)

### SSH Credentials File

Optional `ssh-credentials.json` file for secure local storage of SSH passwords with shell-style pattern matching support (via Python's `fnmatch` module).

**Setup**: Copy `ssh-credentials.json.example` to `ssh-credentials.json` and configure your credentials.

**Supported Patterns**:
- `*` - matches any characters
- `?` - matches single character  
- `[0-9]` - matches any digit
- `{dev,test,staging}` - matches any of the listed options

**Authentication Priority Order**:
1. Parameters passed to connect tool (`password`, `key_path`)
2. Exact match in credentials file (`username@host`)
3. Pattern match in credentials file (first matching pattern)
4. Environment variable password (`SSH_PASSWORD`)
5. Environment variable key (`SSH_KEY_PATH`)
6. Default SSH key (`~/.ssh/id_rsa` if exists)

**Example**:
```json
{
  "root@192.168.1.100": "password123",
  "admin@web-[0-9].example.com": "web_password",
  "deploy@server-{dev,test,staging}.company.com": "deploy_password",
  "admin@*.internal.network": "internal_password"
}
```

**Security Features**:
- File permissions automatically set to 600 (owner read/write only)
- Added to `.gitignore` to prevent accidental commits
- Only stores passwords (not SSH keys or other sensitive data)
- No caching - file is read fresh on each connection for immediate updates

### Dependencies

- `mcp[cli]>=1.6.0`: MCP protocol implementation
- `paramiko>=3.3.1`: SSH client functionality

## MCP Client Configuration

The server is designed to be used as an MCP server in LLM clients:

```json
{
  "mcpServers": {
    "my-mcp-ssh": {
      "command": "uv",
      "args": ["--directory", "<path>/my-mcp-ssh", "run", "src/main.py"],
      "env": {}
    }
  }
}
```