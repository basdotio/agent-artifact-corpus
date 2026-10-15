# Setup:
1. Compile server.cpp and run it
2. put the mcp.py in any AI (ex: Claude) MCP list, Heres an example config for Claude
```json
{
  "mcpServers": {
    "roblox": {
      "command": "path to your python.exe and it must have mcp installed (pip install mcp)",
      "args": [
        "path to server.py"
      ]
    }
  },
  "preferences": {
    "coworkScheduledTasksEnabled": false,
    "sidebarMode": "chat",
    "coworkWebSearchEnabled": true,
    "ccdScheduledTasksEnabled": false
  }
} 

```

3. execute Client.lua


Showcase:
https://streamable.com/3a8mpr
