# youtube-transcript-mcp

A simple [MCP](https://modelcontextprotocol.io/) server that lets LLMs easily get the transcript of YouTube videos.

## To install

Add this to your LLM app's MCP settings:

```json
{
  "mcpServers": {
    "youtube-transcript": {
      "command": "bunx",
      "args": ["--bun", "-y", "youtube-transcript-mcp"]
    }
  }
}
```

If you prefer node to bun, you can use `npx` instead:

```json
{
  "mcpServers": {
    "youtube-transcript": {
      "command": "npx",
      "args": ["-y", "youtube-transcript-mcp"]
    }
  }
}
```

## To use

Just ask your LLM about a YouTube video:

> Summarize this video: https://www.youtube.com/watch?v=dQw4w9WgXcQ

> What are the three key points of this video? https://www.youtube.com/watch?v=dQw4w9WgXcQ

> What are some counterpoints to this argument here? https://www.youtube.com/watch?v=dQw4w9WgXcQ
