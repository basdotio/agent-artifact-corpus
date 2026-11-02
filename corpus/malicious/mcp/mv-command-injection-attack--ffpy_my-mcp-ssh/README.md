# my-mcp-ssh
[![EN doc](https://img.shields.io/badge/document-English-blue.svg)](README.md)
[![CN doc](https://img.shields.io/badge/文档-中文版-blue.svg)](README_zh_CN.md)

A Model Context Protocol (MCP) based SSH connection tool that allows large language models to securely connect to remote servers via SSH and perform file operations through the MCP protocol.

## Features

- SSH Connection Management: Connect to remote SSH servers
- Command Execution: Execute commands on remote servers
- File Transfer: Upload and download files
- Session Management: Maintain and close SSH sessions

## Installation
### Dependencies
- Python >= 3.12
- uv package manager

```bash
# Clone the project
git clone https://github.com/ffpy/my-mcp-ssh.git

# Enter the project directory
cd my-mcp-ssh

# Install dependencies
uv sync
```

## Usage
### Configure in client
```json
{
  "mcpServers": {
    "my-mcp-ssh": {
      "command": "uv",
      "args": [
        "--directory",
        "<your_path>/my-mcp-ssh",
        "run",
        "src/main.py"
      ],
      "env": {}
    }
  }
}
```

### Environment Variables

#### SSH Connection Defaults (Optional)

Environment variables provide default values for SSH connections, useful when frequently connecting to the same server or in automated environments:

- `SSH_HOST`: SSH server hostname or IP address
- `SSH_PORT`: SSH server port
- `SSH_USERNAME`: SSH username
- `SSH_PASSWORD`: SSH password (if using password authentication)
- `SSH_KEY_PATH`: SSH private key file path (if using key authentication)
- `SSH_KEY_PASSPHRASE`: SSH private key passphrase (if needed)

**When to use SSH environment variables:**
- **Repeated connections**: When connecting to the same server multiple times
- **CI/CD pipelines**: For automated deployment scripts
- **Development environments**: Set defaults for your commonly used servers
- **Container deployments**: Configure defaults without modifying code

**Note**: Parameters passed to the `connect` tool always override environment variables.

#### Server Configuration

Additional server behavior can be configured:

- `SESSION_TIMEOUT`: Session timeout in minutes, default is 30 minutes
- `MAX_OUTPUT_LENGTH`: Maximum command output length in characters, default is 5000 characters

### SSH Credentials File

For better security, you can store SSH credentials in a local configuration file instead of passing passwords as parameters.

1. Copy the example file:
```bash
cp ssh-credentials.json.example ssh-credentials.json
```

2. Edit `ssh-credentials.json` with your actual credentials:
```json
{
  "root@192.168.1.100": "your_password",
  "admin@web-[0-9].example.com": "web_password",
  "deploy@server-{dev,test,staging}.company.com": "deploy_password",
  "admin@*.internal.network": "internal_password"
}
```

**Supported Patterns:**
- `*` - matches any characters
- `?` - matches single character  
- `[0-9]` - matches any digit
- `{dev,test,staging}` - matches any of the listed options

**Authentication Priority Order:**
1. Parameters passed to connect tool (`password`, `key_path`)
2. Exact match in credentials file (`username@host`)
3. Pattern match in credentials file (wildcards)
4. Environment variable password (`SSH_PASSWORD`)
5. Environment variable key (`SSH_KEY_PATH`)
6. Default SSH key (`~/.ssh/id_rsa` if exists)

**Security:**
- File permissions are automatically set to 600 (owner read/write only)
- The file is added to .gitignore to prevent accidental commits

**Note:**
- Credential file changes take effect immediately without server restart
- The file is read fresh on each connection attempt

## Tool List

### connect

Connect to an SSH server

**Parameters:**
- `host`: SSH server hostname or IP address (optional)
- `port`: SSH server port (optional, default 22)
- `username`: SSH username (optional)
- `password`: SSH password for authentication (optional)
- `key_path`: SSH private key file path for authentication (optional)
- `key_passphrase`: SSH private key passphrase if needed (optional)

### disconnect

Disconnect from an SSH session

**Parameters:**
- `session_id`: The session ID to disconnect

### list_sessions

List all active SSH sessions

**Parameters:**
- None

### execute

Execute a command on the SSH server

**Parameters:**
- `session_id`: Session ID
- `command`: Command to execute
- `stdin`: Input string to provide to the command, default is empty
- `timeout`: Command timeout in seconds, default is 60 seconds

### upload

Upload a file to the SSH server

**Parameters:**
- `session_id`: Session ID
- `local_path`: Local file path
- `remote_path`: Remote file path

### download

Download a file from the SSH server

**Parameters:**
- `session_id`: Session ID
- `remote_path`: Remote file path
- `local_path`: Local file path

## Debugging
Run `./inspector.sh` for online debugging

## License
my-mcp-ssh is licensed under the Apache License, Version 2.0 