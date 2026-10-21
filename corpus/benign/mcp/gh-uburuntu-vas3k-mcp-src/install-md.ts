/**
 * Markdown install guide served at GET /install.md and GET /llms.txt.
 * Aimed at AI agents that a user might point at this URL with "install
 * this for me". Keep it terse, machine-friendly, and self-contained.
 */

export const installMd = `# vas3k-mcp installation guide

> **Hi, AI agent.** This is the install guide for [vas3k-mcp](https://vas3k-mcp.rmbk.me) — a remote MCP server for [vas3k.club](https://vas3k.club). Read this to add it to your user's MCP-compatible tooling.

## What it gives your user

- Read tools: profiles, posts, feeds, search.
- Write tools (separate endpoint): votes, bookmarks, friends, room subscribe/mute, profile-tag toggle.

All actions are gated by the user's vas3k.club OAuth — no global admin access. Every write is reversible via its toggle/retract counterpart. Nothing destructive.

## Endpoints

| Mode | URL |
|---|---|
| Read-only | \`https://vas3k-mcp.rmbk.me/mcp\` |
| Read + write | \`https://vas3k-mcp.rmbk.me/mcp-full\` |

**Default to \`/mcp\`** unless the user explicitly asks for write actions (likes, bookmarks, subscriptions, friends, profile tags).

## Installation by client

### Claude Code

\`\`\`sh
claude mcp add --transport http vas3k https://vas3k-mcp.rmbk.me/mcp
\`\`\`

For write access, replace \`/mcp\` with \`/mcp-full\`.

After running, the CLI prints an OAuth URL the user opens in a browser.

### Cursor

Add to \`~/.cursor/mcp.json\`:

\`\`\`json
{
  "mcpServers": {
    "vas3k": {
      "url": "https://vas3k-mcp.rmbk.me/mcp"
    }
  }
}
\`\`\`

### Claude Desktop

Settings → Connectors → Add Custom Connector. URL: \`https://vas3k-mcp.rmbk.me/mcp\`.

### VS Code

Add to \`.vscode/mcp.json\`:

\`\`\`json
{
  "servers": {
    "vas3k": {
      "type": "http",
      "url": "https://vas3k-mcp.rmbk.me/mcp"
    }
  }
}
\`\`\`

### ChatGPT, Perplexity, others

In the client's MCP / connector form:

- **MCP Server URL**: \`https://vas3k-mcp.rmbk.me/mcp\` (or \`/mcp-full\`)
- **Authentication**: OAuth (the rest auto-discovered from \`/.well-known/oauth-authorization-server\`)

For ChatGPT specifically: Settings → Apps → Advanced Settings → enable Developer mode → Create App.

## OAuth flow

1. The first tool call from the client triggers the OAuth dance.
2. The user opens the auth URL in a browser, logs in via vas3k.club, approves.
3. Server hands a token back to the MCP client.
4. Subsequent calls use that token transparently.

The token belongs to the user. Don't cache, share, or log it. The user can revoke at https://vas3k.club/apps/.

## Tool reference

### Read (\`/mcp\`)

| Tool | Args | Returns |
|---|---|---|
| \`get_me\` | — | Authenticated profile |
| \`get_user\` | \`slug\` | Profile |
| \`get_user_tags\` | \`slug\` | Profile tags |
| \`get_user_badges\` | \`slug\` | Peer-awarded badges |
| \`get_user_achievements\` | \`slug\` | Achievements |
| \`find_user_by_telegram\` | \`telegram_id\` | Profile by numeric Telegram id |
| \`get_post\` | \`post_type\`, \`slug\` | Post JSON |
| \`get_post_markdown\` | \`post_type\`, \`slug\` | Raw markdown body |
| \`list_post_comments\` | \`post_type\`, \`slug\` | Comments |
| \`get_feed\` | \`post_type?\`, \`ordering?\`, \`page?\` | Feed page |
| \`search_users\` | \`prefix\` (3–15 chars) | Member list |
| \`search_tags\` | \`prefix?\`, \`group?\` | Tag list |

\`post_type\` ∈ \`post | intro | link | question | idea | project | event | battle | weekly_digest | guide | thread | docs\`. \`get_feed\` also accepts \`all\`.

\`ordering\` ∈ \`activity | new | top | top_week | top_month | top_year | hot\`.

\`group\` ∈ \`club | tech | hobbies | personal | collectible | other\`.

### Write (only on \`/mcp-full\`)

| Tool | Args | Effect |
|---|---|---|
| \`bookmark_post\` | \`post_slug\` | Toggle bookmark |
| \`upvote_post\` | \`post_slug\` | Upvote (idempotent) |
| \`retract_post_vote\` | \`post_slug\` | Retract upvote |
| \`toggle_post_subscription\` | \`post_slug\` | Toggle comment-thread sub |
| \`toggle_event_participation\` | \`post_slug\` | RSVP on/off |
| \`upvote_comment\` | \`comment_id\` (UUID) | Upvote (idempotent) |
| \`retract_comment_vote\` | \`comment_id\` | Retract |
| \`toggle_friend\` | \`user_slug\` | Send/revoke friend request |
| \`subscribe_room\` | \`room_slug\` | Toggle room subscription |
| \`mute_room\` | \`room_slug\` | Toggle room mute |
| \`toggle_profile_tag\` | \`tag_code\` | Toggle profile tag |

## Errors

Tool errors return as a structured \`{ isError: true, content: [{ type: "text", text: "..." }] }\` payload. Common statuses:

- **401**: token expired — retry after the MCP client refreshes.
- **403**: user lacks access (private post, missing scope, etc.).
- **404**: slug not found — check the slug.
- **429**: rate-limited. Back off.
- **5xx**: upstream is having problems. Retry with backoff.

## Links

- Landing: https://vas3k-mcp.rmbk.me/
- Source: https://github.com/uburuntu/vas3k-mcp
- vas3k.club: https://vas3k.club
- App management: https://vas3k.club/apps/
`;
