"""One-shot workspace setup: python3 setup.py <workspace>

Stdlib only (runs under the system python3 before any venv exists). Idempotent — every step prints "ok" or
"skipped (already present)". Creates <ws>/venv with requirements.txt, installs Playwright + chromium into <ws>
when node cannot resolve it (NODE_PATH and an app repo's node_modules count), then says which PDF renderer
manual.py --pdf will use here.
"""
import pathlib, platform, subprocess, sys, venv
import renderers as R

ws = pathlib.Path(sys.argv[1]).expanduser().resolve()
ws.mkdir(parents=True, exist_ok=True)
win = platform.system() == "Windows"
py = ws / "venv" / ("Scripts/python.exe" if win else "bin/python")
npm, npx = ("npm.cmd", "npx.cmd") if win else ("npm", "npx")
run = lambda *cmd, **kw: subprocess.run(cmd, check=True, **kw)


def step(name, present, do):
    if present:
        print(f"{name}: skipped (already present)")
    else:
        do()
        print(f"{name}: ok")


step("venv", py.exists(), lambda: venv.create(ws / "venv", with_pip=True))
deps_ok = subprocess.run([py, "-c", "import pptx, PIL, lxml, defusedxml"], capture_output=True).returncode == 0
step("python packages", deps_ok, lambda: run(py, "-m", "pip", "install", "-q", "-r", R.HERE.parent / "requirements.txt"))
pw_ok = subprocess.run(["node", "-e", "require.resolve('playwright')"], cwd=ws, capture_output=True).returncode == 0


def install_playwright():
    if not (ws / "package.json").exists():  # npm would otherwise walk up and install into a parent project
        (ws / "package.json").write_text('{ "private": true }\n', encoding="utf-8")
    run(npm, "i", "-D", "playwright", cwd=ws)
    run(npx, "playwright", "install", "chromium", cwd=ws)


step("playwright + chromium", pw_ok, install_playwright)
print("pdf renderer:", R.renderer() or "none (PPTX only — install LibreOffice for PDF export)")
