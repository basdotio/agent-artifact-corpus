# Namecheap MCP

> Check domain availability across 600+ TLDs on Namecheap without leaving Claude

Ask Claude to check domains conversationally and get instant results with purchase links.

---

## Installation

```bash
npx @birdmania1/namecheap-mcp
```

**⚠️ IMPORTANT:** After installing, you MUST configure your Namecheap API credentials (see Setup below). The MCP won't work without them.

---

## Setup (3 minutes)

Copy-paste these commands to Claude **one at a time** and follow the steps:

---

### Step 1: Get Your IP Address

**Say to Claude:**
```
Visit https://api.ipify.org and tell me my IP address
```

Claude will tell you your IP. **Write it down** - you'll need it in steps 2 and 3.

---

### Step 2: Enable Namecheap API

**Do these steps manually in your browser:**

1. Go to https://www.namecheap.com and log in
2. Click **Profile (top right) → Tools → Namecheap API Access**
3. Click **"Enable API Access"**
4. Under **Whitelisted IPs**, click **"Add New"** and paste your IP from Step 1
5. **Copy your API key** - you'll need it in Step 3

---

### Step 3: Configure Claude Code

**Say to Claude:**
```
Add the Namecheap MCP server to my Claude Code config with these credentials:
- API User: [your namecheap username]
- API Key: [the key you just copied]
- Username: [your namecheap username]
- Client IP: [the IP from step 1]

Use this exact MCP server config:

{
  "command": "npx",
  "args": ["-y", "@birdmania1/namecheap-mcp"],
  "env": {
    "NAMECHEAP_API_USER": "your_username",
    "NAMECHEAP_API_KEY": "your_api_key_here",
    "NAMECHEAP_USERNAME": "your_username",
    "NAMECHEAP_CLIENT_IP": "your.ip.address.here"
  }
}

Important:
1. Add it to the SAME config file where your other MCP servers are (check where perplexity/github/etc are configured)
2. Make sure "namecheap" only appears in ONE config file (not duplicated across ~/.claude.json, settings.json, or mcp.json)
3. If you get errors, check for duplicate entries and remove them
```

**Important:** Replace the placeholder values with your actual credentials before sending to Claude.

---

### Step 4: Restart Claude Code

Fully quit Claude Code (⌘+Q on Mac, Alt+F4 on Windows) and reopen it.

---

### Step 5: Test It

**Say to Claude:**
```
Check if example.com and startup.io are available
```

You should get instant results with prices and purchase links!

If it doesn't work, see [Troubleshooting](#troubleshooting) below.

---

## What You Can Do

**Find startup names:**
```
"I'm building a SaaS for restaurants. Help me find a domain."
```

**Check specific domains:**
```
"Check if myapp.com, myapp.io, and myapp.ai are available"
```

**Find alternatives:**
```
"example.com is taken. Find me similar domains."
```

**Research TLDs:**
```
"Check if any single-word domains are available in .ai"
```

---

## Features

- **600+ TLDs** — .com, .io, .ai, .xyz, .tech, and more
- **Batch checking** — Check 100 domains at once
- **Instant pricing** — See costs upfront
- **Purchase links** — One-click to buy
- **Secure** — Direct API, no proxy server

---

## Troubleshooting

**"Invalid request IP" error:**
- Your IP changed. Update it in Namecheap's whitelist.
- Ask Claude "What's my IP?" to get your current IP.

**"API access not enabled":**
- Enable it in your Namecheap account settings.

**Not showing up in Claude:**
- Check for duplicate entries: "namecheap" should only appear in ONE config file
- Common locations: `~/.claude.json`, `~/.claude/settings.json`, `~/.claude/mcp.json`
- Remove duplicates, keeping only the one in the file where your other MCPs live
- Restart Claude Code after editing (full quit and reopen)
- Verify JSON is valid (no trailing commas, proper nesting)

---

## License

MIT

**Made by developers tired of tab-switching**
