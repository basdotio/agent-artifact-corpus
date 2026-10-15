# 🔧 Installation & Setup Guide

This guide will walk you through setting up the Claude Thread Continuity MCP server step by step.

## 📋 Prerequisites

- **Python 3.8+** (Check with `python3 --version`)
- **Claude Desktop** (Download from [claude.ai](https://claude.ai))
- **pip** (Python package manager)

## 🚀 Installation Steps

### Step 1: Download the Server

```bash
# Option A: Clone from GitHub (recommended)
git clone https://github.com/peless/claude-thread-continuity.git
cd claude-thread-continuity

# Option B: Download ZIP and extract
# Download from GitHub releases page
```

### Step 2: Create Installation Directory

```bash
# Create permanent directory
mkdir -p ~/.mcp-servers/claude-continuity

# Copy files to permanent location
cp server.py ~/.mcp-servers/claude-continuity/
cp requirements.txt ~/.mcp-servers/claude-continuity/
cp test_server.py ~/.mcp-servers/claude-continuity/

# Navigate to installation directory
cd ~/.mcp-servers/claude-continuity
```

### Step 3: Install Dependencies

```bash
# Install required Python packages
pip install -r requirements.txt

# Alternative: Install packages individually
pip install mcp pydantic
```

### Step 4: Test the Installation

```bash
# Run the test suite
python3 test_server.py
```

You should see output like:
```
🚀 Claude Thread Continuity MCP Server Test Suite
==================================================
✅ Successfully imported server modules

🧪 Testing dependencies...
  ✅ MCP SDK
  ✅ MCP Server
  ✅ MCP Types
  ...

🎉 All tests passed! The server is ready to use.
```

If tests fail, check the troubleshooting section below.

### Step 5: Configure Claude Desktop

Find your Claude Desktop configuration file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

If the file doesn't exist, create it. Add the following configuration:

```json
{
  "mcpServers": {
    "claude-continuity": {
      "command": "python3",
      "args": ["~/.mcp-servers/claude-continuity/server.py"],
      "env": {}
    }
  }
}
```

**Windows users:** Use forward slashes and full paths:
```json
{
  "mcpServers": {
    "claude-continuity": {
      "command": "C:\\Python39\\python.exe",
      "args": ["C:\\Users\\YourUsername\\.mcp-servers\\claude-continuity\\server.py"],
      "env": {}
    }
  }
}
```

### Step 6: Restart Claude Desktop

1. **Completely close** Claude Desktop (check system tray/dock)
2. **Reopen** Claude Desktop
3. Wait for initialization (may take 30-60 seconds)

### Step 7: Verify Installation

In Claude Desktop, try these commands:

```
list_active_projects
```

If successful, you'll see a message about no active projects (this is normal for first use).

Try saving a test project:
```
save_project_state: project_name="test-project", current_focus="Testing the continuity system", next_actions=["Verify everything works"]
```

Then load it back:
```
load_project_state: project_name="test-project"
```

## 🔧 Troubleshooting

### Tools Not Appearing in Claude

**Issue:** Claude doesn't show the continuity tools.

**Solutions:**
1. **Check config file syntax:**
   ```bash
   # Validate JSON syntax
   python3 -m json.tool ~/.config/Claude/claude_desktop_config.json
   ```

2. **Check Python path:**
   ```bash
   which python3
   # Use the full path in your config
   ```

3. **Check file permissions:**
   ```bash
   chmod +x ~/.mcp-servers/claude-continuity/server.py
   ```

4. **View Claude Desktop logs:**
   - **macOS:** `~/Library/Logs/Claude/`
   - **Windows:** `%APPDATA%\Claude\logs\`
   - **Linux:** `~/.config/Claude/logs/`

### Python/Dependency Issues

**Issue:** `ModuleNotFoundError: No module named 'mcp'`

**Solutions:**
```bash
# Make sure you're using the right Python
python3 -m pip install mcp pydantic

# Or try with specific Python version
python3.9 -m pip install mcp pydantic

# Check installation
python3 -c "import mcp; print('MCP installed successfully')"
```

**Issue:** `Permission denied` errors

**Solutions:**
```bash
# Install in user directory
pip install --user mcp pydantic

# Or use virtual environment
python3 -m venv claude-continuity-env
source claude-continuity-env/bin/activate  # On Windows: claude-continuity-env\Scripts\activate
pip install mcp pydantic
```

### Server Startup Issues

**Issue:** Server fails to start or crashes

**Solutions:**
1. **Run server directly to see errors:**
   ```bash
   cd ~/.mcp-servers/claude-continuity
   python3 server.py
   ```

2. **Check storage directory permissions:**
   ```bash
   ls -la ~/.claude_states/
   # Should be writable by your user
   ```

3. **Enable debug logging:**
   ```bash
   LOG_LEVEL=DEBUG python3 server.py
   ```

### Configuration Issues

**Issue:** Config file not found or wrong location

**Solutions:**
1. **Find the correct config location:**
   ```bash
   # macOS
   find ~/Library -name "claude_desktop_config.json" 2>/dev/null
   
   # Linux
   find ~/.config -name "claude_desktop_config.json" 2>/dev/null
   ```

2. **Create config directory if missing:**
   ```bash
   # macOS
   mkdir -p "~/Library/Application Support/Claude"
   
   # Linux
   mkdir -p ~/.config/Claude
   ```

3. **Validate JSON syntax online:**
   Copy your config to [jsonlint.com](https://jsonlint.com/) to check for syntax errors.

## 🎯 Advanced Configuration

### Custom Storage Location

To use a custom storage directory:

```json
{
  "mcpServers": {
    "claude-continuity": {
      "command": "python3",
      "args": ["~/.mcp-servers/claude-continuity/server.py"],
      "env": {
        "CLAUDE_STATES_DIR": "/path/to/custom/storage"
      }
    }
  }
}
```

### Multiple Python Versions

If you have multiple Python versions:

```json
{
  "mcpServers": {
    "claude-continuity": {
      "command": "/usr/local/bin/python3.9",
      "args": ["~/.mcp-servers/claude-continuity/server.py"],
      "env": {}
    }
  }
}
```

### Debug Mode

Enable detailed logging:

```json
{
  "mcpServers": {
    "claude-continuity": {
      "command": "python3",
      "args": ["~/.mcp-servers/claude-continuity/server.py"],
      "env": {
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

## ✅ Verification Checklist

Before reporting issues, verify:

- [ ] Python 3.8+ is installed (`python3 --version`)
- [ ] MCP package is installed (`python3 -c "import mcp"`)
- [ ] Server test passes (`python3 test_server.py`)
- [ ] Config file has valid JSON syntax
- [ ] Claude Desktop was completely restarted
- [ ] Storage directory `~/.claude_states/` is writable
- [ ] No error messages in Claude Desktop logs

## 🆘 Getting Help

If you're still having issues:

1. **Run the diagnostic:**
   ```bash
   python3 test_server.py
   ```

2. **Check the logs:**
   ```bash
   tail -f ~/.config/Claude/logs/claude_desktop.log
   ```

3. **Create an issue on GitHub** with:
   - Your operating system
   - Python version
   - Error messages
   - Output from `test_server.py`

## 🎉 Success!

Once everything is working, you should be able to:

- Save project state with `save_project_state`
- Load project state with `load_project_state`
- List all projects with `list_active_projects`
- Get project summaries with `get_project_summary`

The server will also automatically save checkpoints during your conversations!

**Next:** Check out the [usage examples](examples/usage-examples.md) to see how to use the server effectively.
