---
name: browser-scraper
description: Scrape websites using a real Chrome browser with the user's Chrome profile — shares cookies, auth, and fingerprint to bypass bot detection (Cloudflare, Reddit, etc.). Use when scraping sites that block headless browsers or require login, or when asked to "open a browser and scrape", "take a screenshot of a page", "get data from a site that blocks bots", or "scrape with a specific Chrome profile".
---

# Browser Scraper

Scrapes web pages using Playwright with a real Chrome/Chromium binary and an existing user profile. Bypasses bot detection by sharing existing cookies, fingerprint, and session.

## Profiles

The scraper supports multiple Chrome profiles:

- **Default (no `--profile` flag):** Uses the system's default Chrome profile
  - macOS: `~/Library/Application Support/Google/Chrome/Default`
  - Linux: `~/.config/google-chrome/Default`
  - Windows: `%LOCALAPPDATA%\Google\Chrome\User Data\Default`

- **Named profile (`--profile <name>`):** Uses `profiles/<name>/` under the skill directory
  - Create a profile by launching Chrome with `--profile-directory=Profile 1` or similar, then point the scraper at that folder
  - Useful for: isolating logins, avoiding conflicts with your main Chrome session, scraping without auth

## Script

```bash
# Default profile (system Chrome)
node scripts/scrape.mjs <url> [css_selector]

# Named profile (profiles/<name>/)
node scripts/scrape.mjs <url> [css_selector] --profile <name>

# Headless mode (faster, higher block risk)
node scripts/scrape.mjs <url> --headless --profile <name>

# Keep browser open after scraping (for interactive use)
node scripts/scrape.mjs <url> --profile <name> --keep-open

# Extra wait for lazy-loaded content (default: 3000ms)
node scripts/scrape.mjs <url> --profile <name> --wait 6000
```

Run from the skill directory:
```bash
cd ~/.openclaw-yekeen/workspace/skills/browser-scraper/
node scripts/scrape.mjs https://www.reddit.com/
```

## Output

- JSON to stdout: matched elements or page preview
- Screenshot saved to `/tmp/browser-scraper-last.png`

## Key Design

- `channel: 'chrome'` — launches real Chrome when available, falls back to system Chromium
- `launchPersistentContext` with the profile directory
- `--disable-blink-features=AutomationControlled` + `navigator.webdriver` patch
- `headless: false` by default to avoid SingletonLock conflicts

## Requirements

- [Playwright](https://playwright.dev) installed: `npm install playwright`
- Chrome or Chromium installed on the system
- On macOS/Linux: the `channel: 'chrome'` option requires Chrome (not Chromium) to be installed

## Tips

- Chrome must not already be open with the target profile (SingletonLock error). Close Chrome first, or use a named profile to avoid conflicts.
- If you get a `SingletonLock` error with a named profile, delete the `SingletonLock` file in that profile directory and try again.
- Use `--keep-open` to leave the browser open for interactive use after scraping — Ctrl+C to close.
- For sites with lazy-loaded content: use `--wait <ms>` flag or modify the script to increase `waitForTimeout`
- For Reddit: use selector `shreddit-post` and read attributes (`post-title`, `author`, `score`, `permalink`)
- To create a fresh isolated profile: run Chrome from the terminal with `--profile-directory=Profile X` and log in, then point the scraper at that directory