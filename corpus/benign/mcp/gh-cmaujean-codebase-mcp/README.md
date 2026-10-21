# Codebase MCP Server

A Model Context Protocol (MCP) server that analyzes any application codebase with real-time file watching, providing AI assistants like Claude with deep insights into your project structure, code patterns, and architecture.

## Features

- **Universal Codebase Analysis**: Works with any programming language or framework (not just Vite)
- **Real-time File Watching**: Automatically stays synchronized with file system changes
- **Smart Framework Detection**: Identifies React, Vue, Svelte, Angular, or vanilla projects
- **Intelligent Filtering**: Excludes node_modules, build files, and other non-essential content
- **File Categorization**: Organizes files into source, config, test, documentation, and build categories
- **Content Search**: Search files by name patterns, content, type, or category
- **Multi-project Support**: Switch between different projects seamlessly
- **Global Installation**: Install once, use anywhere

## Installation

### Global Installation (Recommended)

```bash
# Install globally with Bun
bun install -g @codebase-mcp/server

# Or install globally with npm
npm install -g @codebase-mcp/server
```

### Local Development Installation

```bash
# Clone the repository
git clone https://github.com/your-username/codebase-mcp-server.git
cd codebase-mcp-server

# Install dependencies
bun install

# Build the project
bun run build

# Install globally from local build
bun run install-global
```

## Configuration

### With Claude Code (Console/CLI)

Add the MCP server using the Claude Code CLI:

```bash
# Add the MCP server (local scope - for current project)
claude mcp add codebase-mcp codebase-mcp

# Or add for user scope (available across all projects)
claude mcp add --scope user codebase-mcp codebase-mcp

# Verify it was added
claude mcp list
```

### With Claude Desktop

Add to your Claude Desktop settings:

```json
{
  "mcps": {
    "codebase-mcp": {
      "command": "codebase-mcp",
      "env": {}
    }
  }
}
```

## Usage

### Quick Start

1. **Install the MCP server globally** (see installation above)
2. **Configure Claude Code/Desktop** with the MCP server
3. **Restart Claude Code/Desktop**
4. **Analyze any codebase:**

```
Hey Claude, can you ingest the codebase at /path/to/my-project?
```

### Multi-Project Usage

#### Single Instance (Project Switching)
Within one Claude Code instance, switch between projects:

```
Claude, ingest the React app at /Users/me/my-react-app
Claude, now switch to analyze the Python project at /Users/me/my-python-project
Claude, go back to the React app and show me the component structure
```

#### Multiple Instances (Concurrent Projects)
Each Claude Code instance runs its own isolated MCP server process:

- **Project A** (Claude Code in `/path/to/project-a/`): Own MCP server with PID 1234
- **Project B** (Claude Code in `/path/to/project-b/`): Own MCP server with PID 5678
- **Project C** (Claude Code in `/path/to/project-c/`): Own MCP server with PID 9012

Each instance maintains its own:
- File index and project structure
- File watcher for real-time updates
- Independent state and memory

No conflicts or interference between projects!

### Real-time Synchronization

Once a codebase is ingested, the server automatically:
- Monitors all file changes in real-time
- Updates the file index when files are created, modified, or deleted
- Re-analyzes project structure automatically
- Keeps Claude's understanding up-to-date with your changes

### Available Tools

#### `ingest_codebase`
Analyzes a Vite project from a given path.

```json
{
  "path": "/path/to/vite/project",
  "includeTests": true,
  "includeDocs": true, 
  "maxDepth": 10
}
```

#### `get_project_structure`
Returns the complete project analysis including:
- Framework detection
- File distribution by category
- Directory structure
- Package.json analysis
- Key dependencies

#### `search_files`
Search for files by various criteria:

```json
{
  "pattern": "*.vue",
  "content": "useState",
  "fileType": "ts",
  "category": "source"
}
```

### Available Resources

Once a codebase is ingested, you can access:

- `project://structure` - Complete project structure as JSON
- `project://summary` - Human-readable project summary
- `file://path/to/file` - Individual file contents

## Example Workflow

```bash
# Start the server
bun run server.ts

# In Claude Code:
# "Ingest the codebase at /Users/me/my-vite-app"
# "Show me the project structure"
# "Find all Vue components that use the Composition API"
# "What's the overall architecture of this application?"
# "Generate a new component following this project's patterns"
```

## Supported File Types

### Source Files
- JavaScript/TypeScript (`.js`, `.ts`, `.jsx`, `.tsx`)
- Vue components (`.vue`)
- Svelte components (`.svelte`)
- Stylesheets (`.css`, `.scss`, `.sass`, `.less`)

### Configuration Files
- `package.json`, `vite.config.*`, `tsconfig.json`
- Environment files (`.env*`)
- Other config formats (`.yaml`, `.toml`, etc.)

### Documentation
- Markdown files (`.md`)
- README files
- Documentation directories

## Configuration

The server intelligently excludes common directories and files:

### Excluded by Default
- `node_modules/`
- `dist/`, `build/`
- `.git/`, `.vscode/`, `.idea/`
- `coverage/`, `.nyc_output/`
- Log files and OS files

### File Size Limits
- Maximum file size: 1MB
- Maximum directory depth: 10 levels (configurable)

## Security

- **Local only**: Runs entirely on your local machine
- **No internet required**: All processing happens locally
- **Selective access**: Only reads files you explicitly point it to
- **Respects .gitignore patterns**: Won't expose sensitive files

## Troubleshooting

### Common Issues

1. **"Path does not exist"**: Ensure the provided path is correct and accessible
2. **"No package.json found"**: This is just a warning - the server works with any codebase
3. **Permission errors**: Ensure the server has read access to the target directory

### Multiple Instance Debugging

Each MCP server instance shows its Process ID (PID) for debugging:

```
Successfully ingested codebase from: /path/to/project
Server PID: 12345 (for debugging multiple instances)
```

**Check running instances:**
```bash
# See all running codebase-mcp processes
ps aux | grep codebase-mcp

# Kill a specific instance if needed
kill 12345
```

**Verify isolation:**
- Each Claude Code instance should show a different PID
- File changes in Project A should only affect that instance
- Each instance can watch different codebases simultaneously

### Debug Mode
```bash
# Run with additional logging
DEBUG=1 bun run server.ts

# Or check Claude Code logs for MCP server output
tail -f ~/.claude/logs/mcp.log
```

## Contributing

This is a generic Vite MCP server that can be extended for specific needs:

- Add support for other build tools (Webpack, Rollup, etc.)
- Implement more sophisticated code analysis
- Add support for monorepos
- Include dependency graph analysis

## License

MIT License - feel free to modify and distribute as needed.

## Next Steps

After setting up:

1. Configure Claude Code to use this MCP server
2. Point it at one of your Vite projects
3. Start asking Claude about your codebase structure
4. Use Claude to generate code that follows your existing patterns

The server provides deep context about your codebase, enabling much more accurate and relevant assistance from Claude.