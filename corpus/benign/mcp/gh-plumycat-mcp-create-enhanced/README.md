# MCP Create Enhanced

An **enhanced version** of the dynamic MCP server management service that creates, runs, and manages Model Context Protocol (MCP) servers dynamically. This service runs as an MCP server itself and spawns/manages other MCP servers as child processes, enabling a robust and flexible MCP ecosystem.

## 🔄 Enhanced Version

This is an **enhanced and improved version** of [tesla0225/mcp-create](https://github.com/tesla0225/mcp-create) with significant improvements and new features.

<a href="https://glama.ai/mcp/servers/lnl6xjkkeq">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/lnl6xjkkeq/badge" alt="Create Server MCP server" />
</a>

## 🌟 Key Features

- **Dynamic MCP Server Creation**: Create and run MCP server code on-the-fly
- **Multi-Language Support**: TypeScript, JavaScript, and Python server templates
- **Parameter Validation**: Strict JSON Schema validation with proper MCP error codes (-32602)
- **Server Persistence**: Save/load/delete servers to/from disk
- **Tool Execution**: Execute tools on child MCP servers with validation
- **Server Management**: Update, restart, and delete servers as needed
- **Robust Python Support**: Fixed Python server stability issues

## 🔧 Recent Improvements

### ✨ New Features
- **MCP Parameter Validation**: Strict validation with proper error codes (-32602 for invalid parameters)
- **Server Persistence**: Save servers to disk and reload them later
- **Enhanced Python Support**: Fixed Python server stability and closure issues
- **Better Error Handling**: Improved error messages and MCP compliance

### 🐛 Bug Fixes
- Fixed Python servers closing immediately after creation
- Corrected pip installation to use `python3 -m pip`
- Fixed duplicate process spawning issues
- Improved EOF handling in Python templates
- Better signal handling and graceful shutdown

### 🔄 Differences from Original

This enhanced version provides significant improvements over the [original mcp-create](https://github.com/tesla0225/mcp-create):

| Feature | Original | Enhanced |
|---------|----------|----------|
| **Parameter Validation** | ❌ Default values for missing params | ✅ Strict JSON Schema validation with MCP errors |
| **Python Support** | ⚠️ Unstable, immediate closure | ✅ Robust, fixed stability issues |
| **Server Persistence** | ❌ Not available | ✅ Save/load/delete servers to/from disk |
| **Error Handling** | ⚠️ Basic error messages | ✅ Proper MCP error codes (-32602, -32601) |
| **Process Management** | ⚠️ Duplicate process spawning | ✅ Clean single process management |
| **Documentation** | ⚠️ French comments, basic docs | ✅ Full English docs with examples |

**Original Project**: [tesla0225/mcp-create](https://github.com/tesla0225/mcp-create)

## 📦 Installation

**Note: Docker is the recommended method for running this service**

### Docker Installation (Recommended)

```bash
# Build the Docker image
docker build -t mcp-create .

# Run the Docker container
docker run -it --rm mcp-create
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/PlumyCat/mcp-create-enhanced.git
cd mcp-create-enhanced

# Install dependencies
npm install

# Build
npm run build

# Run
npm start
```

### Testing Local Installation

After making changes to the code, you can test locally:

```bash
# Rebuild after changes
npm run build

# Test the server directly (it will wait for MCP protocol input)
npm start

# Or test with a simple echo command
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | npm start
```

### Using Local Version with Claude Desktop

To use your modified local version with Claude Desktop, update your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-create-local": {
      "command": "node",
      "args": ["./build/index.js"],
      "cwd": "/path/to/your/mcp-create-enhanced"
    }
  }
}
```

**Note:** Replace `/path/to/your/mcp-create-enhanced` with the actual path to your local repository.

### Building Docker Image with Local Changes

To create a Docker image with your local changes:

```bash
# Build Docker image with your changes
docker build -t mcp-create-local .

# Test the Docker image
docker run -it --rm mcp-create-local

# Use with Claude Desktop
# Update claude_desktop_config.json:
{
  "mcpServers": {
    "mcp-create-local": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "mcp-create-local"]
    }
  }
}
```

## 🤖 Claude Desktop Integration

Add the following to your Claude Desktop configuration file (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mcp-create": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "mcp-create"]
    }
  }
}
```

## 🛠️ Available Tools

| Tool Name | Description | Input Parameters | Output |
|-----------|-------------|-----------------|--------|
| create-server-from-template | Create an MCP server from template | language: string<br>code?: string<br>dependencies?: object | { serverId: string, message: string } |
| execute-tool | Execute a tool on the server | serverId: string<br>toolName: string<br>args: object | Tool execution result |
| get-server-tools | Get list of server tools | serverId: string | { tools: ToolDefinition[] } |
| delete-server | Delete a server | serverId: string | { success: boolean, message: string } |
| list-servers | Get list of running servers | none | { servers: string[] } |
| save-server | Save a server to disk | serverId: string<br>name: string | Success message |
| list-saved-servers | List saved servers | none | Array of saved servers |
| load-saved-server | Load a saved server | savedServerId: string | New server ID |
| delete-saved-server | Delete a saved server | savedServerId: string | Success message |

## 📋 Usage Examples

### Creating a New Server

```json
{
  "name": "create-server-from-template",
  "arguments": {
    "language": "python",
    "code": "# Custom Python MCP server code here"
  }
}
```

### Executing a Tool with Validation

```json
{
  "name": "execute-tool",
  "arguments": {
    "serverId": "ba7c9a4f-6ba8-4cad-8ec8-a41a08c19fac",
    "toolName": "echo",
    "args": {
      "message": "Hello, dynamic MCP server!"
    }
  }
}
```

### Parameter Validation Example

If you try to execute a tool with missing required parameters:

```json
{
  "name": "execute-tool",
  "arguments": {
    "serverId": "ba7c9a4f-6ba8-4cad-8ec8-a41a08c19fac",
    "toolName": "echo",
    "args": {}
  }
}
```

You'll get a proper MCP error response:
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Invalid parameters: Missing required parameter: 'message'"
  }
}
```

## 🔄 Complete Workflow After Modifications

1. **Make your changes** in the source code
2. **Rebuild Docker**: `docker build -t mcp-create-local .`
3. **Test**: `docker run -it --rm mcp-create-local`
4. **Update Claude Desktop** configuration if needed

## 💡 Practical Tips

- **Different tag**: If you want to keep the old version, use a different tag:
  ```bash
  docker build -t mcp-create-local:v2 .
  ```

- **Cleanup**: Remove unused old images:
  ```bash
  docker image prune
  ```

- **Verification**: List your images to confirm:
  ```bash
  docker images | grep mcp-create
  ```

## 🏗️ Technical Specifications

- Node.js 18 or higher
- TypeScript (required)
- Dependencies:
  - @modelcontextprotocol/sdk: MCP client/server implementation
  - child_process (Node.js built-in): Child process management
  - fs/promises (Node.js built-in): File operations
  - uuid: Unique server ID generation
  - zod: JSON schema validation

## 🔒 Security Considerations

- **Code Execution Restrictions**: Consider sandboxing as the service executes arbitrary code
- **Resource Limitations**: Set limits on memory, CPU usage, file count, etc.
- **Process Monitoring**: Monitor and forcefully terminate zombie or runaway processes
- **Path Validation**: Properly validate file paths to prevent directory traversal attacks
- **Parameter Validation**: All tool parameters are validated against JSON schemas before execution

## 🧪 Testing

The project includes comprehensive validation for MCP parameters:

- ✅ **Valid parameters**: Normal execution
- ✅ **Missing required parameters**: Returns MCP error -32602 with explicit message
- ✅ **Wrong parameter types**: Returns MCP error -32602 with type details
- ✅ **Unknown tools**: Returns MCP error -32601
- ✅ **Optional parameters**: Handled correctly

## 📄 License

MIT

## 🤝 Contributing

Feel free to submit issues and pull requests. This project has been enhanced with Claude Code assistance to provide robust MCP server management capabilities.

---

🧪 **Generated with [Claude Code](https://claude.ai/code)**

Co-Authored-By: Claude <noreply@anthropic.com>