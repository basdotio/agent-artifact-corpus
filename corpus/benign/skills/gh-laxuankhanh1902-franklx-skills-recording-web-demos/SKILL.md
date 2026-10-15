---
name: recording-web-demos
description: Use when asked to record, film or screencast a demo or walkthrough of a web UI as a video (mp4, webm), with captions, subtitles, a transcript, narration text or step labels — for any app reachable in a browser, local or remote.
---

# Recording web demos

## Overview
Works on any page Chromium can open — local dev server, staging, a public site, a `file://` page.
A demo video is a **Playwright script** (the storyboard) driving a real browser under
`recordVideo`, with a fake cursor, click ripples and captions injected into every page, then
re-encoded to H.264 by ffmpeg. The captions are logged with timestamps, so the same run writes
`<name>.srt`, `.vtt` and a readable `.md` transcript that match the video exactly.

`demo-kit.js` (beside this file) does all of that. You write only the storyboard.

## Setup (once per project)
```bash
cp ~/.claude/skills/recording-web-demos/demo-kit.js <project>/demo/
npm install -D playwright && npx playwright install chromium
# mp4 needs ffmpeg with libx264: brew install ffmpeg, or npm i -D ffmpeg-static, or FFMPEG=/path
```
Output in `out/`: `<name>.mp4`, `.srt`, `.vtt`, `.md`; on failure `<name>.failure.png`.

## Workflow
1. **Know the UI before scripting.** Read the frontend source or open it with the Playwright MCP
   (`browser_snapshot`) to get stable selectors: roles/labels first (`getByRole`, `getByLabel`),
   ids next, text last. Write the storyboard as a list of steps: caption + action + what proves
   the step happened.
2. **Write `demo/record.js`** (template below). The app's server: start it from the script with
   `d.server(cmd, args, /url regex/)` on a free port — it is killed when recording ends. The script
   builds nothing; say so in its header comment, with the build command.
3. **Run** `node demo/record.js`. Fix any `ERR` (look at `failure.png`), re-run.
4. **Verify by looking**: `ffprobe` the duration, then extract a frame inside 2–3 cues
   (`ffmpeg -ss <cue start+1> -i out/x.mp4 -frames:v 1 f.png`) and read them. A video is not done
   until you have seen a caption on screen over the right page.

## Storyboard template
```js
const kit = require('./demo-kit');
kit.run({ out: __dirname + '/out', name: 'acme-demo', title: 'Acme demo', accent: '#4f8cff' }, async d => {
  const s = await d.server('npm', ['run', 'preview', '--', '--port', '4173'], /(http:\/\/localhost:\d+)/);
  await d.card({ brand: 'Acme', title: 'Invoices in one minute', pills: ['local', 'no signup'] }, 6000);
  await d.goto(s.match[1], 'form#login');
  await d.lead('Step 1 · Sign in', 'Any user works on the demo data.');   // caption, then action
  await d.type(d.page.getByLabel('Email'), 'demo@acme.test');
  await d.click(d.page.getByRole('button', { name: 'Sign in' }));
  await d.page.waitForSelector('.dashboard', { timeout: 60000 });         // real condition, not a sleep
  const total = (/(\d+) invoices/.exec(await d.text()) || [])[1];
  await d.say('Step 2 · Dashboard', (total || 'All') + ' invoices, read off the page.');  // caption, read time
  await d.card({ title: 'Try it', terminal: ['$ npm start'] }, 6000);
});
```

## API (`d.`)
| call | does |
|---|---|
| `say(step, html, extraMs?)` | caption, then waits its reading time (58 ms/char, ≥3 s) |
| `lead(step, html, ms=1600)` | caption, short beat; the next actions play under it |
| `clear()` | hide caption |
| `card({brand,title,lines,terminal,pills,meta,titleSize}, ms)` | full-screen title/end card |
| `goto(url, waitForSelector?)` · `click(loc, {dx})` · `type(loc, text)` | visible-cursor actions |
| `point(loc)` | decorative hover — skipped, never fatal, if missing |
| `scroll(dy, ms)` · `scrollTop()` · `wait(ms)` · `text()` | |
| `server(cmd, args, readyRegex)` | start a process, resolve on the match, kill at end |
| `page`, `ctx` | raw Playwright when needed |

Options: `width/height` (1440×900), `accent`, `captionBg`, `cardBg`, `trim` (0.5 s), `msPerChar`,
`embedSubtitles` (soft subtitle track in the mp4), `headless`, `context` (extra `newContext` opts).

## Rules that keep a demo honest and re-runnable
- **Numbers in captions are read off the page** (`d.text()` + regex), never typed in — the data
  moves between runs and a hardcoded figure turns into a false claim.
- **Mask secrets** shown on cards or in URLs (tokens, passwords) before they reach a frame.
- **Wait on conditions** for anything slow (`waitForSelector`, `waitForFunction`), with a generous
  timeout; fixed sleeps are only for pacing the viewer.
- **`click` for steps that must happen, `point` for decoration** — a missing must-step should fail
  the run, a missing hover should not.
- Captions are short outcomes ("what the viewer should notice"), one idea each; `<code>` and `<b>`
  render.

## Common mistakes
| symptom | fix |
|---|---|
| WebM only, "no ffmpeg with libx264" | install ffmpeg / `ffmpeg-static`, or set `FFMPEG` |
| `require('playwright')` not found | kit was not copied into the project, or Playwright not installed there |
| first second is a white frame | raise `trim` |
| caption covers the element being clicked | `scroll` it up first, or `clear()` before the action |
| page shows stale state / second run differs | a server left from a previous run — let `d.server` own it |
| app needs a login (SSO, 2FA, captcha) | sign in once by hand, `ctx.storageState({path:'auth.json'})`, then `context: { storageState: 'auth.json' }` |
| no cursor/caption inside an iframe or a popup window | the overlay lives in the top page; record the iframe's own URL, or keep the action in the main page |
| native file picker / OS dialog not in the video | they are outside the page — use `setInputFiles` and caption what was chosen |
