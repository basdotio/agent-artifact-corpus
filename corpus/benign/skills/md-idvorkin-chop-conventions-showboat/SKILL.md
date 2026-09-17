---
name: showboat
description: Create executable demo documents with screenshots using Showboat + Rodney. Use when the user wants to document an app, create a visual walkthrough, take screenshots of a deployed site, run an accessibility audit, or build self-verifying documentation.
allowed-tools: Bash, Read, Write, Glob, Grep
---

# Showboat - Executable Demo Documents

Create markdown documents that mix commentary, screenshots, and captured command output. These docs are **self-verifying** — `showboat verify` re-runs everything and diffs the output.

## Prerequisites

Install both Go binaries:

```bash
go install github.com/simonw/showboat@latest
go install github.com/simonw/rodney@latest
export PATH="$HOME/go/bin:$PATH"
```

### Chrome Setup

Rodney needs Chrome/Chromium. If none is installed system-wide, use Playwright's:

```bash
ls ~/.cache/ms-playwright/chromium-*/chrome-linux/chrome
export ROD_CHROME_BIN=~/.cache/ms-playwright/chromium-<VERSION>/chrome-linux/chrome
```

If Playwright isn't installed: `npx playwright install chromium --with-deps`

## Workflow

### 1. Start and init

```bash
rodney start
showboat init docs/demo.md "App Walkthrough"
```

### 2. Add Table of Contents

Use `<table>` for TOC grids (GitHub/pandoc sanitize `<div>` styles and `<style>` blocks):

```bash
showboat note docs/demo.md '## Table of Contents

<table><tr>
<td><a href="#home-screen">1. Home Screen</a></td>
<td><a href="#settings-panel">2. Settings Panel</a></td>
</tr></table>

---'
```

### 3. Navigate, screenshot, repeat

Each section gets a nav bar with prev/TOC/next links, then screenshots:

```bash
showboat note docs/demo.md '## Home Screen
<p align="center"><a href="#table-of-contents">📋 TOC</a> · <a href="#settings-panel">Settings →</a></p>'
showboat exec docs/demo.md bash "rodney open https://your-app.example.com"
showboat exec docs/demo.md bash "rodney screenshot -w 1280 -h 720 docs/home.png"
showboat image docs/demo.md docs/home.png
```

For interactions before capturing:

```bash
showboat exec docs/demo.md bash "rodney click 'button[aria-label=Settings]'"
showboat exec docs/demo.md bash "rodney sleep 0.5"
showboat exec docs/demo.md bash "rodney screenshot -w 1280 -h 720 docs/settings.png"
showboat image docs/demo.md docs/settings.png
```

### 4. Accessibility audit

```bash
showboat exec docs/demo.md bash "rodney ax-tree --depth 3"
showboat exec docs/demo.md bash "rodney ax-find --role button"
```

### 5. Add attribution footer

Every walkthrough gets a footer linking to the showboat skill, the current repo, and the current PR (if any). Detect these dynamically:

```bash
# Get repo and PR info
REPO_URL=$(gh repo view --json url -q .url 2>/dev/null)
REPO_NAME=$(basename "$REPO_URL")
PR_NUM=$(gh pr view --json number -q .number 2>/dev/null)
PR_URL=$(gh pr view --json url -q .url 2>/dev/null)

# Build the footer
FOOTER="---
*Generated with [Showboat](https://github.com/idvorkin/chop-conventions/tree/main/skills/showboat) + [Rodney](https://github.com/simonw/rodney)*"

if [ -n "$REPO_URL" ]; then
  FOOTER="$FOOTER | [$REPO_NAME]($REPO_URL)"
fi
if [ -n "$PR_NUM" ]; then
  FOOTER="$FOOTER | [PR #$PR_NUM]($PR_URL)"
fi

showboat note docs/demo.md "$FOOTER"
```

### 6. Clean up and verify

```bash
rodney stop

# Later, to verify the doc still matches:
rodney start
showboat verify docs/demo.md
rodney stop
```

## Serving the Document

Use pandoc + python http.server (avoids grip's GitHub API rate limits). Run from the document's directory so relative image paths resolve.

```bash
cd docs/walk-the-store
pandoc walkthrough.md -o walkthrough.html --standalone \
  --metadata title="Walkthrough Title" \
  --template pandoc-template.html
python3 -m http.server <port> --bind 0.0.0.0
```

The pandoc template is at `skills/showboat/pandoc-template.html` in this repo — copy it to the document directory.

**Anchor ID note:** Pandoc lowercases, removes special chars, replaces spaces with hyphens. Em dashes become single hyphens. Example: `## 3. Featured Post — Eulogy` → `#featured-post-eulogy`.

## Command Reference

### Showboat

| Command                              | Purpose                           |
| ------------------------------------ | --------------------------------- |
| `showboat init <file> <title>`       | Create a new document             |
| `showboat note <file> [text]`        | Add commentary (text or stdin)    |
| `showboat exec <file> <lang> [code]` | Run code, capture output          |
| `showboat image <file> <path>`       | Copy image into document          |
| `showboat pop <file>`                | Remove the most recent entry      |
| `showboat verify <file>`             | Re-run all blocks and diff output |

### Rodney (key commands)

| Command                                  | Purpose                   |
| ---------------------------------------- | ------------------------- |
| `rodney start [--show]`                  | Launch headless Chrome    |
| `rodney stop`                            | Shut down Chrome          |
| `rodney open <url>`                      | Navigate to URL           |
| `rodney screenshot [-w N] [-h N] [file]` | Take screenshot           |
| `rodney screenshot-el <selector> [file]` | Screenshot an element     |
| `rodney click <selector>`                | Click an element          |
| `rodney input <selector> <text>`         | Type into a field         |
| `rodney js <expression>`                 | Run JavaScript            |
| `rodney wait <selector>`                 | Wait for element          |
| `rodney waitstable`                      | Wait for DOM to stabilize |
| `rodney ax-tree [--depth N]`             | Dump accessibility tree   |
| `rodney ax-find [--name N] [--role R]`   | Find accessible nodes     |

## Publishing to Gisthost

[Gisthost](https://gisthost.github.io/) renders HTML gists in the browser. It's Simon Willison's improved fork of gistpreview that handles large files and Substack URL mangling.

**Base technique:** Use the **gist-image** skill to create a gist and push binary images via git. Then apply the gisthost-specific steps below.

### Constraints

- **GitHub API truncates gist files over 1MB** — keep `index.html` under 1MB
- **Gisthost uses `document.write()`** — relative image paths won't resolve. Use absolute raw URLs
- **Gisthost looks for `index.html` by name** — always name your HTML file `index.html`
- **Max 300 files per gist** — split into multiple gists if needed

### Publish Flow

```bash
# 1. Generate HTML from showboat markdown
pandoc walkthrough.md -o index.html --standalone \
  --metadata title="Title" --template pandoc-template.html

# 2. Create PUBLIC gist (gisthost requires public access)
GIST_NAME="showboat-walkthrough"
GIST_URL=$(gh gist create --public --desc "$GIST_NAME" - <<< "# $GIST_NAME" 2>&1 | grep gist.github.com)
GIST_ID=$(basename "$GIST_URL")
GH_USER=$(gh api user --jq '.login')

# 3. Clone gist repo, copy in index.html and screenshots
git clone "$GIST_URL" ".tmp/$GIST_NAME"
cp index.html /path/to/screenshots/*.png ".tmp/$GIST_NAME/"
cd ".tmp/$GIST_NAME"

# 4. Convert screenshots to WebP for smaller size
for png in *.png; do
  name=$(basename "$png" .png)
  magick "$png" -quality 70 "${name}.webp"
done

# 5. Rewrite image src attributes to absolute gist raw URLs
#    (required because gisthost uses document.write())
#    Replace: src="screenshot.png"
#    With:    src="https://gist.githubusercontent.com/$GH_USER/$GIST_ID/raw/screenshot.webp"

# 6. Git add, commit, push, return to project root
git add index.html *.webp
git commit -m "Add walkthrough"
git push
cd -
```

### View the result

```
https://gisthost.github.io/?GIST_ID
```

### Image naming convention

Use numbered, descriptive names that match the walkthrough sections:

```
01-landing.webp
02-user-menu.webp
03-load-demo-data.webp
04-weekly-tracker.webp
```

### Why not `<base href>`?

A `<base>` tag would let you use relative image paths, but gisthost uses `document.write()` which replaces the entire page — the `<base>` tag affects gisthost's own resource resolution and breaks the page. Always use absolute raw URLs.

### Why not base64-embedded images?

Base64 encoding inflates file size ~33%. A walkthrough with 8 screenshots easily exceeds the 1MB API truncation limit. Gisthost handles truncated files via `raw_url` fallback, but keeping files small is more reliable.

## Tips

- **Undo mistakes:** `showboat pop` removes the last entry
- **Viewport size:** `rodney screenshot -w 1280 -h 720` for consistent dimensions
- **Wait for animations:** `rodney sleep 0.5` or `rodney waitstable` before screenshots
- **Element screenshots:** `rodney screenshot-el ".modal"` to capture just a component
- **Selectors:** Prefer `[data-testid=...]` or `[aria-label=...]` for stability
- **Charts:** Use [Chartroom](https://github.com/simonw/chartroom) via `uvx chartroom bar --csv -o chart.png` then `showboat image`
- **Remote viewing:** Set `SHOWBOAT_REMOTE_URL` to stream to a datasette-showboat viewer in real-time
