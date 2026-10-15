# Install and configure

The repository root is the skill. `scripts/install.py` copies the distributable resources into an agent's discovery directory without copying private runtime files. Run it from a downloaded/extracted checkout:

```bash
python3 scripts/install.py
```

On Windows, `py -3 scripts/install.py` runs the same standalone installer. The installer is standard-library-only; native video checks require a regular CPython interpreter, not a free-threaded default selected by `py`. Use `--help` for a custom `--target` or another supported agent. Installation is a local copy, not a paid generation or a ready runtime.

Full processing uses `assets/workflow/`. The supported Windows setup route is WSL2 Ubuntu; run the installation/setup inside the environment where the agent will execute. A Windows Claude install and a WSL Claude install have different home/discovery paths. Do not mix their environments or reuse a virtual environment across OSes.

## Prerequisites

- Main regular CPython >=3.12 and its isolated virtual environment. Free-threaded builds are unsupported by the compiled video wheels.
- Rubber Band CLI for +3-semitone vocal pitch, without changing duration.
- Cloudflared for the launcher's callback-only tunnel, or a configured HTTPS callback.
- Enhancor and Replicate user accounts with valid keys and sufficient credits.
- Mesh only: separate Python 3.12 environment and Google Face Landmarker model.

Detect these before installing anything; do not reinstall working dependencies or install/restart WSL silently. Upstream main pins are in `assets/workflow/requirements.txt`. Use a dedicated environment and report exact install failures instead of substituting untested versions.

Ubuntu/WSL commonly uses `rubberband-cli`, `python3-venv` and `python3-pip`. Cloudflared comes from Cloudflare's official distribution. On macOS, Homebrew supplies Rubber Band, Python and cloudflared. Package-manager commands require the user's system installation scope. See the preserved [upstream setup runbook](../assets/workflow/docs/SETUP-AGENT.md) for platform specifics.

From the installed `assets/workflow/` directory:

```bash
bash setup.sh
bash setup-face-mesh.sh
```

The second command is optional for depth-only use and requires Python 3.12. It sets up the isolated mesh worker and obtains the official face model without hosted inference. Keep `.env` private; setup preserves it if it exists.

Set your own `ENHANCOR_API_KEY` and `REPLICATE_API_TOKEN` in `.env`, following `.env.example`. Optional settings include `HF_TOKEN`, `MEDIA_HOST`, `MEDIA_HOST_FALLBACKS`, `CATBOX_USERHASH`, `ENHANCOR_WEBHOOK_URL` and provider base URL. Never ask for secrets in chat or copy another project's credentials.

## Readiness

Run `scripts/runtime.py doctor` from the skill root. `--require-keys` checks configuration presence, not remote access/balance; `--mesh` additionally checks the worker/model prerequisites. Setup does not generate/upload media.

Start the local UI from `assets/workflow/`:

```bash
bash start.command
```

Default URL is `http://127.0.0.1:8770`. If occupied, use `PORT=8771 bash start.command` and leave unrelated services running. Keep the app and its callback receiver/tunnel running during jobs. The tunnel exposes the callback receiver, not the app or source files. A custom callback must be HTTPS and reachable by the provider.

Check `/health`, the UI and the three companion images. A running UI is different from a generation-ready account. First-use local mesh imports/tracking and authorized live provider requests remain separate checks.

Official links: [WSL](https://learn.microsoft.com/windows/wsl/install), [Python](https://www.python.org/downloads/), [Cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/), [Rubber Band](https://breakfastquay.com/rubberband/), [Enhancor keys](https://app.enhancor.ai/api-dashboard), [Replicate tokens](https://replicate.com/account/api-tokens).
