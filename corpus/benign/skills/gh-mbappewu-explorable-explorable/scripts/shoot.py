"""Screenshot every <figure> of an explorable page, and report console errors.

Usage: python3 shoot.py URL OUT_DIR [--dark] [--width 760] [--lang zh]
Needs: pip install playwright && playwright install chromium
"""
import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("url")
ap.add_argument("out")
ap.add_argument("--dark", action="store_true")
ap.add_argument("--width", type=int, default=760)
ap.add_argument("--lang", default=None)
ap.add_argument("--wait", type=int, default=1200, help="ms to let each figure animate before the shot")
a = ap.parse_args()

out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
url = a.url + (("&" if "?" in a.url else "?") + f"lang={a.lang}" if a.lang else "")
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(args=["--use-gl=angle", "--enable-webgl", "--ignore-gpu-blocklist"])
    page = browser.new_page(viewport={"width": a.width, "height": 900}, device_scale_factor=2,
                            color_scheme="dark" if a.dark else "light")
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(500)
    overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
    figs = page.locator("figure")
    n = figs.count()
    for i in range(n):
        f = figs.nth(i)
        f.scroll_into_view_if_needed()
        page.wait_for_timeout(a.wait)
        name = f.get_attribute("id") or f"figure-{i + 1}"
        f.screenshot(path=str(out / f"{i + 1:02d}-{name}.png"))
    browser.close()

print(f"{n} figures -> {out}")
print("horizontal overflow:", overflow)
print("console errors:", len(errors))
for e in errors[:10]:
    print("  ", e)
sys.exit(1 if errors or overflow else 0)
