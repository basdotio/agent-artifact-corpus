#!/usr/bin/env python3
"""Seed and verify the mailbox logins that the scheduled warm-up run will use.

A scheduled run has no access to the user's normal browser, so it drives its own Playwright
profile. The user signs in once, by hand, into THAT profile; the session persists there and
every later run reuses it.

    seed_login.py list
    seed_login.py seed gmail
    seed_login.py seed https://mail.example.com --name work
    seed_login.py check                 # every seeded provider
    seed_login.py check gmail

Signed-in status is decided by loading the mailbox and reading the final URL, never by
looking for a cookie. Auth cookies outlive the session they belong to, so a cookie test
reports a mailbox as signed in while it is redirecting to a login form - which is exactly
how a warm-up can log sends it never made.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROFILE = Path(os.environ.get("EMAILWARM_PROFILE", Path.home() / ".emailwarm/browser-profile"))
STATE = PROFILE.parent / "providers.json"

PROVIDERS = {
    "gmail":    "https://mail.google.com/mail/u/0/#inbox",
    "outlook":  "https://outlook.live.com/mail/0/",
    "office365": "https://outlook.office.com/mail/",
    "yahoo":    "https://mail.yahoo.com/d/folders/1",
    "aol":      "https://mail.aol.com/",
    "icloud":   "https://www.icloud.com/mail/",
    "proton":   "https://mail.proton.me/u/0/inbox",
    "zoho":     "https://mail.zoho.com/zm/",
    "fastmail": "https://app.fastmail.com/mail/Inbox",
    "gmx":      "https://www.gmx.com/",
}

# Which reputation system a consumer address actually belongs to. The address gives no hint,
# and warming the wrong system teaches you nothing about where your mail is going: sky.com
# and btinternet.com are Yahoo, so an AOL or Yahoo mailbox is what tests them.
CONSUMER_STACKS = {
    "yahoo": ("yahoo.com", "yahoo.co.uk", "ymail.com", "aol.com", "sky.com", "btinternet.com",
              "rocketmail.com"),
    "microsoft": ("hotmail.com", "hotmail.co.uk", "outlook.com", "live.com", "msn.com"),
    "google": ("gmail.com", "googlemail.com"),
    "apple": ("icloud.com", "me.com", "mac.com"),
}
# A final URL containing any of these means the mailbox bounced us to authentication.
SIGNED_OUT = ("login", "signin", "sign-in", "challenge", "auth", "account/", "oauth", "logon")

# Where a SIGNED-IN mailbox actually lives. "Not a login page" is not the same as "in the
# mailbox": a signed-out Outlook redirects to microsoft.com's product page, which contains
# none of the words above and so passed as signed in. Landing anywhere other than the
# mailbox itself - marketing page, help centre, interstitial - means no usable session.
MAILBOX_URLS = {
    # Match the mailbox HOST, not a path. Webmail paths change with every redesign - AOL's
    # inbox is /f/today today and was /d/folders before - and a stale path here reports a
    # perfectly good session as signed out. The host is the stable part, and it is enough:
    # a signed-out Outlook lands on microsoft.com, a signed-out AOL on login.aol.com, both
    # different hosts.
    "gmail": ("mail.google.com",),
    "outlook": ("outlook.live.com", "outlook.com/mail"),
    "office365": ("outlook.office.com", "outlook.office365.com"),
    "yahoo": ("mail.yahoo.com",),
    "aol": ("mail.aol.com",),
    "icloud": ("icloud.com/mail",),
    "proton": ("mail.proton.me",),
    "zoho": ("mail.zoho.com",),
    "fastmail": ("app.fastmail.com",),
    "gmx": ("navigator-bs.gmx.com", "gmx.com/mail"),
}


IS_WINDOWS = sys.platform.startswith("win")


def _alive(pid: str) -> bool:
    """Is this pid a running process?

    os.kill(pid, 0) is the usual trick and it is NOT safe on Windows: there, os.kill with a
    signal other than CTRL_C_EVENT/CTRL_BREAK_EVENT calls TerminateProcess, so the liveness
    probe would kill the very process it is asking about. Windows gets tasklist instead.
    """
    try:
        pid_i = int(pid)
    except ValueError:
        return False
    if IS_WINDOWS:
        try:
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid_i}", "/NH"],
                                 capture_output=True, text=True, timeout=10).stdout
        except (OSError, subprocess.TimeoutExpired):
            return True  # cannot tell; assume alive rather than deleting a live lock
        return str(pid_i) in out
    try:
        os.kill(pid_i, 0)
        return True
    except OSError:
        return False


def _holding_profile() -> list[str]:
    """Pids of browsers using this profile, on whichever platform we are on."""
    if IS_WINDOWS:
        # PowerShell rather than wmic: wmic is deprecated and is absent from recent Windows
        # 11 builds, so a wmic call returns nothing and every lock looks stale.
        # -like treats [ and ] as wildcard syntax, and ' ends the string, so all three are
        # escaped rather than trusting the path to be tidy.
        profile = (str(PROFILE).replace("'", "''")
                   .replace("[", "`[").replace("]", "`]"))
        script = ("Get-CimInstance Win32_Process | "
                  f"Where-Object {{ $_.CommandLine -like '*user-data-dir={profile}*' }} | "
                  "ForEach-Object {{ $_.ProcessId }}").replace("{{", "{").replace("}}", "}")
        try:
            out = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                                 capture_output=True, text=True, timeout=20).stdout
        except (OSError, subprocess.TimeoutExpired):
            return []
        return [ln.strip() for ln in out.splitlines() if ln.strip().isdigit()]
    try:
        out = subprocess.run(["pgrep", "-f", f"user-data-dir={PROFILE}"],
                             capture_output=True, text=True, timeout=10).stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        return []
    return out


def clear_stale_lock() -> None:
    """Remove a singleton lock only when nothing is actually holding the profile.

    A killed browser leaves the lock behind and every later run dies on it. Deleting a LIVE
    lock instead corrupts the very session this profile exists to hold, so the check is not
    optional. Note that pgrep matches its own command line, hence the explicit filter.
    """
    locks = [PROFILE / n for n in ("SingletonLock", "SingletonCookie", "SingletonSocket")]
    if not any(p.exists() or p.is_symlink() for p in locks):
        return
    out = _holding_profile()
    live = []
    for pid in out:
        # Confirm the process is REALLY alive and really ours. A pid pgrep listed a moment
        # ago can already be gone, and calling a dead one live means refusing to clear a
        # stale lock - after which Chrome hands off to a session that no longer exists and
        # the launch dies with "Opening in existing browser session".
        if not _alive(pid):
            continue
        if IS_WINDOWS:
            live.append(pid)  # already matched on the profile path by _holding_profile
            continue
        try:
            cmd = subprocess.run(["ps", "-p", pid, "-o", "command="],
                                 capture_output=True, text=True, timeout=5).stdout
        except (OSError, subprocess.TimeoutExpired):
            continue
        if "pgrep" not in cmd and str(PROFILE) in cmd and "chrome" in cmd.lower():
            live.append(pid)
    if live:
        print(f"profile is in use by pid(s) {', '.join(live)} - not touching the lock")
        return
    for p in locks:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
    print("cleared a stale browser lock")


def window_size() -> tuple[int, int]:
    """A window the user can actually work in, sized to their screen.

    Playwright defaults to a fixed 1280x720 viewport that does not follow the window, so
    sign-in dialogs get clipped and the buttons the user needs sit off-screen. Seeding is
    the one step that is entirely manual, so the window has to behave like a normal browser.
    """
    if IS_WINDOWS:
        try:
            import ctypes

            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            w, h = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
            if w > 400 and h > 400:
                return max(1100, w - 80), max(700, h - 120)
        except Exception:  # noqa: BLE001 - fall through to the default size
            pass
    if sys.platform == "darwin":
        try:
            out = subprocess.run(
                ["osascript", "-e", "tell application \"Finder\" to get bounds of window of desktop"],
                capture_output=True, text=True, timeout=10).stdout.strip()
            parts = [int(x) for x in out.replace(" ", "").split(",")]
            if len(parts) == 4 and parts[2] > 400 and parts[3] > 400:
                return max(1100, parts[2] - 80), max(700, parts[3] - 80)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
    return 1440, 900


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


INSTALL_HINT = (
    "Playwright needs its browser binary, which is separate from the python package:\n"
    f"  {sys.executable} -m pip install playwright\n"
    f"  {sys.executable} -m playwright install chromium\n"
    "Whichever interpreter runs these scripts must be the one with the browser installed, "
    "and the scheduled job has to use that same interpreter."
)


def _playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright is not installed.\n" + INSTALL_HINT)
    return sync_playwright


def _browser_missing(exc: Exception) -> bool:
    """A missing browser build is a setup problem, not a signed-out mailbox.

    Reporting it as "SIGNED OUT" would send the user off re-seeding logins that are
    perfectly fine, so it gets its own message.
    """
    text = str(exc)
    return "Executable doesn't exist" in text or "playwright install" in text


def verify(name: str, url: str, headless: bool = True) -> tuple[bool, str]:
    """Load the mailbox and report where we actually ended up."""
    clear_stale_lock()
    sync_playwright = _playwright()
    with sync_playwright() as p:
        try:
            ctx = p.chromium.launch_persistent_context(
                str(PROFILE), headless=headless,
                viewport={"width": 1440, "height": 900} if headless else None,
                no_viewport=not headless)
        except Exception as exc:  # noqa: BLE001
            if _browser_missing(exc):
                sys.exit("cannot start a browser.\n" + INSTALL_HINT)
            raise
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(url, timeout=45000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            final = page.url
        except Exception as exc:  # noqa: BLE001 - a failed load is a status, not a crash
            ctx.close()
            if _browser_missing(exc):
                sys.exit("cannot start a browser.\n" + INSTALL_HINT)
            return False, f"could not load: {type(exc).__name__}"
        ctx.close()
    low = final.lower()
    if any(s in low for s in SIGNED_OUT):
        return False, final
    expected = MAILBOX_URLS.get(name)
    if expected and not any(e in low for e in expected):
        # Landed somewhere that is neither the mailbox nor a login page.
        return False, final + "   (not the mailbox)"
    return True, final


def _launch_headed(p, w: int, h: int):
    # no_viewport is the part that matters: without it the page keeps a fixed viewport no
    # matter how big the window is, which is what clips the sign-in buttons.
    return p.chromium.launch_persistent_context(
        str(PROFILE), headless=False, no_viewport=True,
        args=["--no-first-run", f"--window-size={w},{h}", "--window-position=24,24"])


def seed(name: str, url: str) -> int:
    print(f"\nOpening {name} in the warm-up profile at {PROFILE}.")
    print("Sign in yourself in that window. Nothing here types a password, a one-time code, "
          "or answers a security prompt.")
    print("When the mailbox is open, come back here and press Enter.\n")
    clear_stale_lock()
    sync_playwright = _playwright()
    with sync_playwright() as p:
        w, h = window_size()
        try:
            # no_viewport is the part that matters: without it the page keeps a fixed
            # viewport no matter how big the window is, which is what clips the sign-in
            # buttons. With it, the page fills the window like an ordinary browser.
            ctx = _launch_headed(p, w, h)
        except Exception as exc:  # noqa: BLE001
            if _browser_missing(exc):
                sys.exit("cannot start a browser.\n" + INSTALL_HINT)
            if "existing browser session" not in str(exc):
                raise
            busy = [x for x in _holding_profile() if _alive(x)]
            if busy:
                sys.exit(f"another window is already using this profile (pids {', '.join(busy)}). "
                         "Only one thing can use it at a time - close that window and run this "
                         "again.")
            for lock in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
                (PROFILE / lock).unlink(missing_ok=True)
            print("cleared locks left behind by a killed run; retrying")
            ctx = _launch_headed(p, w, h)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        try:
            input("press Enter once you are signed in... ")
        except EOFError:
            print("no terminal to wait on; close the browser window when done")
        final = page.url
        ctx.close()
    low = final.lower()
    expected = MAILBOX_URLS.get(name)
    ok = (not any(s in low for s in SIGNED_OUT)
          and (not expected or any(e in low for e in expected)))
    state = load_state()
    state[name] = {"url": url, "seeded": ok}
    save_state(state)
    if ok:
        print(f"\n{name}: signed in, session stored in the profile.")
    else:
        # Say which of the two things happened. "Looks like a login page" was printed for
        # both, including for a perfectly good mailbox sitting at an unexpected path, which
        # sends someone signing in again to fix nothing.
        if any(m in final.lower() for m in SIGNED_OUT):
            print(f"\n{name}: still on a sign-in page ({final}). The session was not stored - "
                  "run this again and complete the sign-in.")
        else:
            print(f"\n{name}: ended on {final}, which is not the mailbox. If you ARE signed in, "
                  f"this is the checker being too strict: add that address to MAILBOX_URLS["
                  f"'{name}'] in this script.")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("list", "seed", "check", "reset"))
    ap.add_argument("target", nargs="?", help="a provider name, or a mailbox URL")
    ap.add_argument("--name", help="label for a custom URL")
    args = ap.parse_args()
    state = load_state()

    if args.command == "list":
        print(f"profile: {PROFILE}  ({'exists' if PROFILE.exists() else 'not created yet'})")
        print("built-in providers:", ", ".join(PROVIDERS))
        print("seeded:", ", ".join(state) or "none")
        return 0

    if args.command == "reset":
        if PROFILE.exists():
            shutil.rmtree(PROFILE)
        STATE.unlink(missing_ok=True)
        print("profile cleared; every mailbox needs seeding again")
        return 0

    if args.command == "seed":
        if not args.target:
            return ap.error("seed needs a provider name or a URL") or 2
        if args.target in PROVIDERS:
            return seed(args.target, PROVIDERS[args.target])
        if args.target.startswith("http"):
            name = args.name or args.target.split("//")[-1].split("/")[0]
            return seed(name, args.target)
        return ap.error(f"unknown provider {args.target!r}; use a URL or one of "
                        f"{', '.join(PROVIDERS)}") or 2

    targets = {}
    if args.target:
        url = PROVIDERS.get(args.target) or (state.get(args.target) or {}).get("url")
        if not url:
            if not args.target.startswith("http"):
                return ap.error(
                    f"{args.target!r} is not a seeded name or a known provider, and is not a "
                    f"URL. Seeded: {', '.join(state) or 'none'}. Built in: "
                    f"{', '.join(PROVIDERS)}.") or 2
            url = args.target
        targets[args.target] = url
    else:
        targets = {n: d["url"] for n, d in state.items()}
        if not targets:
            print("nothing seeded yet - run: seed_login.py seed gmail")
            return 0

    worst = 0
    for name, url in targets.items():
        ok, final = verify(name, url)
        print(f"  {name:12} {'SIGNED IN' if ok else 'SIGNED OUT'}   {final[:90]}")
        if not ok:
            worst = 1
    if worst:
        print("\nA signed-out mailbox stops the cadence. Re-seed it before the next run, and "
              "do not let a run quietly skip it - a missed leg is a gap in the evidence.")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
