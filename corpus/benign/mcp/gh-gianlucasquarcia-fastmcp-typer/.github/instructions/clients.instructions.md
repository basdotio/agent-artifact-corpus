---
applyTo: "clients/**/*.py"
---

# Client guidelines
- Clients are runnable examples: keep them small, readable, and focused on one transport (HTTP, stdio, Ollama bridge).
- Take server URLs, model names, and similar values from `settings`/environment, not hard-coded literals.
- Close connections via context managers and handle connection errors with clear messages.
- Keep `README.md` project layout in sync when adding a client.
