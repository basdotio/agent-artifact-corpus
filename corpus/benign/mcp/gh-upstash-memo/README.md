# Memo MCP

An MCP server that saves and retrieves AI conversation context. Hand off conversations between AI agents seamlessly. Free and no account required.

## What it does

When you're working with an AI agent and need to:

- **Switch agents** - Claude can't fix your bug? Try Cursor or Copilot with dense context
- **Continue later** - Save progress and pick up where you left off
- **Move machines** - Start on laptop, continue on desktop

Just say `memo set` and the agent will save structured context (goal, completed tasks, pending tasks, decisions, relevant files). Get a short ID back, use `memo get <id>` anywhere to restore context.



https://github.com/user-attachments/assets/f96798e1-2f8b-4de3-9431-b7bc52c58dfa



## Installation

### Claude Code

```bash
claude mcp add memo -- npx -y @upstash/memo
```

### OpenCode

Add to your `opencode.json`:

```json
{
  "mcp": {
    "memo": {
      "type": "local",
      "command": ["npx", "-y", "@upstash/memo"]
    }
  }
}
```

### Claude Desktop / Cursor

Add to your MCP config:

```json
{
  "mcpServers": {
    "memo": {
      "command": "npx",
      "args": ["-y", "@upstash/memo"]
    }
  }
}
```

## Usage

### Save context

```
memo set
```

The AI will summarize the conversation and return an ID like `4tJ630XqhCV5gQelx98pu`.

### Restore context

```
memo get 4tJ630XqhCV5gQelx98pu
```

The AI will load the previous context and continue where you left off.

## What gets saved

When you run `memo set`, the agent stores a structured snapshot, for example:

- Goal
- Completed tasks
- Pending tasks
- Key decisions
- Relevant files (paths only) or references

This keeps restored conversations focused and avoids reloading raw chat history.

## Security

Your conversation context is stored in Upstash Redis with encryption enabled at rest and in transit. Data expires automatically after 24 hours (configurable via `--ttl-mins`).

If you prefer full control over your data, you can self-host both the API and storage using your own infrastructure. See the Self-hosting section below.

## Self-hosting

The repo includes both the MCP server and the API. To self-host:

### 1. Set up environment

Create a `.env` file with your Upstash Redis credentials:

```
UPSTASH_REDIS_REST_URL=your-redis-url
UPSTASH_REDIS_REST_TOKEN=your-redis-token
```

### 2. Run locally

```bash
npx vercel dev
```

### 3. Deploy to Vercel

```bash
vercel
```

Set the same environment variables in your Vercel project settings.

### 4. Point MCP to your API

The MCP server uses `https://memo-upstash.vercel.app` by default. To use your own API, modify `index.ts`:

```typescript
const GET_URL = "https://your-api.vercel.app/api/get";
const SET_URL = "https://your-api.vercel.app/api/set";
```

## Options

### `--ttl-mins`

Set expiration time in minutes. Default is 1440 (24 hours).

```json
{
  "mcpServers": {
    "memo": {
      "command": "npx",
      "args": ["-y", "@upstash/memo", "--ttl-mins", "4320"]
    }
  }
}
```

## License

MIT
