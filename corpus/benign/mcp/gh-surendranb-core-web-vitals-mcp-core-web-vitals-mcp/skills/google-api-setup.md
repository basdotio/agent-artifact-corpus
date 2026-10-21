# Google API Key Setup & Free Quota Guide

This guide walks you through acquiring, configuring, and troubleshooting a free Google API Key for Core Web Vitals (CrUX and PageSpeed Insights).

Official Google Documentation: [PageSpeed Insights API - Get Started (API Key)](https://developers.google.com/speed/docs/insights/v5/get-started#APIKey)

---

## 1. Do You Need an API Key?

- **PageSpeed Insights (`audit_pagespeed`)**: 
  - **Works without an API key!** Out of the box, you can run synthetic Lighthouse lab audits with zero configuration.
  - Adding a free API key raises your daily limit to **25,000 queries per day**.
- **Chrome UX Report (`get_crux_metrics`, `get_crux_history`)**: 
  - **Requires a free API key.** Google requires all callers requesting real Chrome user field data (28-day rolling window) to identify themselves.
  - Quota is **150 queries per minute** per project (completely free).

---

## 2. Step-by-Step: Get Your Free API Key in 2 Minutes

1. **Open Google Cloud Console**:
   Navigate to [Google Cloud Console Credentials](https://console.cloud.google.com/apis/credentials).
   *(If you don't have a Google Cloud account, signing in with your regular Google account gives you immediate free access.)*

2. **Select or Create a Project**:
   Click the project dropdown in the top bar and click **New Project** (e.g. named `Web-Vitals-Audits`).

3. **Enable Required APIs**:
   You must enable the two APIs in the API Library:
   - [Enable PageSpeed Insights API](https://console.cloud.google.com/apis/library/pagespeedonline.googleapis.com) -> Click **Enable**.
   - [Enable Chrome UX Report API](https://console.cloud.google.com/apis/library/chromeuxreport.googleapis.com) -> Click **Enable**.

4. **Generate the Key**:
   - Go to **APIs & Services** > **Credentials**.
   - Click **+ Create Credentials** at the top and select **API key**.
   - Your new API key (starts with `AIzaSy...`) will appear on screen. Click **Copy**.

5. *(Recommended)* **Restrict the Key**:
   - In the API key dialog, click **Edit API key**.
   - Under **API restrictions**, select **Restrict key** and check:
     - `Chrome UX Report API`
     - `PageSpeed Insights API`
   - Click **Save**.

---

## 3. Configuring the Key in Your MCP Client

You can provide the key using any of the following methods:

### Option A: Environment Variable (Recommended)
Add to your shell profile (`~/.zshrc` or `~/.bashrc`):
```bash
export GOOGLE_API_KEY="AIzaSyYourSecretKeyHere"
```
Or use `CRUX_API_KEY`:
```bash
export CRUX_API_KEY="AIzaSyYourSecretKeyHere"
```

### Option B: Claude Desktop Configuration
Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "core-web-vitals": {
      "command": "uvx",
      "args": ["core-web-vitals-mcp"],
      "env": {
        "GOOGLE_API_KEY": "AIzaSyYourSecretKeyHere"
      }
    }
  }
}
```

### Option C: Cursor / Cline / Claude Code Config
Add to your MCP server configuration:
```json
{
  "mcpServers": {
    "core-web-vitals": {
      "command": "npx",
      "args": ["-y", "core-web-vitals-tools-mcp"],
      "env": {
        "GOOGLE_API_KEY": "AIzaSyYourSecretKeyHere"
      }
    }
  }
}
```

### Option D: Direct Tool Argument
Pass directly to any tool call:
```json
{
  "url": "https://example.com",
  "api_key": "AIzaSyYourSecretKeyHere"
}
```

---

## 4. Free Usage Limits & Built-in Throttling

| Service | Free Quota | Built-in Client Throttling |
|---|---|---|
| **PageSpeed Insights (Keyless)** | Shared public IP pool | 1 request every 1.5s + 5-min cache |
| **PageSpeed Insights (With Key)** | 25,000 queries / day | 1 request every 0.5s + 5-min cache |
| **Chrome UX Report (CrUX)** | 150 queries / min | 1 request every 0.4s + 15-min cache |

The MCP server automatically throttles outbound queries and caches repeated results so your AI agent does not hit Google's 429 rate limits.

---

## 5. Troubleshooting Common Errors

### Error: `HTTP 403: Method doesn't allow unregistered callers`
- **Cause**: Querying CrUX (`get_crux_metrics` or `get_crux_history`) without an API key.
- **Fix**: Set `GOOGLE_API_KEY` following Section 2 above. When keyless, `core-web-vitals-mcp` automatically provides lab Core Web Vitals via PageSpeed Insights instead.

### Error: `HTTP 400: API key not valid`
- **Cause**: The key passed in `api_key` or `GOOGLE_API_KEY` is invalid or mistyped.
- **Fix**: Re-copy the key from Google Cloud Console Credentials.

### Error: `HTTP 429: Quota exceeded for 'Queries per day'`
- **Cause**: Unauthenticated public PageSpeed IP limit reached.
- **Fix**: Generate and configure a free Google API key as described above to get your dedicated 25,000 queries/day allowance.
