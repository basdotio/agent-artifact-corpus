---
name: restart-vite-when-needed
description: Always restart the Vite frontend dev server after making frontend changes. Run the restart script from project root; never tell the user to restart manually.
---

# Restart Vite Dev Server

Run from the **project root** after any frontend changes:

```bash
./restart-frontend.sh
```

## When to restart (always after frontend changes)

- Any changes under `frontend/` (React, config, .env, proxy, etc.).
- Changes to `vite.config.ts`, `.env`, or proxy settings.
- User says the frontend or Vite needs a restart.

## Fallback

If `restart-frontend.sh` does not exist but `run-frontend.sh` does, stop Vite (`lsof -ti:5173 | xargs kill` or `pkill -f "vite"`) then run `./run-frontend.sh`.

## Important

- Never say "restart the frontend" without actually running the script.
- Run from the project root so relative paths resolve correctly.
