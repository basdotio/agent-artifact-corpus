# MCP Server Usage

This repository now includes an MCP (Model Context Protocol) server that exposes the now playing functionality as a tool.

## MCP Server Features

The MCP server provides a single tool:

- **`now_playing`**: Returns currently playing song information from music players

## Running the MCP Server

### Prerequisites

1. Install dependencies:
   ```bash
   uv sync
   ```

2. On Windows, ensure you have music players running (Spotify, QQMusic, NeteaseMusic)

### Starting the Server

Run the MCP server:

```bash
uv run mcp_server.py
```

The server will run on stdio and communicate using the MCP protocol.


## MCP Client Configuration

To use this server with an MCP client, add the following configuration:

```json
{
  "mcpServers": {
    "now-playing": {
      "command": "uv",
      "args": ["run", "mcp_server.py"],
      "cwd": "/path/to/NowPlayingAPI"
    }
  }
}
```

## Platform Support

- **Windows**: Full functionality with actual music player detection

> MacOS/Linux currently not supported.

## Tool Schema

### now_playing

**Description**: Get currently playing song information from music players

**Input**: No parameters required

**Output**: Text response with currently playing songs, formatted as:
```
Currently playing:
🎵 Artist - Song Title (from spotify.exe)
🎵 Another Song - Artist (from qqmusic.exe)
🎵 One More Song - Artist (from cloudmusic.exe)
```

If no music is playing, returns: "No music is currently playing."
