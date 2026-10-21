# 🔧 Troubleshooting - MCP SVN

## Problem: "not a working copy"

### Typical error:
```
❌ Error: The directory 'C:\your\directory' is not an SVN working copy.
Make sure you are in a directory that contains an SVN repository or run checkout first.
```

### Cause:
This error occurs when you try to execute SVN commands (`svn info`, `svn status`, etc.) in a directory that **is not under SVN version control**.

### Solutions:

#### 1. **Switch to the correct directory**
If you already have an SVN working copy elsewhere:

```bash
# Configure the environment variable to point to your working copy
export SVN_WORKING_DIRECTORY="/path/to/your/working-copy"
```

On Windows:
```cmd
set SVN_WORKING_DIRECTORY=C:\path\to\your\working-copy
```

#### 2. **Check out a repository**
If you need to create a fresh working copy:

```bash
# Use the svn_checkout tool from the MCP
svn_checkout(
  url: "https://your-svn-server.com/repo/trunk",
  path: "my-project"
)
```

#### 3. **Check whether a directory is a working copy**
Look for the hidden `.svn` folder:

**Windows (PowerShell):**
```powershell
Get-ChildItem -Force | Where-Object {$_.Name -like ".svn*"}
```

**Linux/Mac:**
```bash
ls -la | grep .svn
```

## Environment Configuration

### Important Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SVN_PATH` | Path to the SVN executable | `C:/Program Files/TortoiseSVN/bin/svn.exe` |
| `SVN_WORKING_DIRECTORY` | Working directory | `C:/my-project` |
| `SVN_USERNAME` | Authentication user | `user@company.com` |
| `SVN_PASSWORD` | Password | `my-password` |

### Example MCP Configuration

```json
{
  "mcpServers": {
    "svn": {
      "command": "npx",
      "args": ["@grec0/mcp-svn"],
      "env": {
        "SVN_PATH": "C:/Program Files/TortoiseSVN/bin/svn.exe",
        "SVN_WORKING_DIRECTORY": "C:/my-project",
        "SVN_USERNAME": "my-user",
        "SVN_PASSWORD": "my-password"
      }
    }
  }
}
```

## System Verification

### 1. Verify the SVN installation
```bash
svn --version
```

### 2. Verify that the MCP works
Use the `svn_health_check()` tool to verify:
- ✅ SVN is available
- ✅ Working copy is valid
- ✅ Repository is accessible

### 3. Test basic commands
```bash
# Check the working copy info
svn info

# Show file status
svn status
```

## Typical Workflow

### 1. **First use - Check out**
```
1. svn_checkout(url: "https://server/repo", path: "my-project")
2. Configure SVN_WORKING_DIRECTORY to point to "my-project"
3. Use the other SVN commands
```

### 2. **Regular use - Working with files**
```
1. svn_info() - Get repository information
2. svn_status() - Show modified files
3. svn_add(paths: ["new-file.txt"])
4. svn_commit(message: "Add new file")
```

### 3. **Maintenance**
```
1. svn_update() - Update from the server
2. svn_cleanup() - Clean up the working copy if there are issues
```

## Common Errors and Solutions

### Error: "SVN command failed with code 1"
- **Cause**: SVN command failed
- **Solution**: Check the specific error message for details

### Error: "SVN is not available"
- **Cause**: SVN is not installed or not on PATH
- **Solution**: Install SVN or configure SVN_PATH

### Error: "Authentication failed"
- **Cause**: Incorrect credentials
- **Solution**: Check SVN_USERNAME and SVN_PASSWORD

### Error: "E215004: No more credentials or we tried too many times"
- **Cause**: Too many failed authentication attempts — credentials may be incorrectly cached
- **Solution**: Run `svn_clear_credentials()` to clear the SVN credentials cache

### Error: "Working copy locked"
- **Cause**: A previous SVN operation was interrupted
- **Solution**: Run `svn_cleanup()`

## Diagnostic Tools

### Full diagnostic command
```javascript
// Check the entire system
await svn_health_check();

// If there are issues, check step by step:
1. Check SVN: svn --version
2. Check the directory: ls -la .svn
3. Check the connection: svn info --non-interactive
```

## Support

If the problem persists after following this guide:

1. **Review the logs** of the MCP for specific errors
2. **Check permissions** on files and directories
3. **Test SVN commands manually** in the terminal
4. **Check connectivity** to the SVN server

---

**💡 Tip**: Always run `svn_health_check()` first to diagnose configuration issues.
