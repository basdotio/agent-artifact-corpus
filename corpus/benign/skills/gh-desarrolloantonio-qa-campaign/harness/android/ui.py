#!/usr/bin/env python3
"""Command-line UI driver for a QA campaign (see SKILL.md).

Drives an Android device or emulator over `adb`, reading the accessibility tree
(`uiautomator dump`) instead of pixels: it is text, it can be asserted on, and it is cheap.
Screenshots are for the visual layer only.

Selectors (space-separated, ALL must match):
    text=Add list      exact text            text~=list      contains (case-insensitive)
    desc=Settings      contentDescription    desc~=sync      contains
    id=fab_add         testTag / resource-id (suffix)        id~=row_        contains
    class=… class~=…   clickable= scrollable= enabled= checked= selected=  (true/false)
The first match is used; a selector that hits several DIFFERENT controls is refused instead — name one
with `--index N`, or `--any` to take the first on purpose. `--expect <sel>` on tap/longpress/type/clear acts only if that selector is on screen.
`--in <sel>` on tap/longpress/find/assert looks only inside the item that selector names.

    ui.py tap "desc=Settings"
    ui.py wait "text~=Welcome back" --timeout 20
    ui.py scroll-to "text=QA_Card1"
    ui.py type "QA_Note1"
    ui.py shot list-screen --dir qa-shots
    ui.py a11y                     # small targets, overlaps, off-screen, unnamed icons
    ui.py hide-keyboard            # BACK only if the keyboard is showing
    ui.py rotate 1                 # and reads the rotation back from the window manager
    ui.py size tablet              # resizable emulator: phone | unfolded | tablet, read back too
    ui.py demo on                  # frozen status bar, so two screenshots are comparable
    ui.py db main "select id, title, syncStatus from items"   # secret-looking columns come out <hidden>
    ui.py files                    # every file the app keeps, with sizes: where its stores really are
    ui.py file settings            # a text store (shared_prefs, JSON) with secrets hidden; binary → --out
    ui.py kill                     # process death that KEEPS saved state (R9); `stop` discards it
    ui.py open "myapp://item/42"   # a deep link — an entry point the UI inventory can't see
    ui.py tap "desc=Delete" --in "text=QA_Item1"   # the Delete of THAT card, or a refusal
    ui.py installed --apk app/build/outputs/apk/debug/app-debug.apk   # is the device running this build?

Configuration lives in `qa.config.json` (searched upwards from the working directory, or
`QA_CONFIG`). Keys this script reads: `android.package`, `android.packagePrefix` (a LIST of exact
package names, or a prefix — which is refused when it matches more than one installed app),
`android.databases` (alias → file in databases/, or a path in the data folder), `android.files`
(alias → path in the data folder), `android.secretKeys`, `devices` (alias → adb serial or `avd:<name>`),
`managedDevices` and `campaign`. Nothing project-specific here.

Device: `--device <alias>` (from `devices` in the config: an adb serial, or `avd:<name>` for an
emulator, whose serial is looked up on every command), `--serial`, or `ANDROID_SERIAL`.
Every command first checks the device is reachable and refuses with adb's own message if not — and,
once `devices` lists anything, refuses any device that is not on the list.
"""
import argparse
import datetime
import hashlib
import html
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

import json

ADB = None


def _find_adb():
    """$ADB, then PATH, then the SDK env vars, then the macOS default — and refuse if none exists.
    The first version hard-coded the author's macOS path and died with a traceback elsewhere."""
    if os.environ.get("ADB") and not os.path.isfile(os.environ["ADB"]):
        # It used to fall through to PATH, so a typo in $ADB meant a different adb than the one the
        # project's scripts use — and nothing said so (audit).
        raise SystemExit(f"$ADB is {os.environ['ADB']!r}, which is not a file. Fix it or unset it.")
    candidates = [os.environ.get("ADB"), shutil.which("adb")]
    for var in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        if os.environ.get(var):
            candidates.append(os.path.join(os.environ[var], "platform-tools", "adb"))
    candidates.append(os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"))
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    raise SystemExit("adb not found: set $ADB, put adb on PATH, or set $ANDROID_HOME / $ANDROID_SDK_ROOT")


def _load_config():
    """
    `qa.config.json`, looked up from `QA_CONFIG` or by walking up from the working directory.

    Everything project-specific lives there so this script stays the same in every repository.
    """
    explicit = os.environ.get("QA_CONFIG")
    if explicit and not os.path.isfile(explicit):
        # A mistyped QA_CONFIG must not fall back to whatever config is lying around (R8).
        raise SystemExit(f"QA_CONFIG={explicit} does not exist")
    candidates = [explicit] if explicit else []
    here = os.path.abspath(os.getcwd())
    while True:
        candidates.append(os.path.join(here, "qa.config.json"))
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    for path in candidates:
        if path and os.path.isfile(path):
            with open(path) as fh:
                try:
                    return json.load(fh), path
                except ValueError as e:
                    raise SystemExit(f"{path} is not valid JSON: {e}")
    return {}, None


CONFIG, CONFIG_PATH = _load_config()
ANDROID = CONFIG.get("android", {})
DEFAULT_PKG = ANDROID.get("package", "")
# alias → file name inside the app's `databases/` directory, or a path relative to its data folder
DBS = {k: v for k, v in ANDROID.get("databases", {}).items() if not k.startswith("_")}
# alias → any other file the app keeps, relative to its data folder (DataStore, shared_prefs…)
FILES = {k: v for k, v in ANDROID.get("files", {}).items() if not k.startswith("_")}
# What counts as "the app" when reading the accessibility tree and the crash log: exactly `package`,
# unless `packagePrefix` says otherwise. The default used to be the first two segments — the vendor —
# and on an emulator that also had another app by the same vendor, that app's screens counted as
# this one's (measured).
# It can be a LIST of exact package names — the safe form — or a bare prefix, which is only accepted
# while it matches one installed package: `require_one_app()` refuses otherwise, because a vendor-wide
# prefix makes the other app's screens read as this one's and a test can then "pass" against the wrong
# app. `a11y` used to warn about that and carry on.
_prefix = ANDROID.get("packagePrefix") or ""
APP_PKGS = [p for p in _prefix if p] if isinstance(_prefix, list) else []
APP_PKG_PREFIX = "" if APP_PKGS else _prefix
if APP_PKGS and DEFAULT_PKG and DEFAULT_PKG not in APP_PKGS:
    APP_PKGS.append(DEFAULT_PKG)
_PREFIX_OK = False


def is_app(pkg):
    """Does a node's package belong to the app under test?"""
    if APP_PKGS:
        return pkg in APP_PKGS
    return pkg.startswith(APP_PKG_PREFIX) if APP_PKG_PREFIX else pkg == DEFAULT_PKG


def require_one_app():
    """A bare `packagePrefix` must mean ONE installed app, or nothing read from the tree can be
    attributed. Asked once per run, before the first tree is read."""
    global _PREFIX_OK
    if _PREFIX_OK or not APP_PKG_PREFIX:
        return
    _PREFIX_OK = True                                  # ask the device once, however many dumps follow
    installed = [line.split(":", 1)[-1].strip()
                 for line in shell("pm", "list", "packages", APP_PKG_PREFIX, check=False).splitlines()]
    matching = sorted({p for p in installed if p.startswith(APP_PKG_PREFIX)})
    if len(matching) > 1:
        raise SystemExit(
            f"refusing: packagePrefix {APP_PKG_PREFIX!r} matches {len(matching)} installed packages "
            f"({', '.join(matching)}). Their screens would read as this app's, so a flow driven in one "
            "would count as the other's. Name them instead: \"packagePrefix\": [\"" + '", "'.join(matching[:2]) + "\"]"
        )
# alias → adb serial, so a plan can say "phone"/"tablet" instead of emulator-5554. Keys starting with
# `_` are comments. Once this lists anything, no other device is touched (see require_device).
DEVICES = {k: v for k, v in CONFIG.get("devices", {}).items() if not k.startswith("_")} \
    if isinstance(CONFIG.get("devices"), dict) else {}
CLAIM = True  # `release` and `serial` look without stamping the device
DEVICE_TMP = "/data/local/tmp"
# Devices that are not the campaign's to alter — a managed work phone, someone's own phone. Aliases or
# serials. Commands that change device-wide settings or clear shared buffers refuse on them unless
# --allow-device-change: the harness used to assume every test device was disposable (measured).
MANAGED = set(CONFIG.get("managedDevices") or [])
DEVICE_CHANGING = ("rotate", "size", "demo", "clear-crashes")
BOUNDS_RE = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


# ── adb ──────────────────────────────────────────────────────────────────────────────────────────

def adb(*args, check=True, binary=False, timeout=60, with_stderr=False):
    global ADB
    if ADB is None:
        ADB = _find_adb()
    cmd = [ADB, *args]
    try:
        res = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        # A traceback reads like a bug in the harness; this is the device not answering (R8).
        raise SystemExit(f"adb {' '.join(args)} did not answer in {timeout}s — is the device still there? "
                         "(`adb devices`; an emulator that is booting or swapping can take longer)")
    if check and res.returncode != 0:
        raise SystemExit(f"adb {' '.join(args)} → {res.returncode}: {res.stderr.decode(errors='replace').strip()}")
    if binary:
        return res.stdout
    out = res.stdout.decode(errors="replace")
    # `run-as` writes its refusals to STDERR. Callers that need to see a refusal ask for it;
    # the first version of the run-as probe didn't, and never fired (measured).
    return out + res.stderr.decode(errors="replace") if with_stderr else out


def shell(*args, **kw):
    return adb("shell", *args, **kw)


def require_device():
    """
    Refuse up front when no device answers. Without this, every command failed deep inside adb
    with an empty or misleading reason — `dump` said "did not answer: " and `db` blamed the app
    ("has that screen been opened yet?") when the emulator was simply off (R8, measured).
    """
    global ADB
    if ADB is None:
        ADB = _find_adb()
    res = subprocess.run([ADB, "get-state"], capture_output=True, timeout=20)
    if res.returncode == 0 and b"device" in res.stdout:
        # A work or personal phone plugged into the same machine answers too, and with a single
        # device attached adb picks it without being asked. A listed `devices` is the allow-list.
        serial = subprocess.run([ADB, "get-serialno"], capture_output=True, timeout=20).stdout.decode(errors="replace").strip()
        if DEVICES and serial not in {resolve_device(v) for v in DEVICES.values()}:
            listed = ", ".join(f"{k}={v}" for k, v in sorted(DEVICES.items()))
            raise SystemExit(
                f"refusing {serial or 'the connected device'}: it is not in `devices` in {CONFIG_PATH} ({listed}). "
                "The campaign never touches a device it was not given — pass --device <alias>, or add it to the list "
                "if it really is a test device."
            )
        if CLAIM:
            claim_device(serial)
        return
    attached = subprocess.run([ADB, "devices"], capture_output=True, timeout=20).stdout.decode(errors="replace").strip()
    serial = os.environ.get("ANDROID_SERIAL") or "(none — set --device, --serial or ANDROID_SERIAL)"
    raise SystemExit(
        f"no device reachable: {res.stderr.decode(errors='replace').strip() or res.stdout.decode(errors='replace').strip()}\n"
        f"  ANDROID_SERIAL={serial}\n  {attached}"
    )


def density():
    out = shell("wm", "density")
    m = re.search(r"Override density: (\d+)", out) or re.search(r"Physical density: (\d+)", out)
    if not m:
        # A guessed density makes every dp figure wrong, and "assuming 420" was printed to stderr and
        # then used anyway — a measurement nobody took, in a number the report quotes (R8). Unproven is
        # a result; an estimate dressed as a measurement is not.
        raise SystemExit(f"UNPROVEN: could not read the density from `wm density` ({out.strip()!r}). "
                         "Every dp figure depends on it, so nothing is reported rather than assumed.")
    return int(m.group(1))


def screen_size():
    """Screen size in the CURRENT orientation: display 0's `cur=WxH` in `dumpsys window displays`,
    which is already rotated.

    Not the root of the accessibility tree: with a menu open, the dump is the POPUP's window and its
    root is the size of the menu. A tap on a menu's last item was then taken as "under the gesture
    bar", the screen was scrolled, the menu closed, and the tap said NOT found (measured). `wm size`
    gives the unrotated physical size, and `dumpsys input` is useless on resizable emulators: they
    have two displays and the first `SurfaceOrientation` reported is not the app's (measured)."""
    out = shell("dumpsys", "window", "displays", check=False)
    block = re.split(r"(?=Display: mDisplayId=)", out)
    first = next((b for b in block if re.match(r"Display: mDisplayId=0\b", b)), "")
    m = re.search(r"\bcur=(\d+)x(\d+)", first)
    if m:
        return int(m.group(1)), int(m.group(2))
    nodes = dump()
    root = nodes[0] if nodes else None
    if root and root.w > 0 and root.h > 0:
        return root.x2, root.y2
    out = shell("wm", "size")
    m = re.search(r"Override size: (\d+)x(\d+)", out) or re.search(r"Physical size: (\d+)x(\d+)", out)
    if not m:
        # Same rule: every tap coordinate, every "off screen" and every system-bar check is derived
        # from this. A guessed 1080×2400 taps somewhere nobody chose.
        raise SystemExit(f"UNPROVEN: could not read the screen size from `dumpsys window displays`, the "
                         f"accessibility tree or `wm size` ({out.strip()!r}). Coordinates depend on it, so "
                         "nothing is driven rather than assumed.")
    return int(m.group(1)), int(m.group(2))


# ── accessibility tree ───────────────────────────────────────────────────────────────────────────

class Node:
    def __init__(self, el, depth):
        a = el.attrib
        self.text = a.get("text", "")
        self.desc = a.get("content-desc", "")
        self.rid = a.get("resource-id", "")
        self.cls = a.get("class", "")
        self.pkg = a.get("package", "")
        self.clickable = a.get("clickable") == "true" or a.get("long-clickable") == "true"
        self.scrollable = a.get("scrollable") == "true"
        self.enabled = a.get("enabled") == "true"
        self.checked = a.get("checked") == "true"
        self.checkable = a.get("checkable") == "true"
        self.selected = a.get("selected") == "true"
        self.focused = a.get("focused") == "true"
        self.password = a.get("password") == "true"
        m = BOUNDS_RE.match(a.get("bounds", "[0,0][0,0]"))
        if not m:
            # Refuse rather than assume [0,0][0,0]: a 0×0 node reads as an off-screen element or a
            # too-small touch target, which is the silent-wrong-answer class this file guards against.
            raise SystemExit(f"unreadable bounds {a.get('bounds')!r} in the dump — read it again")
        self.x1, self.y1, self.x2, self.y2 = (int(v) for v in m.groups())
        self.depth = depth
        self.children = []
        self.parent = None

    @property
    def center(self):
        return (self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2

    @property
    def w(self):
        return self.x2 - self.x1

    @property
    def h(self):
        return self.y2 - self.y1

    def label(self):
        return self.text or self.desc or self.rid.split("/")[-1] or ""

    def __str__(self):
        flags = "".join(f for f, on in (("C", self.clickable), ("S", self.scrollable), ("✓", self.checked),
                                         ("•", self.selected), ("×", not self.enabled)) if on)
        parts = []
        if self.text:
            parts.append(f'text="{self.text[:70]}"')
        if self.desc:
            parts.append(f'desc="{self.desc[:70]}"')
        if self.rid:
            parts.append(f"id={self.rid.split('/')[-1]}")
        if self.checkable:
            # A Compose switch is an unnamed View beside its label: say what it is, whether it is on, and
            # which label it sits with — a campaign read the wrong node and filed two findings of its own.
            # Its label is INSIDE it when the whole row is the switch (measured: a Settings row), else beside it.
            def labels(nodes):
                for x in nodes:
                    if x.label():
                        yield x.label()
                    yield from labels(x.children)
            own = next(labels(self.children), "")
            beside = own or next((x.label() for x in (self.parent.children if self.parent else []) if x is not self and x.label()), "")
            # A label from BESIDE it is not its name: two unlabeled checkboxes both printed `off ("item one")`,
            # which reads as the app naming them so (measured). Say whose label it is.
            if self.text or self.desc or not beside:
                said = ""
            elif own:
                said = f' ("{own[:40]}")'
            else:
                said = f' (no label; beside "{beside[:40]}")'
            parts.append(f"{'ON' if self.checked else 'off'}" + said)
        return f"{'  ' * min(self.depth, 12)}{flags:<3} {' '.join(parts) or self.cls.split('.')[-1]}  [{self.x1},{self.y1}][{self.x2},{self.y2}]"


SYSTEM_UI_PKGS = ("com.android.systemui",)


def dump(retries=4, windows=False):
    """Flat list of nodes, from the focused window — what the user can actually touch.

    `windows=True` adds the app's OTHER windows (`uiautomator dump --windows`), minus the system bars.
    A Compose dropdown menu opens in a window of its own and is **missing** from the plain dump while
    it is on screen: `find` said no match for an item the screenshot showed (measured). The fallback is
    only used when the plain dump has no match, so a dialog still hides what is behind it (R5).
    """
    last = ""
    require_one_app()
    for i in range(retries):
        # /data/local/tmp, not /sdcard: a managed phone's "no USB file transfer" policy let uiautomator
        # print "dumped to" while the shell couldn't read /sdcard back (measured). The shell owns this one.
        cmd = ["uiautomator", "dump"] + (["--windows"] if windows else []) + [f"{DEVICE_TMP}/qa_ui.xml"]
        out = shell(*cmd, check=False, with_stderr=True)
        if "dumped to" in out:
            xml = shell("cat", f"{DEVICE_TMP}/qa_ui.xml")
            # /data/local/tmp is world-readable: the screen's text (and whatever it showed) stayed on
            # the device after every dump (audit).
            shell("rm", "-f", f"{DEVICE_TMP}/qa_ui.xml", check=False)
            try:
                root = ET.fromstring(xml)
            except ET.ParseError as e:
                last = str(e)
                continue
            nodes = []

            def walk(el, depth, parent):
                for child in el:
                    if child.tag != "node":
                        # `--windows` wraps every window: <displays><display><window><hierarchy><node>.
                        walk(child, depth, parent)
                        continue
                    n = Node(child, depth)
                    n.parent = parent
                    if parent:
                        parent.children.append(n)
                    nodes.append(n)
                    walk(child, depth + 1, n)

            walk(root, 0, None)
            if windows:
                # Only the app's own windows: the keyboard carries "Delete" and "Search" descriptions,
                # and matching them would make `find` say a control is there while `assert` says it is not.
                nodes = [n for n in nodes if is_app(n.pkg)]
            return nodes
        last = out.strip()
        time.sleep(0.8 * (i + 1))
    raise SystemExit(f"uiautomator dump did not answer: {last}")


def parse_selector(sel):
    conds = []
    # "text=Add list clickable=true" → two conditions; a value may contain spaces.
    for tok in re.split(r"\s+(?=\w+~?=)", sel.strip()):
        m = re.match(r"(\w+)(~?=)(.*)", tok, re.S)
        if not m:
            raise SystemExit(f"malformed selector: {tok!r}")
        key, op, val = m.groups()
        conds.append((key, op, val.strip().strip('"')))
    if not conds:
        raise SystemExit(f"selector has no conditions: {sel!r}")
    return conds


def matches(n, conds):
    for key, op, val in conds:
        field = {"text": n.text, "desc": n.desc, "id": n.rid, "class": n.cls}.get(key)
        if key in ("clickable", "scrollable", "enabled", "checked", "selected"):
            if str(getattr(n, key)).lower() != val.lower():
                return False
            continue
        if field is None:
            raise SystemExit(f"unknown selector key: {key}")
        if key == "id" and op == "=":
            # The part after the slash, or the whole resource-id: `id=com.x:id/title` matched nothing
            # before, although that is what the dump prints (audit).
            if field != val and field.split("/")[-1] != val:
                return False
        elif op == "=":
            if field != val:
                return False
        elif val.lower() not in field.lower():
            return False
    return True


def find(sel, nodes=None):
    conds = parse_selector(sel)
    return [n for n in (nodes or dump()) if matches(n, conds)]


def pick(sel, index=0, nodes=None):
    found = find(sel, nodes)
    if len(found) <= index:
        visible = [n.label() for n in (nodes or dump()) if n.label()][:25]
        raise SystemExit(f"NOT found: {sel!r} (index {index}). What IS there: {visible}")
    return found[index]


def clickable_ancestor(n):
    """Compose puts the click on a container, not on the text: climb to the first clickable."""
    cur = n
    while cur is not None and not cur.clickable:
        cur = cur.parent
    return cur or n


# ── actions ──────────────────────────────────────────────────────────────────────────────────────


def ensure_tappable(sel, n, index=0, within=None):
    """Scrolls the node away from the system bars before tapping it.

    An element whose centre falls in the gesture bar (bottom) or the status bar (top) gets its tap
    delivered to the SYSTEM, not the app, and the control looks dead. Measured on a real campaign;
    it is indistinguishable from a genuinely dead button. The zones are a fraction of the height,
    which is a guess that has held on every device tried so far.
    """
    w, h = screen_size()
    bottom_zone, top_zone = int(h * 0.94), int(h * 0.035)
    _, cy = n.center
    if top_zone < cy < bottom_zone:
        return n
    direction = 1 if cy >= bottom_zone else -1
    shell("input", "swipe", str(w // 2), str(int(h * 0.6 + 300 * direction)),
          str(w // 2), str(int(h * 0.6 - 300 * direction)), "250")
    time.sleep(0.7)
    # Re-pick INSIDE the same scope: a plain pick after scrolling would take the first match on the
    # whole screen — another card's Delete.
    found = find_in(sel, within, dump())
    if len(found) <= index:
        raise SystemExit(f"NOT found after scrolling it clear of the system bars: {sel!r}" + (f" in {within!r}" if within else ""))
    return clickable_ancestor(found[index])


def shown(n):
    """What a control says: its own label, or the first label inside it (Compose puts the click on
    a container and the text on a child)."""
    return n.label() or next((c.label() for c in walk_desc(n) if c.label()), "")


INPUT_CMDS = ("tap", "longpress", "type", "clear", "key", "back", "hide-keyboard", "show-keyboard", "scroll-to")


def app_in_front(pkg):
    """The package of the resumed activity, from the activity manager."""
    out = shell("dumpsys", "activity", "activities", check=False)
    m = re.search(r"(?:topResumedActivity|mResumedActivity)[=:]\s*ActivityRecord\{\S+ \S+ ([\w.]+)/", out)
    if not m:
        raise SystemExit("could not read which app is in front (`topResumedActivity` in `dumpsys activity activities`)")
    return m.group(1)


def is_ours(front, pkg):
    """Is the package in front the app under test? `pkg` (it may come from --pkg), or whatever
    `packagePrefix` counts as the app. The guards compared with `pkg` alone and ignored the LIST form,
    so the variant the config named as the same app was refused as another one."""
    if APP_PKG_PREFIX:
        return front.startswith(APP_PKG_PREFIX)
    return front == pkg or front in APP_PKGS


def require_app_in_front(pkg):
    """
    Input only goes to the app under test. When two campaigns share an AVD, the other campaign's app
    stays in the task stack: a BACK too many, or an instrumented run ending the app's process, and the
    next input landed on the OTHER app — twice (measured). `--any-app` for flows that leave on purpose
    (a share sheet, the browser, a permission dialog).
    """
    if not pkg and not APP_PKG_PREFIX and not APP_PKGS:
        return
    front = app_in_front(pkg)
    if not is_ours(front, pkg):
        raise SystemExit(
            f"refusing input: {front} is in front, not {APP_PKG_PREFIX or ' / '.join(APP_PKGS) or pkg}. Something left the app under test — "
            "`ui.py launch` to bring it back, or pass --any-app if leaving it was the point."
        )


def check_expected(expect, nodes=None):
    """
    `--expect <sel>`: act only if the screen is the one the script thinks it is. Measured: a sheet
    reopened over Settings mid-loop, and every later tap landed on the sheet and printed a normal
    "tap:" line — a row of invalid results instead of one stop.
    """
    if not expect:
        return nodes
    nodes = nodes or dump()
    if not find(expect, nodes):
        visible = [n.label() for n in nodes if n.label()][:25]
        raise SystemExit(f"NOT on the expected screen: {expect!r} is not showing. What IS there: {visible}")
    return nodes


def find_in(sel, within=None, nodes=None):
    """
    `--in <anchor>`: only the matches in the smallest part of the screen that holds both the anchor
    and a match — "the Delete button of the card titled X". On a feed every card has the same
    buttons, and an --index guess on a destructive one is how real data gets deleted (measured: a
    campaign had to write this guard itself before touching any per-card control).

    Refuses rather than guess: when the anchor appears in two different places, when the smallest
    shared part is a scrolling list (the anchor's own item has no such control, so the match would be
    another item's), and — in `tap` — when that part still holds several different controls.
    """
    nodes = nodes or dump()
    if not within:
        return find(sel, nodes)
    anchors = find(within, nodes)
    # A search field holding the anchor's text is not an item: searching "QA_Off01" and anchoring on
    # the card titled "QA_Off01" matched both, and --in refused (measured). Text fields anchor only
    # when nothing else matches.
    anchors = [n for n in anchors if not n.cls.endswith("EditText")] or anchors
    if not anchors:
        visible = [n.label() for n in nodes if n.label()][:25]
        raise SystemExit(f"NOT found: anchor {within!r}. What IS there: {visible}")
    targets = find(sel, nodes)
    scope, inside = None, []
    for cand in [anchors[0], *ancestors(anchors[0])]:
        inside = [t for t in targets if t is cand or cand in ancestors(t)]
        if inside:
            scope = cand
            break
    if scope is None:
        raise SystemExit(f"NOT found: {sel!r} anywhere around {within!r}")
    # a list at the scope, or between the anchor and the scope, means the match is in another item
    if scope.scrollable or any(p.scrollable for p in ancestors(anchors[0]) if scope in ancestors(p)):
        raise SystemExit(
            f"{sel!r} is not inside the same item as {within!r}: the nearest one belongs to the list around it, "
            "so it would be another item's. Refusing."
        )
    strays = [a for a in anchors[1:] if a is not scope and scope not in ancestors(a)]
    if strays:
        raise SystemExit(
            f"anchor {within!r} matches {len(anchors)} different places on screen, each with its own {sel!r}. "
            "Narrow the anchor until it names one item."
        )
    return inside


def tap(sel, index=None, long=False, expect=None, within=None, allow_any=False):
    nodes = check_expected(expect) or dump()
    found = find_in(sel, within, nodes)
    if not found:
        found = find_elsewhere(sel, within)
    if len(found) <= (index or 0):
        visible = [n.label() for n in nodes if n.label()][:25]
        raise SystemExit(f"NOT found: {sel!r} (index {index or 0}). What IS there: {visible}")
    # A selector that hits two DIFFERENT controls is a question, not a choice: `text~=OK` matched an
    # error message ({"ok":false…}) before the button, and the tap printed a normal line (measured).
    # It used to take the first and warn — which is how "Delete" hits the wrong Delete and the run
    # still reads green. It refuses now: `--index N` names one, `--any` takes the first on purpose.
    matched = found[index or 0]
    targets, labels = [], []
    for m in found:
        t = clickable_ancestor(m)
        if all(t is not o for o in targets):
            targets.append(t)
            labels.append(m.label() or shown(t) or t.cls.split('.')[-1])
    if index is None and len(targets) > 1:
        listed = "; ".join(f"[{i}] {lab}" for i, lab in enumerate(labels[:5]))
        where = f" in {within!r}" if within else ""
        if not allow_any:
            raise SystemExit(f"refusing: {sel!r}{where} is {len(targets)} different controls ({listed}). "
                             "Narrow the selector, name one with --index N, or --any to take the first.")
        print(f"note: {sel!r}{where} is {len(targets)} different controls ({listed}) — --any took the first",
              file=sys.stderr)
    n = clickable_ancestor(matched)
    n = ensure_tappable(sel, n, index or 0, within)
    refuse_a_stand_in(sel, matched, n)
    x, y = n.center
    # The dump still lists nodes the keyboard covers: a tap meant for "Create" typed a "g" into a
    # field, twice (measured). Same for the stylus pill over a nav rail.
    for x1, y1, x2, y2 in ime_rects():
        if x1 <= x < x2 and y1 <= y < y2:
            raise SystemExit(
                f"refusing: {shown(n) or sel} @({x},{y}) is under the keyboard — a tap there types instead. "
                "`hide-keyboard` (or `scroll-to`) first."
            )
    if long:
        shell("input", "swipe", str(x), str(y), str(x), str(y), "800")
    else:
        shell("input", "tap", str(x), str(y))
    note = ""
    if index is None and len(found) > 1:
        # Repeats that are the same control (a label and its chip inside one row: measured in three
        # processes) are not ambiguous — the tap lands in the right place. Still say how many there were.
        listed = "; ".join(f"[{i}] {m.label() or m.cls.split('.')[-1]} @({m.center[0]},{m.center[1]})" for i, m in enumerate(found[:5]))
        note = f" — ⚠️ first of {len(found)} matches ({listed}); use --index or a narrower selector"
    # The label of what the SELECTOR matched, not the first label inside the clickable container:
    # `tap "desc=Remove qa_off2"` printed "qa_off2", a neighbour's text (measured).
    print(f"{'longpress' if long else 'tap'}: {matched.label() or shown(n) or sel} @({x},{y}){note}")


def refuse_a_stand_in(sel, matched, n):
    """
    The clickable that `clickable_ancestor` found stands in for a label that is not clickable. When it is
    half the screen or more, its centre is somewhere else entirely: `tap "text=Remember me"` climbed to
    a full-screen container (it clears focus), pressed (540,1200), printed "tap:" and toggled nothing —
    and a false "the upgrade logs everyone out" P1 followed (measured).
    """
    if n is matched or matched.clickable or n.w * n.h == 0:
        return
    w, h = screen_size()
    if n.w * n.h * 2 >= w * h and n.w * n.h >= 4 * max(1, matched.w * matched.h):
        raise SystemExit(
            f"refusing: {sel!r} is not clickable, and the nearest clickable around it covers "
            f"{100 * n.w * n.h // (w * h)}% of the screen ([{n.x1},{n.y1}][{n.x2},{n.y2}]) — its centre is not "
            "this control. Tap the control itself (the checkbox or switch beside the label: `state` finds it)."
        )


def find_elsewhere(sel, within=None):
    """The same selector in the app's other windows (a dropdown, a popup). Says so when it hits."""
    if not DEFAULT_PKG and not APP_PKG_PREFIX:
        return []          # without a package we cannot tell the app's windows from anyone else's
    found = find_in(sel, within, dump(windows=True))
    if found:
        print(f"note: {sel!r} is in another window of the app (a popup or dropdown), not in the focused one",
              file=sys.stderr)
    return found


def wait(sel, timeout=15.0, gone=False):
    t0 = time.time()
    while time.time() - t0 < timeout:
        present = bool(find(sel)) or (not gone and bool(find_elsewhere(sel)))
        if present != gone:
            print(f"{'gone' if gone else 'visible'}: {sel} ({time.time() - t0:.1f}s)")
            return True
        time.sleep(0.7)
    nodes = dump()
    visible = [n.label() for n in nodes if n.label()][:25]
    hint = "" if gone else " `wait` doesn't scroll: if it may be below the fold, use `scroll-to`."
    raise SystemExit(f"TIMEOUT {timeout}s waiting for {sel!r} to {'disappear' if gone else 'appear'}.{hint} What IS there: {visible}")


def scroll_to(sel, direction="down", max_swipes=12):
    w, h = screen_size()
    for i in range(max_swipes + 1):
        nodes = dump()
        found = find(sel, nodes)
        if found:
            n = found[0]
            print(f"found after {i} swipes: {n.label()} [{n.x1},{n.y1}][{n.x2},{n.y2}]")
            return n
        scrollables = sorted((n for n in nodes if n.scrollable), key=lambda n: n.w * n.h, reverse=True)
        area = scrollables[0] if scrollables else None
        cx = area.center[0] if area else w // 2
        top = (area.y1 if area else 0) + (area.h if area else h) // 4
        bottom = (area.y1 if area else 0) + 3 * (area.h if area else h) // 4
        a, b = (bottom, top) if direction == "down" else (top, bottom)
        shell("input", "swipe", str(cx), str(a), str(cx), str(b), "350")
        time.sleep(0.6)
    raise SystemExit(f"NOT found after {max_swipes} swipes ({direction}): {sel!r}")


def clear_field(sel=None, n=80, expect=None):
    """Clears a field: tap, jump to the end, delete `n` characters in ONE `input` call
    (one `input` call per key costs ~1 s each: 40 deletes were half a minute). With no selector, the
    FOCUSED field — like `type`, which needs none (the asymmetry cost a campaign a round trip)."""
    if sel:
        tap(sel, expect=expect)
    else:
        nodes = check_expected(expect) or dump()
        if not any(x.focused for x in nodes):
            raise SystemExit("no focused field to clear — pass a selector")
    shell("input", "keyevent", "KEYCODE_MOVE_END")
    shell("input", "keyevent", *(["KEYCODE_DEL"] * n))
    print(f"cleared: {sel or 'the focused field'}")


def watch(seconds, sel=None):
    """
    Every label that appears on screen for `seconds`, with when it first and last showed. A snackbar
    lives ~2 s and one dump takes ~1.5 s: a single read missed "Session expired" as often as not, and was
    reported as "no message at all" twice (measured). With a selector, it stops as soon as that appears.
    """
    seen, t0, hit = {}, time.time(), False
    while time.time() - t0 < seconds:
        nodes = dump()
        now = time.time() - t0
        for n in nodes:
            lab = n.text or n.desc
            if lab:
                first, _ = seen.get(lab, (now, now))
                seen[lab] = (first, now)
        if sel and find(sel, nodes):
            print(f"appeared: {sel} ({now:.1f}s)")
            hit = True
            break
    for lab, (first, last) in sorted(seen.items(), key=lambda kv: kv[1][0]):
        print(f"{first:6.1f}s–{last:5.1f}s  {lab[:100]}")
    if sel and not hit:
        # It used to re-check the labels it collected, which cannot answer `id=` or `class=`
        # selectors: `watch --until "id=…"` printed "appeared" and then exited 1 (measured).
        raise SystemExit(f"{sel!r} never appeared in {seconds}s")


def matches_label(sel, label):
    conds = parse_selector(sel)
    fake = Node(ET.Element("node", {"text": label, "content-desc": label}), 0)
    return any(matches(fake, [c]) for c in conds if c[0] in ("text", "desc"))


def state(sel):
    """On/off of the switch or checkbox a selector names — or of the one beside the label it matches."""
    n = pick(sel)
    # The switch can be the label's own row (an ancestor), inside what matched, or beside it — in that
    # order. The first version looked only inside and beside, and missed a whole-row switch (measured).
    candidates = [n, *ancestors(n)[:3], *walk_desc(n)]
    if n.parent is not None:
        candidates += [s for s in n.parent.children if s is not n] + [d for s in n.parent.children for d in walk_desc(s)]
    box = next((c for c in candidates if c.checkable), None)
    if box is None:
        raise SystemExit(f"nothing checkable in or beside {sel!r} — not a switch or checkbox, or its state isn't exposed")
    print(f"{'ON' if box.checked else 'off'}  ({box.cls.split('.')[-1]} [{box.x1},{box.y1}][{box.x2},{box.y2}])")
    return box.checked


LOG_HEADER_RE = re.compile(r"^(\S+ \S+\s+\d+\s+\d+ [VDIWEFA] .*?: )(.*)$")


def app_log(pkg, lines=300, grep=None):
    """
    The log of the app's RUNNING process, with secret-looking values hidden (keys, JWTs, and the
    project's own `android.secretKeys`). A campaign's first P0 lived in logcat, and reading it by hand
    printed a real NFC card id into the transcript and cleared the phone's log with `logcat -c`
    (measured). This reads, filters by the app's pid, hides, and never clears.
    """
    pids = shell("pidof", pkg, check=False).split()
    if not pids:
        raise SystemExit(f"{pkg} is not running — launch it first: `log` reads the running process only")
    out = adb("logcat", f"--pid={pids[0]}", "-t", str(lines))
    shown_any = False
    for line in out.splitlines():
        # Hide inside the message only: the "Tag : " header reads like "key: value", and a tag named
        # RtrSession hid the word after it (measured here, on a fake log, before shipping).
        head = LOG_HEADER_RE.match(line)
        shown = (head.group(1) + hide_secrets_in_text(head.group(2), inline=True)) if head else hide_secrets_in_text(line, inline=True)
        # Filter AFTER hiding: grepping the raw line let `--grep <the secret>` confirm a value by
        # whether anything came back (audit). Grepping by key name still works on the hidden text.
        if grep and grep.lower() not in shown.lower():
            continue
        print(shown)
        shown_any = True
    if not shown_any:
        print(f"(no log lines{' matching ' + repr(grep) if grep else ''} from pid {pids[0]})", file=sys.stderr)


def keyboard_state():
    """
    "none", "keyboard" or "small" — from the WINDOW MANAGER, not `dumpsys input_method` (its
    `mInputShown` is per client, and a stale `true` pressed BACK with no keyboard up — measured).

    The input-method window being visible is not enough: Gboard's stylus toolbar — a small pill on
    the side — is a visible input-method window too, doesn't take BACK, and a BACK sent for it closed
    the app under test (measured). Its touchable region tells them apart, measured on one emulator:
    hidden → only the navigation strip; stylus pill → ~4 % of the screen; floating keyboard → ~28 %.
    """
    out = shell("dumpsys", "window", "InputMethod", check=False)
    vis = re.search(r"isVisible=(true|false)", out)
    if not vis:
        raise SystemExit("could not read the keyboard window (`isVisible` in `dumpsys window InputMethod`)")
    if vis.group(1) != "true":
        return "none"
    w, h = screen_size()
    area = sum((x2 - x1) * (y2 - y1) for x1, y1, x2, y2 in ime_rects(out, h))
    return "keyboard" if area >= 0.15 * w * h else "small"


def ime_rects(out=None, h=None):
    """The input-method window's touchable rectangles — keyboard or stylus pill — without the
    navigation strip it always keeps at the bottom. Empty when it isn't visible."""
    out = out if out is not None else shell("dumpsys", "window", "InputMethod", check=False)
    if "isVisible=true" not in out:
        return []
    h = h or screen_size()[1]
    region = re.search(r"touchable region=SkRegion\(((?:\(\d+,\d+,\d+,\d+\))*)\)", out)
    rects = []
    for x1, y1, x2, y2 in re.findall(r"\((\d+),(\d+),(\d+),(\d+)\)", region.group(1) if region else ""):
        x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
        if not (y2 >= h - 2 and (y2 - y1) < h * 0.05):
            rects.append((x1, y1, x2, y2))
    return rects


def keyboard_shown():
    return keyboard_state() == "keyboard"


def hide_keyboard(expect=None):
    """
    Hide the keyboard and PROVE nothing else went with it. Android has no shell command that only
    hides the keyboard (ESCAPE and CLOSE_SYSTEM_DIALOGS do nothing — measured), so this sends BACK,
    and BACK can do more: in one app a single BACK closed the keyboard AND the sheet holding the
    field (measured). So: nothing is sent when no keyboard is up, and after BACK the text field
    that was on screen — or `--expect` — must still be there, or the command fails.
    """
    state = keyboard_state()
    if state == "none":
        print("keyboard not showing — nothing sent")
        return
    if state == "small":
        raise SystemExit(
            "only a small input-method window is up (Gboard's stylus toolbar, a floating pill) — not a keyboard. "
            "It doesn't take BACK, so nothing was sent: a BACK here closes the screen instead (measured). "
            "Tap outside the field, or carry on with the pill showing."
        )
    before = dump()
    fields = [(n.x1, n.y1, n.x2, n.y2) for n in before if n.cls.endswith("EditText")]
    shell("input", "keyevent", "KEYCODE_BACK")
    t0 = time.time()
    while keyboard_shown():
        if time.time() - t0 > 3:
            raise SystemExit("sent BACK, and the keyboard is still showing")
        time.sleep(0.3)
    time.sleep(0.5)
    after = dump()
    if expect and not find(expect, after):
        raise SystemExit(f"keyboard hidden, but BACK also left the screen: {expect!r} is gone")
    if not expect and fields and not any(n.cls.endswith("EditText") for n in after):
        raise SystemExit(
            f"keyboard hidden, but BACK also closed what held the text field (was at {fields[0]}). "
            "The screen changed: re-check where you are. Before filing it against the app, repeat one Back with a "
            "keyboard up in an app you are not testing (the system Settings search): on one emulator it closed that "
            "screen too, so it was not the app's doing (measured)."
        )
    print("keyboard hidden")


def show_keyboard():
    """
    A real keyboard, when Gboard shows only its stylus pill. The pill's own menu offers "Show on-screen
    keyboard" with the shortcut Alt+K, and the shortcut works from the shell (measured). The device-level
    alternative — `settings put secure stylus_handwriting_enabled 0`, effective from the next field focus
    (measured) — changes a user setting, so it is the human's to agree.
    """
    state = keyboard_state()
    if state == "keyboard":
        print("keyboard already up")
        return
    if state == "none":
        raise SystemExit("no input method is up — focus a text field first")
    shell("input", "keycombination", "KEYCODE_ALT_LEFT", "KEYCODE_K")
    t0 = time.time()
    while time.time() - t0 < 3:
        time.sleep(0.3)
        if keyboard_state() == "keyboard":
            print("keyboard up (Alt+K from the stylus pill)")
            return
    raise SystemExit(
        "Alt+K did not bring a keyboard up — the small input window may not be Gboard's pill. Open its menu by hand, "
        "or ask the human about `settings put secure stylus_handwriting_enabled 0`."
    )


def focused_field(nodes):
    return next((n for n in nodes if n.focused and (n.cls.endswith("EditText") or n.password)), None)


def type_text(text, expect=None, into=None, check=True):
    check_expected(expect)
    if into:
        # Tap the field first and stop if the tap is refused: a refused tap followed by `type` wrote into
        # whichever field still had focus (measured). One command, so a shell chain can't skip the refusal.
        tap(into)
        time.sleep(0.4)
    # What `input text` cannot do, said out loud instead of printing "typed" (R8): a newline is a
    # command separator on the device's shell, and non-ASCII never arrives — `input text "Grüße"`
    # types "Gr" and drops the rest, which reads as an app that eats characters.
    bad = [name for ch, name in ((chr(10), "a newline"), (chr(13), "a carriage return"), (chr(9), "a tab")) if ch in text]
    if bad:
        raise SystemExit(f"`type` cannot send {' or '.join(bad)} — send the lines one at a time, "
                         "with `key ENTER` between them")
    if any(ord(c) > 127 for c in text):
        raise SystemExit(f"`type` cannot send non-ASCII text ({text!r}): `input text` drops it. "
                         "Paste it through the clipboard (`am broadcast` in your project's script) or use ASCII in the fixture")
    # `input text` chokes on spaces and several symbols: escape them one by one, then quote the whole
    # argument — it is re-parsed by the device's shell after adb joins the arguments with spaces.
    esc = re.sub(r"([\\\"'`$&|;<>()*?!#~])", r"\\\1", text).replace(" ", "%s")
    shell("input", "text", shlex.quote(esc))
    # Read it back: once the first character was dropped, and "typed: 'A_R8_Place'" hid it until the
    # record showed up as "_R8_Place" (measured). A password field shows dots — never read, never echoed.
    field = focused_field(dump()) if check else None
    if field is not None and field.password:
        print(f"typed: {len(text)} characters into a password field (not read back)")
        return
    if field is not None and text not in field.text:
        raise SystemExit(f"typed {text!r}, but the field reads {field.text!r}. "
                         "Clear it and type again; `--no-check` for a field that reformats what it gets")
    print(f"typed: {text!r}" + ("" if field is not None or not check else " (no focused text field to read it back from)"))


def screenshot(name, outdir, overwrite=False):
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, name if name.endswith(".png") else name + ".png")
    # A reused name, and the gate's old screenshot was read as the new build's (measured).
    if os.path.exists(path) and not overwrite:
        raise SystemExit(f"{path} already exists — it is an earlier screenshot. Pick a new name, or --overwrite")
    # Multi-display emulators: `screencap -p` prints a warning into the stream and corrupts the
    # PNG; it needs the id of the main display — and **which one is first in the list is not fixed**.
    # An emulator listed EMU_display_1 first, so every shot was a black portrait image of the other
    # display while the window manager said 1920×1200 (measured). Take HWC display 0 / port=0.
    disp = shell("dumpsys", "SurfaceFlinger", "--display-id", check=False)
    m = (re.search(r"^Display (\d+) \(HWC display 0\)", disp, re.M)
         or re.search(r"^Display (\d+)[^\n]*\bport=0\b", disp, re.M)
         or re.search(r"^Display (\d+)", disp, re.M))
    remote = f"{DEVICE_TMP}/qa_shot.png"
    args = ["screencap", "-p", remote] if not m else ["screencap", "-d", m.group(1), "-p", remote]
    shell(*args)
    adb("pull", remote, path)
    shell("rm", "-f", remote, check=False)     # world-readable: don't leave screens behind (audit)
    # R8: a screenshot of the wrong display is not a screenshot. Its size has to be the screen's.
    size = png_size(path)
    if size and size != screen_size():
        raise SystemExit(
            f"the screenshot is {size[0]}×{size[1]} but the screen is {screen_size()[0]}×{screen_size()[1]} — "
            f"it came from another display. It is at {path}; don't read it as this screen."
        )
    print(path)
    return path


def png_size(path):
    """(width, height) from the PNG header, or None if it doesn't look like a PNG."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(24)
        if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
            return None
        return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
    except OSError:
        return None


def current_rotation():
    """0..3 from the window manager — the only source that says what the device actually did."""
    out = shell("dumpsys", "window", check=False)
    m = re.search(r"mCurrentRotation=ROTATION_(\d+)", out) or re.search(r"\bmRotation=(?:ROTATION_)?(\d+)", out)
    if not m:
        raise SystemExit("could not read the rotation from `dumpsys window`")
    v = int(m.group(1))
    return v // 90 if v >= 90 else v


SIZES = {"phone": "0", "unfolded": "1", "tablet": "2"}


def display_size():
    """(width, height, density) from the window manager — the override when one is set."""
    size = shell("wm", "size", check=False)
    dens = shell("wm", "density", check=False)
    s = re.search(r"Override size: (\d+)x(\d+)", size) or re.search(r"Physical size: (\d+)x(\d+)", size)
    d = re.search(r"Override density: (\d+)", dens) or re.search(r"Physical density: (\d+)", dens)
    if not s or not d:
        raise SystemExit(f"could not read the display size back: {size.strip()!r} / {dens.strip()!r}")
    return int(s.group(1)), int(s.group(2)), int(d.group(1))


def looks_like(kind, w, h, dens):
    """Loose on purpose: the presets' exact pixels differ between images, their shape doesn't."""
    wdp, hdp = w * 160 / dens, h * 160 / dens
    if kind == "phone":
        return min(wdp, hdp) < 600
    if kind == "unfolded":
        return min(wdp, hdp) >= 600 and max(wdp, hdp) / min(wdp, hdp) < 1.4
    return min(wdp, hdp) >= 600 and max(wdp, hdp) / min(wdp, hdp) >= 1.4


def resize(kind):
    """
    Switch a resizable emulator between its phone, unfolded and tablet presets — through the
    emulator console (`resize-display`, the only way; a campaign found it in the console's help) —
    and PROVE it from the window manager, like `rotate` (R8). Only works on emulators that have the
    presets; anything else refuses.
    """
    before = display_size()
    out = adb("emu", "resize-display", SIZES[kind], check=False, with_stderr=True).strip()
    if "KO" in out or "unknown" in out.lower():
        raise SystemExit(f"the emulator refused `resize-display {SIZES[kind]}`: {out} — not a resizable AVD?")
    t0, seen = time.time(), None
    while time.time() - t0 < 20:
        time.sleep(1)
        w, h, dens = display_size()
        # The size and the density land at different moments: right after the command the display still
        # had the old pixels at the new density — 731×457 dp, which "looks like a phone" — and `size`
        # reported success 5 s before the real one arrived (measured). Wait for a reading that is
        # different from before AND the same as the previous one.
        if (w, h, dens) != seen:          # still moving: the size and the density land apart
            seen = (w, h, dens)
            continue
        if (w, h, dens) == before and looks_like(kind, w, h, dens):
            print(f"already {kind}: {w}×{h} @ {dens} dpi — the display did not have to change")
            return
        if (w, h, dens) == before:
            continue
        if looks_like(kind, w, h, dens):
            print(f"size {kind}: {w}×{h} @ {dens} dpi ({w * 160 // dens}×{h * 160 // dens} dp), was {before[0]}×{before[1]} @ {before[2]}")
            if dens != before[2]:
                # The presets change width AND density: counting grid columns across them compares two
                # densities, and an adaptive grid looked like it lost a column (measured).
                print(f"   ⚠️ density changed {before[2]} → {dens} dpi: compare layouts in dp, not in columns or pixels", file=sys.stderr)
            return
    raise SystemExit(f"asked for {kind}, the window manager still says {w}×{h} @ {dens} dpi — the display did NOT change")


def rotate(value):
    """
    Rotate and PROVE it (R9). The first version issued one `wm user-rotation lock` and compared two
    accessibility dumps 2 s apart: it failed when asked for the orientation it was already in,
    once reported a rotation that had not happened, and never succeeded on the resizable phone AVD
    it was measured on, whose emulator reverted the lock within ~2 s (a newer resizable image kept
    it: this depends on the emulator image, not on "resizable"). Now the window manager is polled, an "already
    there" is a success, and a reverted lock is re-issued once before giving up.
    """
    target = 0 if value == "natural" else int(value)
    before = current_rotation()
    if value == "natural":
        shell("wm", "user-rotation", "free")
        shell("settings", "put", "system", "accelerometer_rotation", "0")
    if before == target:
        shell("wm", "user-rotation", "lock", str(target))
        print(f"already at rotation {target} (screen {screen_size()})")
        return
    for attempt in range(2):
        # `settings put system user_rotation` does NOT rotate anything while auto-rotate is on
        # (see R9); this does.
        shell("wm", "user-rotation", "lock", str(target))
        t0 = time.time()
        while time.time() - t0 < 5:
            time.sleep(0.5)
            if current_rotation() == target:
                time.sleep(1.0)  # let the activity finish recreating before anyone dumps it
                print(f"rotated {before} → {target} (screen {screen_size()})")
                return
        if attempt == 0:
            print("rotation lock was lost; re-issuing once", file=sys.stderr)
    raise SystemExit(
        f"the screen did NOT rotate: still at {current_rotation()}, wanted {target}. "
        "This device reverted the rotation lock (seen on some resizable/foldable emulator images, not all): "
        "rotate from the emulator's own toolbar, or use a device that keeps the lock, for R9."
    )


def demo(on):
    """Freezes the status bar (clock, battery, signal) so two screenshots are comparable."""
    if on:
        shell("settings", "put", "global", "sysui_demo_allowed", "1")
        for extra in (["enter"], ["clock", "-e", "hhmm", "1200"],
                      ["battery", "-e", "level", "100", "-e", "plugged", "false"],
                      ["network", "-e", "wifi", "show", "-e", "level", "4"],
                      ["network", "-e", "mobile", "hide"], ["notifications", "-e", "visible", "false"]):
            shell("am", "broadcast", "-a", "com.android.systemui.demo", "-e", "command", *extra, check=False)
    else:
        shell("am", "broadcast", "-a", "com.android.systemui.demo", "-e", "command", "exit", check=False)
    print(f"demo mode {'ON' if on else 'OFF'}")


def a11y(min_dp=48):
    """
    Automatic checks on the current screen: touch targets below the minimum, overlapping
    clickables, off-screen content, icons with no accessible name.

    Two classes of finding are reported as notes (·) rather than warnings, because they are the
    tool being wrong rather than the app: elements that only look small because they are
    half-scrolled out of view, and things that float over a list by design (a FAB). See R8.
    """
    nodes = dump()
    dens = density()
    w, h = screen_size()
    px_min = min_dp * dens / 160
    issues = []
    # What the tool does NOT count as a defect but is worth seeing: viewport clipping, and
    # things that float by design.
    notes = []
    if not APP_PKG_PREFIX and not DEFAULT_PKG:
        # R8: a harness with no configuration must SAY SO, not report "0 warnings" over an empty
        # node list. A silent all-clear is the worst thing a checker can do.
        raise SystemExit(
            "a11y needs to know which package is the app: set android.package (or android.packagePrefix) in qa.config.json "
            f"(looked for it from {os.getcwd()} upwards, and in $QA_CONFIG)"
        )
    app_nodes = [n for n in nodes if is_app(n.pkg)]
    if not app_nodes:
        # The same silent all-clear one step later: the app is not in front, so there is nothing of
        # it to check, and "0 warnings" would be a lie.
        in_front = sorted({n.pkg for n in nodes if n.pkg})
        raise SystemExit(f"nothing on screen belongs to {APP_PKG_PREFIX or DEFAULT_PKG}; in front: {', '.join(in_front) or 'nothing'}")
    clickables = [n for n in app_nodes if n.clickable and n.enabled and n.w > 0 and n.h > 0]
    for n in clickables:
        clipping = None
        if n.w < px_min - 1 or n.h < px_min - 1:
            clipping = clipped_by_viewport(n, clickables, px_min, w, h)
            if clipping:
                # `uiautomator` reports VISIBLE bounds: anything half-scrolled out of a list looks
                # small even when it measures fine. This produced two false findings on a real
                # campaign, so it is reported apart from the genuine warning (R8).
                notes.append(
                    f"{n.label() or n.rid.split('/')[-1] or '(unnamed)'} {clipping}, "
                    f"not a small target ({n.w * 160 / dens:.0f}×{n.h * 160 / dens:.0f}dp)"
                )
            else:
                issues.append(f"SMALL TARGET < {min_dp}dp ({n.w * 160 / dens:.0f}×{n.h * 160 / dens:.0f}dp): {n.label() or '(unnamed)'} [{n.x1},{n.y1}][{n.x2},{n.y2}]")
        # A clipped control doesn't show its text in the dump either, so asking whether it has an
        # accessible name tells you nothing.
        named = n.text or n.desc or any((c.text or c.desc) for c in walk_desc(n))
        if not named and clipping is None:
            if n.w < px_min - 1 or n.h < px_min - 1:
                # A control cut off by a half-collapsed bar or a half-scrolled list loses the icon
                # that carries its name from the dump: two app-bar buttons came out "UNNAMED" that
                # were named when expanded (measured). Its size is still a warning above.
                notes.append(
                    f"no name at [{n.x1},{n.y1}][{n.x2},{n.y2}], but it is also smaller than a touch target: probably "
                    "cut off, with its named icon outside the dump — run a11y again with it fully visible"
                )
            else:
                issues.append(f"UNNAMED (icon with no contentDescription): [{n.x1},{n.y1}][{n.x2},{n.y2}] id={n.rid.split('/')[-1]}")
    for n in app_nodes:
        if n.w <= 0 or n.h <= 0:
            continue
        if n.x1 < 0 or n.y1 < 0 or n.x2 > w or n.y2 > h:
            if n.text or n.desc or n.clickable:
                issues.append(f"OFF-SCREEN: {n.label() or n.cls} [{n.x1},{n.y1}][{n.x2},{n.y2}] (screen {w}×{h})")
    for i, a in enumerate(clickables):
        for b in clickables[i + 1:]:
            if a in ancestors(b) or b in ancestors(a):
                continue
            ix = min(a.x2, b.x2) - max(a.x1, b.x1)
            iy = min(a.y2, b.y2) - max(a.y1, b.y1)
            if ix > 4 and iy > 4:
                # A FAB or a floating bar ALWAYS covers the list mid-scroll: that is the
                # design, not a defect. What matters is the END of the scroll, and that is the
                # list's bottom content padding, not this check.
                if floats_over_a_list(a, b):
                    notes.append(f"{described(a)} floats over {described(b)} (it scrolls underneath)")
                else:
                    # A card floating over a map on purpose looks exactly like a mistake to this check
                    # (measured): the warning stays, and says what to ask before filing it.
                    issues.append(f"OVERLAP: {described(a)} ↔ {described(b)} ({ix}×{iy}px) — if one floats there on "
                                  "purpose (a card over a map), it's a design question for EYE, not a defect")
    print(f"a11y: {len(issues)} warnings (density {dens}, screen {w}×{h})")
    for line in issues:
        print("  " + line)
    for line in notes:
        print("  · " + line)
    return issues


def described(n):
    """Enough to find a node again: its name, or its class and id — and always its bounds. "OVERLAP: ? ↔ ?"
    named nothing to look for, four times on one screen (measured)."""
    name = shown(n) or f"{n.cls.split('.')[-1] or 'node'}{' id=' + n.rid.split('/')[-1] if n.rid else ''}"
    return f"{name} [{n.x1},{n.y1}][{n.x2},{n.y2}]"


def walk_desc(n):
    for c in n.children:
        yield c
        yield from walk_desc(c)


def scroll_container(n):
    for p in ancestors(n):
        if p.scrollable:
            return p
    return None


def family(n):
    """Groups controls "of the same kind": one row's overflow button with every other row's."""
    rid = n.rid.split("/")[-1]
    if rid:
        return re.sub(r"_-?\d+$", "_N", rid)
    return f"{n.cls}|{n.parent.cls if n.parent is not None else ''}|{n.desc}"


def clipped_by_viewport(n, clickables, px_min, w, h, margin=2):
    """
    Is [n] small only because it is half out of view?

    `uiautomator dump` reports VISIBLE bounds, so a row half-entering a list, or a chip running off
    the edge, come back clipped even though they measure fine. **Both signals are required**, and
    each one alone gets it wrong:

    - Edge only: a button flush against the right edge that really is 38 dp would be excused.
    - Siblings only: without test tags the family is computed from the class, and unrelated wide
      controls end up covering for the small one. Measured: with this alone, a real 38 dp finding
      stopped being reported.

    Together they get both cases right: a genuinely small button touches no edge, and the
    half-entered row touches one **and** has whole siblings to compare against.
    """
    container = scroll_container(n)
    edges = [(0, 0, w, h)]
    if container is not None:
        edges.append((container.x1, container.y1, container.x2, container.y2))
    siblings = [o for o in clickables if o is not n and family(o) == family(n)]
    if not siblings:
        return None

    def touches_edge(axis):
        for x1, y1, x2, y2 in edges:
            if axis == "x" and (n.x1 <= x1 + margin or n.x2 >= x2 - margin):
                return True
            if axis == "y" and (n.y1 <= y1 + margin or n.y2 >= y2 - margin):
                return True
        return False

    if n.w < px_min - 1 and max(o.w for o in siblings) >= px_min - 1 and touches_edge("x"):
        return "is half out of view (horizontally)"
    if n.h < px_min - 1 and max(o.h for o in siblings) >= px_min - 1 and touches_edge("y"):
        return "is half out of view (vertically)"
    return None


def floats_over_a_list(a, b):
    """Does one of them float (a FAB, a bar) while the other scrolls underneath it?"""
    return ((scroll_container(a) is None) != (scroll_container(b) is None))


def ancestors(n):
    out = []
    cur = n.parent
    while cur is not None:
        out.append(cur)
        cur = cur.parent
    return out


# ── the app's own store ──────────────────────────────────────────────────────────────────────────
#
# Everything is read through `run-as`, from the app's data folder (the working directory `run-as`
# starts in). SQLite is only one kind of store: settings often live in DataStore or shared_prefs
# files, and WorkManager keeps its queue in `no_backup/`, not `databases/` (measured on a second app,
# where that queue was the STORE oracle that mattered most).

# Words that make a column, key or field a secret. Matched against the PARTS of a name
# (authToken → auth, token), so "author" or "passage" are not hidden.
SECRET_PARTS = {"password", "passwd", "pass", "pwd", "passphrase", "secret", "token", "credential",
                "credentials", "cookie", "auth", "authorization", "bearer", "jwt", "session", "apikey",
                "otp", "totp", "mfa", "refresh", "passcode", "cvv", "oauth",
                "pin",
                # EncryptedSharedPreferences keeps its Tink keysets next to the values
                # (`__androidx_security_crypto_encrypted_prefs_key_keyset__`): Keystore-wrapped, but key
                # material all the same, and `file` printed them whole (measured).
                "keyset"}
SECRET_JOINED = ("apikey", "privatekey", "accesskey", "secretkey", "encryptionkey", "masterkey",
                 "signingkey", "clientkey")
# Project words that are credentials HERE — an NFC card id that signs a driver in, an employee number.
SECRET_PARTS |= {w.lower() for w in (CONFIG.get("android", {}).get("secretKeys") or [])}
JWT_RE = re.compile(r"eyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,}")
ESCAPED_JSON_RE = re.compile(r'\\"(?P<key>[^"\\]+)\\"\s*:\s*(?P<val>\\"(?:[^"\\]|\\[^"])*?\\"|[^,}\]\s\\]+)')
# A value that looks random: 32+ characters mixing lower case, upper case and digits (base64 / opaque
# session ids). Hex-only hashes and UUIDs don't match, so ids and checksums stay readable.
TOKEN_SHAPE_RE = re.compile(r"(?<![\w\-/.])(?=[A-Za-z0-9_\-+/]*[a-z])(?=[A-Za-z0-9_\-+/]*[A-Z])(?=[A-Za-z0-9_\-+/]*\d)[A-Za-z0-9_\-+/]{32,}={0,2}(?![\w\-/.])")
HIDDEN = "<hidden>"


def looks_secret(name):
    flat = re.sub(r"[^a-z]", "", name.lower())
    parts = {p.lower() for p in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", re.sub(r"[_\-.\s]+", " ", name))}
    # Plurals too: a project listed `pin` as its secret word and the log printed `"pins": {…}`
    # (measured). One trailing "s" only — nothing else about the word changes.
    parts |= {p[:-1] for p in parts if p.endswith("s")}
    return bool(parts & SECRET_PARTS) or any(j in flat for j in SECRET_JOINED)


def hide_secret_containers(text):
    """Hides a whole `{…}` or `[…]` whose KEY is secret-looking.

    Key-by-key masking misses the values inside: a log line carried `"pins":{"user":…,"truck":…}` and
    printed every pin in clear, because the inner keys are innocent words (measured). Whatever is
    under a secret key is secret, however deep.
    """
    out, i = [], 0
    for m in re.finditer(r'\\?"(?P<key>[^"\\]+)\\?"\s*:\s*(?=[\[{])', text):
        if m.end() < i or not looks_secret(m.group("key")):
            continue
        open_ch = text[m.end()]
        close_ch = "}" if open_ch == "{" else "]"
        depth, j, in_str, esc = 0, m.end(), False, False
        while j < len(text):
            c = text[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        else:
            continue  # never closed: leave it alone
        out.append(text[i:m.end()])
        out.append(HIDDEN)
        i = j
    out.append(text[i:])
    return "".join(out)


def hide_secrets_in_text(text, inline=False):
    """
    Hides the values of secret-looking keys in the text formats apps actually write — shared_prefs
    XML, JSON, key=value — and any JWT anywhere. Anything else that holds a credential must be read
    by a project-side reader that does the same (R11): the STORE oracle never prints a credential.
    """
    def keyed(pattern, value_group):
        def sub(m):
            value = m.group(value_group).strip('"').strip()
            if not looks_secret(m.group("key")) or value in ("", "true", "false"):  # a flag is not a secret
                return m.group(0)
            s, e = m.span(value_group)
            return m.string[m.start():s] + HIDDEN + m.string[e:m.end()]
        return pattern, sub

    rules = [
        # <string name="auth_token">value</string>
        keyed(re.compile(r'name="(?P<key>[^"]+)"[^>]*(?<!/)>(?P<val>[^<]*)<'), "val"),
        # <string name="token" value="…" />
        keyed(re.compile(r'name="(?P<key>[^"]+)"[^>]*?value="(?P<val>[^"]*)"'), "val"),
        # "password": "…"   /   "token": 123
        keyed(re.compile(r'"(?P<key>[^"]+)"\s*:\s*(?P<val>"(?:[^"\\]|\\.)*"|[^,}\]\s]+)'), "val"),
        # password=…   /   token: …
        keyed(re.compile(r'^(?P<ind>\s*)(?P<key>[\w.\-]+)\s*[=:]\s*(?P<val>.+)$', re.M), "val"),
        # …inside a log line: nfcId=04 a1 b2 c3, token: abc — a hex id with spaces is one value.
        # `&` ends a value too: a form body is `grant_type=refresh&refresh_token=abc` on one line.
        keyed(re.compile(r'(?P<key>\b[A-Za-z][\w.\-]*)\s*[=:]\s*(?P<val>(?:[0-9A-Fa-f]{2}(?:[ :][0-9A-Fa-f]{2})+)|[^\s,;&}\]"\'<]+)'), "val"),
    ]
    # An HTTP auth header: the credential follows a scheme word, so the key/value rules hide the
    # scheme and print the credential (measured on `Authorization: Token <40 hex>`, which no shape
    # rule catches). Everything after the colon goes.
    text = re.sub(r'(?i)\b((?:proxy-)?authorization|x-api-key|cookie|set-cookie)(\s*[:=]\s*)\S[^\r\n]*',
                  lambda m: m.group(1) + m.group(2) + HIDDEN, text)
    # JSON stored INSIDE a string — {"user": "{\\"sessionId\\":\\"…\\"}"}, a common Multiplatform
    # Settings / SharedPreferences shape: the outer key "user" looks harmless and the session id inside
    # printed (measured). Same rules on the escaped form, and tokens hidden by their SHAPE too.
    text = ESCAPED_JSON_RE.sub(lambda m: m.group(0) if not looks_secret(m.group("key")) or not m.group("val").strip('\\"')
                               else m.group(0)[:m.start("val") - m.start()] + HIDDEN, text)
    text = TOKEN_SHAPE_RE.sub(HIDDEN, text)
    text = hide_secret_containers(text)
    if inline:
        # A log message: "key = rest of the line" is not a value here — "token: <jwt>, user=John" hid the
        # user too (measured on a fake log). Only the in-line rule and the structured ones apply.
        rules = rules[:3] + rules[4:]
    for pattern, sub in rules:
        text = pattern.sub(sub, text)
    return JWT_RE.sub(HIDDEN, text)


def store_path(alias, table, what):
    """
    alias → path relative to the app's data folder. A bare file name in `databases` means
    `databases/<name>`; anything with a `/` is already relative to the data folder
    (`no_backup/androidx.work.workdb`, `files/datastore/settings.preferences_pb`).
    """
    if alias in table:
        value = table[alias]
    elif "/" in alias or (what == "database" and alias.endswith(".db")) or not table:
        value = alias
    else:
        # A typo'd alias used to become a file name and end in "has that screen been opened yet?"
        # — a wrong diagnosis is worse than none (R8).
        raise SystemExit(f"unknown {what} alias {alias!r}; configured in qa.config.json: {', '.join(sorted(table))}")
    return f"databases/{value}" if what == "database" and "/" not in value else value


def require_run_as(pkg):
    probe = adb("shell", "run-as", pkg, "id", check=False, with_stderr=True).strip()
    if "uid=" not in probe and not probe.startswith("run-as:"):
        raise SystemExit(f"could not run as {pkg}: {probe or 'no answer from the device'}")
    # Every refusal starts with "run-as:" — measured: "package not debuggable", "package not an
    # application", "unknown package". Matching one phrase missed the others (R8: my first version
    # did exactly that, and the smoke test caught it).
    if probe.startswith("run-as:"):
        raise SystemExit(
            f"{probe} — the STORE oracle needs a debuggable build (or root). "
            "Install the debug variant, or point --pkg at it."
        )


def read_app_file(rel, pkg):
    """The bytes of a file in the app's data folder, or None when it is not there."""
    data = adb("exec-out", "run-as", pkg, "cat", rel, binary=True, check=False)
    # A refusal or a missing file comes back as TEXT on this channel; written to disk it becomes
    # "file is not a database" — measured. Never take it for content.
    if not data or data.startswith((b"cat:", b"run-as:")) or b"No such file" in data[:200]:
        return None
    return data


def list_app_files(pkg, folder="."):
    """(size, path) of every file under `folder` in the app's data folder, or [] when it is not there."""
    out = adb("shell", "run-as", pkg, "find", folder, "-type", "f", "-exec", "stat", "-c", "'%s %n'", "{}", "+",
              check=False, with_stderr=True)
    rows = []
    for line in out.splitlines():
        m = re.match(r"(\d+) (\.?/?.+)$", line.strip())
        if m:
            rows.append((int(m.group(1)), m.group(2)[2:] if m.group(2).startswith("./") else m.group(2)))
    return rows


def not_there(rel, pkg):
    """What to say when a store is missing: the facts — it is not there, and here is what is."""
    folder = rel.rsplit("/", 1)[0] if "/" in rel else "."
    near = [p for _, p in list_app_files(pkg, folder) if not p.endswith(("-wal", "-shm", "-journal", ".lck"))]
    return (f"{rel} is not in {pkg}'s data folder. In {folder}/: {', '.join(near[:20]) or 'nothing (empty, or no such folder)'}. "
            "`ui.py files` lists every file the app has.")


def pull_db(alias, pkg=DEFAULT_PKG):
    """
    Copies one of the app's SQLite databases to a temp dir, **including its `-wal`** — without it you
    read stale rows, which is one of the ways a QA run quietly lies to you.
    """
    rel = store_path(alias, DBS, "database")
    require_run_as(pkg)
    tmp = tempfile.mkdtemp(prefix="qa_db_")
    name = os.path.basename(rel)
    for suffix in ("", "-wal", "-shm"):
        data = read_app_file(rel + suffix, pkg)
        if data:
            with open(os.path.join(tmp, name + suffix), "wb") as f:
                f.write(data)
    path = os.path.join(tmp, name)
    if not os.path.exists(path):
        shutil.rmtree(tmp, ignore_errors=True)
        raise SystemExit(not_there(rel, pkg))
    return path


def query(path, sql):
    """Runs `sql` on a local SQLite file and prints it, with secret-looking columns hidden (R11).

    Read-only, and it says so: an `update`/`delete` used to run against the **temp copy** pulled from
    the device and print nothing, so it looked like a write that worked and changed nothing (audit).
    """
    if any(looks_secret(t) for t in re.findall(r"[A-Za-z_]\w*", sql)) and " as " in sql.lower():
        raise SystemExit("a secret-looking column behind an alias or an expression can't be hidden — "
                         "select it by its own name (R11)")
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        cur = con.execute(sql)
        if cur.description is None:
            raise SystemExit(f"`db` only reads: {sql.split()[0].lower()!r} would change the copy pulled from "
                             "the device, not the app's store. Drive the app to change its data (R10).")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    except sqlite3.Error as e:
        # A typo'd column used to end in a Python traceback; the database's own words are the answer.
        raise SystemExit(f"SQL error: {e} — in: {sql}")
    finally:
        con.close()
    secret = [looks_secret(c) for c in cols]
    # A settings table is `(key, value)`: no column name is secret, and the secret sits in the value
    # of the row whose key says so — `password | hunter2` printed in full (measured).
    key_col = next((i for i, c in enumerate(cols) if c.lower() in
                    ("key", "name", "pref_key", "_key", "setting", "property", "field")), None)
    val_cols = [i for i, c in enumerate(cols) if c.lower() in ("value", "val", "_value", "data", "content")]
    if key_col is not None and val_cols:
        print(f"(a key/value table: the value is hidden on any row whose {cols[key_col]} looks like a secret)",
              file=sys.stderr)
    if any(secret):
        print(f"(values hidden in: {', '.join(c for c, s in zip(cols, secret) if s)} — an empty one shows as empty)",
              file=sys.stderr)
    if cols:
        print(" | ".join(cols))
    for r in rows:
        row_secret = list(secret)
        if key_col is not None and val_cols and looks_secret(str(r[key_col] or "")):
            for i in val_cols:
                row_secret[i] = True
        print(" | ".join(
            "" if v is None or v == "" else HIDDEN if hide else hide_secrets_in_text(str(v))
            for v, hide in zip(r, row_secret)
        ))
    return rows


def db(alias, sql, pkg):
    path = pull_db(alias, pkg)
    try:
        return query(path, sql)
    finally:
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)


def app_file(alias, pkg, out=None):
    """
    Any file the app keeps — DataStore, shared_prefs, a JSON cache. Text is printed with secrets
    hidden; binary is never printed (a Proto DataStore is binary), only copied with --out for the
    project's own reader to decode.
    """
    rel = store_path(alias, FILES, "file")
    require_run_as(pkg)
    data = read_app_file(rel, pkg)
    if data is None:
        raise SystemExit(not_there(rel, pkg))
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "wb") as f:
            f.write(data)
        print(f"{rel} → {out} ({len(data)} bytes). A copy on this computer: never print it whole if it holds a "
              "session (R11), and delete it when done.")
        return
    try:
        text = data.decode("utf-8")
        # A Proto DataStore is valid UTF-8 more often than not — its field markers are control bytes
        # (\x0a, \x12…). Only text with no control characters but tab and newlines counts as text;
        # anything else could be a session printed as if it were settings.
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", text):
            raise UnicodeDecodeError("utf-8", data, 0, 1, "control characters")
    except UnicodeDecodeError:
        raise SystemExit(
            f"{rel} is binary ({len(data)} bytes), so it is not printed. Copy it with --out and decode it with "
            "the project's own reader — which must hide secrets too (R11)."
        )
    # SharedPreferences writes a stored JSON object with its quotes escaped as `&quot;`, so the
    # session inside an innocent key (`user`, `profile`) matched no rule and printed whole
    # (measured). The entities are expanded before hiding, and the file is printed that way.
    print(hide_secrets_in_text(html.unescape(text)))


def mentions_app(line, pkg):
    """The package as a whole name: `com.x.app` must not match a line about `com.x.app.debug`."""
    if APP_PKG_PREFIX:
        return re.search(rf"(?<![\w.]){re.escape(APP_PKG_PREFIX)}", line) is not None
    # Every name `packagePrefix` lists is the app: with the list form only `pkg` was looked for, and a
    # crash of the listed debug variant came out as "0 crashes".
    return any(re.search(rf"(?<![\w.]){re.escape(p)}(?![\w.])", line) for p in {pkg, *APP_PKGS} if p)


def installed(pkg, apk=None):
    """
    What is really installed — and, with --apk, whether it IS that file. Measured: a build failed on
    a second call site, the install step pushed the previous APK, and old code on the device read as
    "the fix does not work". A version name doesn't change between two debug builds; the file's
    fingerprint does. (The base APK is compared; split APKs are not.)
    """
    out = shell("dumpsys", "package", pkg, check=False)
    code = re.search(r"versionCode=(\d+)", out)
    if not code:
        raise SystemExit(f"{pkg} is not installed on this device")
    name = re.search(r"versionName=(\S+)", out)
    updated = re.search(r"lastUpdateTime=([\d-]+ [\d:]+)", out)
    print(f"{pkg} {name.group(1) if name else '?'} (versionCode {code.group(1)}) · installed {updated.group(1) if updated else '?'}")
    if not apk:
        return
    if not os.path.isfile(apk):
        raise SystemExit(f"--apk {apk}: no such file")
    paths = [l.split(":", 1)[1].strip() for l in shell("pm", "path", pkg, check=False).splitlines() if l.startswith("package:")]
    base = next((p for p in paths if p.endswith("/base.apk")), paths[0] if paths else "")
    remote = (shell("sha256sum", base, check=False).split() or [""])[0] if base else ""
    with open(apk, "rb") as fh:
        local = hashlib.sha256(fh.read()).hexdigest()
    # The file's date, not the build's: a build that finds nothing changed leaves the APK untouched,
    # and "built 5 days ago" on a fresh build read as "the device has an old APK" (measured).
    written = datetime.datetime.fromtimestamp(os.path.getmtime(apk)).strftime("%Y-%m-%d %H:%M:%S")
    if not remote:
        raise SystemExit(f"could not read the installed APK's fingerprint ({base or 'no path from pm'})")
    if remote != local:
        raise SystemExit(
            f"the installed app is NOT {apk} (file last written {written}). Install that file — and check that the build "
            "that produced it succeeded — before verifying anything on the device."
        )
    print(f"matches {apk}: same bytes (sha256 {local[:12]}…). The file was last written {written} — "
          "an up-to-date build leaves it untouched, so that date is not the build's")


def running_avds():
    """Running AVD name → its serial this boot (`emulator-<port>`), or None when the port is not on its
    command line. Read from the computer's processes: no emulator is asked, no adb server started."""
    procs = subprocess.run(["ps", "-ax", "-o", "command"], capture_output=True, text=True).stdout.splitlines()
    running = {}
    for line in procs:
        m = re.search(r"(?:^|\s)-avd\s+(\S+)", line)
        if m and ("qemu" in line or "emulator" in line):
            port = re.search(r"(?:^|\s)-port\s+(\d+)", line)
            running.setdefault(m.group(1), f"emulator-{port.group(1)}" if port else None)
    return running


def resolve_device(value):
    """
    A `devices` value → the adb serial it means right now. Either a serial, or `avd:<name>`.

    An emulator's serial is its console port, handed out at boot: `emulator-5554` is "whichever
    emulator started first", not a device. Two campaigns on one computer swapped meaning that way
    (measured) — so an AVD is named by what it is, and its serial is looked up on every command.
    Returns None when that AVD is not running.
    """
    if not value.startswith("avd:"):
        return value
    name = value[4:]
    running = running_avds()
    if name not in running:
        return None
    if running[name]:
        return running[name]
    serials = [l.split()[0] for l in adb("devices", check=False).splitlines()[1:] if l.startswith("emulator-")]
    if len(running) == 1 and len(serials) == 1:
        return serials[0]
    raise SystemExit(
        f"AVD {name} is running, but nothing on its command line says which of {', '.join(serials) or 'the emulators'} "
        "it is. Start it with `-port <even number>` so its serial can be found without asking every emulator."
    )


LOCK_DIR = os.path.expanduser(os.environ.get("QA_LOCK_DIR", "~/.qa-campaign/locks"))
LOCK_STALE_S = 30 * 60


def project_name():
    """
    Who is driving, for the device claim: `campaign` in qa.config.json when set, else the git root of
    the config's folder, else that folder. The folder alone called a second config of the SAME campaign
    (the production app id, for the release process) "another campaign" and refused it (measured).
    """
    if CONFIG.get("campaign"):
        return str(CONFIG["campaign"])
    here = os.path.dirname(CONFIG_PATH) if CONFIG_PATH else os.getcwd()
    try:
        root = subprocess.run(["git", "-C", here, "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True, timeout=10)
        if root.returncode == 0 and root.stdout.strip():
            return root.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return here


def device_key(serial):
    """The AVD behind a serial when it is an emulator (serials change between boots), else the serial."""
    for name, s in running_avds().items():
        if s == serial:
            return f"avd-{name}"
    return f"serial-{serial}"


def read_lock(key):
    try:
        with open(os.path.join(LOCK_DIR, key + ".json")) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def claim_device(serial):
    """
    One campaign drives a device at a time. Every command stamps the device with this project; a
    command from ANOTHER project within 30 minutes of the last stamp is refused. `avds` said
    "running", never "in use": a campaign had to read the process list by hand to know whether the
    other one was driving the shared AVD (measured). `ui.py release` frees it when a campaign stops.
    """
    key = device_key(serial)
    lock = read_lock(key)
    mine = project_name()
    if lock and lock.get("project") != mine and time.time() - lock.get("at", 0) < LOCK_STALE_S:
        ago = int((time.time() - lock["at"]) // 60)
        raise SystemExit(
            f"{key[4:] if key.startswith('avd-') else serial} is in use by another campaign: {lock['project']} "
            f"(last command {ago} min ago). Two campaigns can't drive one device at once — wait for it to stop "
            "(it runs `ui.py release`), or, if that campaign is really over, `ui.py release --force`."
        )
    os.makedirs(LOCK_DIR, exist_ok=True)
    with open(os.path.join(LOCK_DIR, key + ".json"), "w") as fh:
        json.dump({"project": mine, "at": time.time()}, fh)


def release_locks(force=False):
    """Free this project's claims without needing a device.

    Keyed by the lock's `project`, not by a serial: the emulator is usually gone by the time a
    campaign stops, and `release` then refused with "no device reachable" (audit). `--force` frees
    the locks of other projects too — only when that campaign is really over.
    """
    mine, freed = project_name(), []
    for name in sorted(os.listdir(LOCK_DIR)) if os.path.isdir(LOCK_DIR) else []:
        if not name.endswith(".json"):
            continue
        path = os.path.join(LOCK_DIR, name)
        try:
            with open(path) as fh:
                lock = json.load(fh)
        except (OSError, ValueError):
            lock = {}
        owner = lock.get("project", "?")
        if owner != mine and not force:
            print(f"{name[:-5]}: claimed by {owner}, left alone — `release --force` only if that campaign is over")
            continue
        os.remove(path)
        freed.append(f"{name[:-5]} (was {owner})")
    print("released: " + ", ".join(freed) if freed else "nothing to release: this project holds no claim")


def release_device(serial, force=False):
    key = device_key(serial)
    lock = read_lock(key)
    if not lock:
        print("not claimed by anyone")
        return
    if lock.get("project") != project_name() and not force:
        raise SystemExit(f"claimed by {lock['project']}, not by this project — `release --force` only if that campaign is over")
    os.remove(os.path.join(LOCK_DIR, key + ".json"))
    print(f"released (was {lock['project']})")


def avds():
    """
    Every AVD, its Android version and screen, and whether it is ALREADY RUNNING — from the
    computer's processes, without talking to any emulator or starting the adb server. `emulator
    -list-avds` and `adb devices` don't say which AVD is behind which serial; a campaign proposed an
    AVD as free that was another campaign's running emulator (measured).
    """
    home = os.environ.get("ANDROID_AVD_HOME") or os.path.expanduser("~/.android/avd")
    names = sorted(f[:-4] for f in os.listdir(home) if f.endswith(".ini")) if os.path.isdir(home) else []
    if not names:
        raise SystemExit(f"no AVDs in {home} (set ANDROID_AVD_HOME if they live elsewhere)")
    running = {k: v or "running (serial: not on its command line)" for k, v in running_avds().items()}
    for name in names:
        cfg = {}
        path = os.path.join(home, f"{name}.avd", "config.ini")
        if os.path.isfile(path):
            for raw in open(path, errors="replace"):
                if "=" in raw:
                    k, v = raw.split("=", 1)
                    cfg[k.strip()] = v.strip()
        api = re.search(r"android-([\d.]+)", cfg.get("image.sysdir.1", ""))
        size = f"{cfg.get('hw.lcd.width', '?')}×{cfg.get('hw.lcd.height', '?')}"
        state = running.get(name, "not running")
        lock = read_lock(f"avd-{name}") if name in running else None
        if lock and time.time() - lock.get("at", 0) < LOCK_STALE_S:
            state += f" · in use by {os.path.basename(lock['project'])}, last command {int((time.time() - lock['at']) // 60)} min ago"
        print(f"{name:<40} API {api.group(1) if api else '?':<6} {size:<11} {state}")


# ── CLI ──────────────────────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--serial", help="adb serial; overrides ANDROID_SERIAL")
    p.add_argument("--device", help="alias from `devices` in qa.config.json (e.g. phone, tablet)")
    p.add_argument("--pkg", default=DEFAULT_PKG,
                   help="the app to act on; the default is android.package from qa.config.json")
    p.add_argument("--any-app", action="store_true",
                   help="allow input when another app is in front (a share sheet, a browser)")
    p.add_argument("--allow-device-change", action="store_true",
                   help="allow rotate/size/demo/clear-crashes/net changes on a device listed in managedDevices")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("dump"); s.add_argument("--all", action="store_true", help="include nodes with no text")
    in_help = "only inside the item this selector names (e.g. a card's title); refuses when ambiguous"
    s = sub.add_parser("find"); s.add_argument("sel"); s.add_argument("--in", dest="within", help=in_help)
    expect_help = "act only if this selector is on screen; stop otherwise"
    for name in ("tap", "longpress"):
        s = sub.add_parser(name); s.add_argument("sel"); s.add_argument("--index", type=int, default=None)
        s.add_argument("--expect", help=expect_help); s.add_argument("--in", dest="within", help=in_help)
        s.add_argument("--any", action="store_true", dest="allow_any",
                       help="take the first when the selector is several different controls, instead of refusing")
    s = sub.add_parser("watch", help="every label that shows for N seconds — for messages too short for one dump")
    s.add_argument("seconds", type=float); s.add_argument("--until", help="stop as soon as this selector appears")
    s = sub.add_parser("log", help="the running app's log, secrets hidden — never clears the buffer")
    s.add_argument("--lines", type=int, default=300); s.add_argument("--grep")
    s = sub.add_parser("state", help="ON/off of the switch or checkbox a selector names, or the one beside its label")
    s.add_argument("sel")
    s = sub.add_parser("wait"); s.add_argument("sel"); s.add_argument("--timeout", type=float, default=15); s.add_argument("--gone", action="store_true")
    s = sub.add_parser("assert"); s.add_argument("sel"); s.add_argument("--absent", action="store_true")
    s.add_argument("--in", dest="within", help=in_help)
    s = sub.add_parser("scroll-to"); s.add_argument("sel"); s.add_argument("--dir", default="down", choices=["down", "up"]); s.add_argument("--max", type=int, default=12)
    s = sub.add_parser("type"); s.add_argument("text"); s.add_argument("--expect", help=expect_help)
    s.add_argument("--into", help="tap this field first; nothing is typed if the tap is refused")
    s.add_argument("--no-check", action="store_true", help="don't read the field back (it reformats what it gets)")
    s = sub.add_parser("clear"); s.add_argument("sel", nargs="?"); s.add_argument("--n", type=int, default=80)
    s.add_argument("--expect", help=expect_help)
    s = sub.add_parser("key"); s.add_argument("key", help="e.g. ENTER, BACK, DEL, TAB")
    sub.add_parser("back")
    sub.add_parser("show-keyboard", help="a real keyboard when Gboard shows only its stylus pill (Alt+K)")
    s = sub.add_parser("hide-keyboard", help="BACK only if the keyboard is up, and fail if the screen went with it")
    s.add_argument("--expect", help="what must still be on screen afterwards")
    sub.add_parser("launch")
    sub.add_parser("avds", help="every AVD, its Android version and size, which are running and which are in use; touches no device")
    s = sub.add_parser("serial", help="the adb serial a `devices` alias means right now — for project-side scripts")
    s.add_argument("alias")
    s = sub.add_parser("release", help="free the device for another campaign (run it when this one stops)")
    s.add_argument("--force", action="store_true", help="free a device another campaign left claimed")
    s = sub.add_parser("claim", help="refuse if another campaign is driving the device, else stamp it (net.sh uses this)")
    s.add_argument("--changes-device", action="store_true", help="the caller is about to change device-wide settings")
    s = sub.add_parser("installed", help="version and install time; with --apk, exit 1 unless the installed app IS that file")
    s.add_argument("--apk")
    sub.add_parser("stop", help="am force-stop — DISCARDS saved state; for R9 use `kill`")
    sub.add_parser("kill", help="HOME + am kill: process death that keeps saved state (R9)")
    s = sub.add_parser("open"); s.add_argument("url", help="deep link / VIEW intent, delivered to the app")
    s = sub.add_parser("shot"); s.add_argument("name"); s.add_argument("--dir", default="qa-shots")
    s.add_argument("--overwrite", action="store_true", help="replace a screenshot already saved under that name")
    s = sub.add_parser("rotate"); s.add_argument("value", choices=["0", "1", "2", "3", "natural"])
    s = sub.add_parser("size", help="resizable emulator: phone, unfolded or tablet — read back from the window manager")
    s.add_argument("kind", choices=sorted(SIZES))
    s = sub.add_parser("demo"); s.add_argument("state", choices=["on", "off"])
    s = sub.add_parser("a11y"); s.add_argument("--min-dp", type=int, default=48)
    s = sub.add_parser("db", help="SQL on one of the app's SQLite stores; secret-looking columns are hidden")
    s.add_argument("module"); s.add_argument("sql")
    s = sub.add_parser("files", help="every file in the app's data folder, with its size")
    s.add_argument("folder", nargs="?", default=".")
    s = sub.add_parser("file", help="print a text store with secrets hidden, or copy any file with --out")
    s.add_argument("alias"); s.add_argument("--out")
    p_crashes = sub.add_parser("crashes", help="app crashes/ANRs since the last `clear-crashes`")
    p_crashes.add_argument("--all", action="store_true",
                           help="include other processes (the harness itself, the system…)")
    sub.add_parser("clear-crashes")
    for name in sub.choices:
        for flag, dest in (("--device", "device"), ("--serial", "serial"), ("--pkg", "pkg"),
                           ("--allow-device-change", "allow_device_change")):
            if flag == "--allow-device-change":
                sub.choices[name].add_argument(flag, dest=dest, action="store_true", default=argparse.SUPPRESS)
            else:
                sub.choices[name].add_argument(flag, dest=dest, default=argparse.SUPPRESS)
        # On every subcommand, and on the parser itself, so it is accepted before OR after the command:
        # `--any-app` was refused in both places on the commands that didn't define it (measured), and a
        # campaign fell back to raw `adb shell input tap`. SUPPRESS keeps a subcommand's default from
        # overwriting the flag when it was passed up front.
        sub.choices[name].add_argument("--any-app", action="store_true", default=argparse.SUPPRESS,
                                       help="allow input when another app is in front (a share sheet, a browser)")
    a = p.parse_args()
    if CONFIG_PATH is None and a.cmd not in ("avds", "serial", "release"):
        # Before any adb call, so nothing is claimed or driven: without a config there is no package,
        # no device allow-list and no front-app guard, and the harness would drive whatever adb picks
        # (audit). `avds`, `serial` and `release` are the three that make sense without one.
        raise SystemExit(
            f"no qa.config.json found (looked from {os.getcwd()} upwards and in $QA_CONFIG), so `{a.cmd}` would "
            "drive whatever device adb picks, with no package and no allow-list. Copy qa.config.example.json "
            "into the project and fill it in (SKILL.md §2.1 step 6)."
        )
    if CONFIG_PATH and not DEVICES and a.cmd not in ("avds", "serial", "release"):
        print(f"note: no `devices` allow-list in {CONFIG_PATH}: driving whatever adb picks", file=sys.stderr)
    if a.device:
        if a.device not in DEVICES:
            raise SystemExit(f"unknown device alias {a.device!r}; `devices` in qa.config.json has: {', '.join(sorted(DEVICES)) or 'nothing'}")
        serial = resolve_device(DEVICES[a.device])
        if serial is None:
            raise SystemExit(
                f"device {a.device!r} is {DEVICES[a.device]}, which is not running. Starting it is the campaign's to ask (R2)."
            )
        os.environ["ANDROID_SERIAL"] = serial
    if a.serial:
        os.environ["ANDROID_SERIAL"] = a.serial
    if a.cmd == "avds":
        # Setup looks before it asks: this must work with no device, no config and no adb server.
        avds()
        return
    if a.cmd == "serial":
        # Project-side scripts (a store reader, an injector) need the serial too; they put
        # `avd:Resizable_Experimental` straight into ANDROID_SERIAL otherwise (measured).
        if a.alias not in DEVICES:
            raise SystemExit(f"unknown device alias {a.alias!r}; `devices` in qa.config.json has: {', '.join(sorted(DEVICES)) or 'nothing'}")
        serial = resolve_device(DEVICES[a.alias])
        if serial is None:
            raise SystemExit(f"device {a.alias!r} is {DEVICES[a.alias]}, which is not running")
        print(serial)
        return
    global CLAIM
    CLAIM = a.cmd != "release"
    if a.cmd == "release":
        # No device needed: a campaign that has already shut its emulator down still has to free the
        # claim, and `release` used to refuse with "no device reachable" (audit).
        release_locks(a.force)
        return
    require_device()
    changes = a.cmd in DEVICE_CHANGING or (a.cmd == "claim" and a.changes_device)
    if changes and MANAGED and not (a.allow_device_change or os.environ.get("QA_ALLOW_DEVICE_CHANGE")):
        serial = os.environ.get("ANDROID_SERIAL") or subprocess.run([ADB, "get-serialno"], capture_output=True, text=True).stdout.strip()
        names = {serial} | {k for k, v in DEVICES.items() if resolve_device(v) == serial}
        if names & MANAGED:
            raise SystemExit(
                f"refusing: {serial} is in managedDevices — not the campaign's to alter, and this "
                f"{'changes device-wide settings' if a.cmd != 'clear-crashes' else 'clears the device log buffers'}. "
                "Ask the human; --allow-device-change (net.sh: QA_ALLOW_DEVICE_CHANGE=1) once they agree."
            )
    if a.cmd == "claim":
        return
    if a.cmd in INPUT_CMDS and not a.any_app:
        require_app_in_front(a.pkg)
    if a.cmd in ("launch", "installed", "stop", "kill", "open", "db", "files", "file", "crashes", "log") and not a.pkg:
        # R8: with no package these would fail deep inside adb with an unrelated message.
        raise SystemExit(
            f"`{a.cmd}` needs the app package: set android.package in qa.config.json "
            f"(looked from {os.getcwd()} upwards and in $QA_CONFIG) or pass --pkg"
        )

    if a.cmd == "dump":
        for n in dump():
            if a.all or n.text or n.desc or n.rid or n.clickable or n.scrollable:
                print(n)
    elif a.cmd == "find":
        found = find_in(a.sel, a.within) or find_elsewhere(a.sel, a.within)
        for n in found:
            print(n)
        if not found:
            # Exit 0 on no match made `find` look like a gate: a wait loop built on it reported a
            # message over a blank screen (measured). Like grep, nothing found is exit 1.
            raise SystemExit(f"no match: {a.sel!r}")
    elif a.cmd in ("tap", "longpress"):
        tap(a.sel, a.index, long=a.cmd == "longpress", expect=a.expect, within=a.within,
            allow_any=a.allow_any)
    elif a.cmd == "wait":
        wait(a.sel, a.timeout, a.gone)
    elif a.cmd == "watch":
        watch(a.seconds, a.until)
    elif a.cmd == "log":
        app_log(a.pkg, a.lines, a.grep)
    elif a.cmd == "state":
        state(a.sel)
    elif a.cmd == "assert":
        try:
            present = bool(find_in(a.sel, a.within))
        except SystemExit as e:
            if not a.absent or "NOT found:" not in str(e) or str(e).startswith("NOT found: anchor"):
                raise
            present = False
        if present == a.absent:
            raise SystemExit(f"ASSERT FAILED: {a.sel!r} is {'present' if present else 'absent'}")
        print(f"ok: {a.sel} {'absent' if a.absent else 'present'}")
    elif a.cmd == "scroll-to":
        scroll_to(a.sel, a.dir, a.max)
    elif a.cmd == "type":
        type_text(a.text, a.expect, a.into, not a.no_check)
    elif a.cmd == "clear":
        clear_field(a.sel, a.n, a.expect)
    elif a.cmd == "key":
        # `key enter` sent KEYCODE_enter, which the device ignores in silence (audit).
        name = a.key.upper()
        shell("input", "keyevent", name if name.startswith("KEYCODE_") else "KEYCODE_" + name)
    elif a.cmd == "show-keyboard":
        show_keyboard()
    elif a.cmd == "hide-keyboard":
        hide_keyboard(a.expect)
    elif a.cmd == "back":
        shell("input", "keyevent", "KEYCODE_BACK")
        # Whether a BACK leaves a single-activity app can't be known before sending it. Right after, it
        # can: a BACK too many revealed the production app underneath on a work phone (measured). Stop
        # the script there, before anything else is sent.
        if a.pkg and not a.any_app:
            time.sleep(0.8)
            front = app_in_front(a.pkg)
            if not is_ours(front, a.pkg):
                raise SystemExit(
                    f"BACK left the app: {front} is in front now. Nothing else was sent — `ui.py launch` to return."
                )
    elif a.cmd == "installed":
        installed(a.pkg, a.apk)
    elif a.cmd == "launch":
        # `check=False` swallowed monkey's "No activities found to run" and launch said nothing at all
        # on a package that isn't installed (measured by the audit). Read the result back, like `back`.
        shell("monkey", "-p", a.pkg, "-c", "android.intent.category.LAUNCHER", "1")
        time.sleep(1.5)
        front = app_in_front(a.pkg)
        if not is_app(front):
            raise SystemExit(f"`launch` did not bring {a.pkg} to the front: {front or 'nothing'} is there. "
                             "Installed? `installed` says.")
        print(f"launched {a.pkg}")
    elif a.cmd == "stop":
        shell("am", "force-stop", a.pkg)
    elif a.cmd == "kill":
        # HOME first: `am kill` only kills BACKGROUND processes, and that is the point — the system
        # keeps the task's saved state, so the next launch is a restore, not a cold start.
        before = shell("pidof", a.pkg, check=False).split()
        if not before:
            raise SystemExit(f"{a.pkg} is not running — launch it first: `kill` tests a restore, and there is nothing to restore")
        shell("input", "keyevent", "KEYCODE_HOME")
        time.sleep(1.0)
        shell("am", "kill", a.pkg)
        time.sleep(1.0)
        how = "am kill"
        # `am kill` said nothing and left the process alive on API 37.1 (same pid before and after —
        # measured): two process-death checks proved nothing. A debuggable app can kill itself.
        if before[0] in shell("pidof", a.pkg, check=False).split():
            shell("run-as", a.pkg, "kill", "-9", before[0], check=False, with_stderr=True)
            time.sleep(1.0)
            how = "kill -9 through run-as, after `am kill` left it alive"
        after = shell("pidof", a.pkg, check=False).split()
        if before[0] in after:
            raise SystemExit(
                f"{a.pkg} is STILL running (pid {before[0]}) after `am kill` and `kill -9` — the process death "
                "did NOT happen, so a restore can't be tested this way (not debuggable? try `stop`, which is a cold start)."
            )
        again = f"; the system started it again as pid {after[0]} (a service or job) — still a restore" if after else ""
        print(f"killed {a.pkg} (pid {before[0]}, {how}) in the background, saved state kept{again} — launch again to test the restore")
    elif a.cmd == "open":
        # Quoted: adb joins the arguments with spaces and the device's shell re-parses them, so a
        # deep link with `?a=1&b=2` was cut at the `&`, the rest ran as a command, and `open` still
        # printed "opened" (measured).
        out = shell("am", "start", "-W", "-a", "android.intent.action.VIEW", "-d", shlex.quote(a.url), a.pkg,
                    check=False, with_stderr=True)
        if "Error" in out or "does not exist" in out or "Unable to resolve" in out:
            raise SystemExit(f"could not open {a.url!r} in {a.pkg}: {out.strip()}")
        print(f"opened {a.url} in {a.pkg}")
    elif a.cmd == "shot":
        screenshot(a.name, a.dir, a.overwrite)
    elif a.cmd == "rotate":
        rotate(a.value)
    elif a.cmd == "size":
        resize(a.kind)
    elif a.cmd == "demo":
        demo(a.state == "on")
    elif a.cmd == "a11y":
        sys.exit(1 if a11y(a.min_dp) else 0)
    elif a.cmd == "db":
        db(a.module, a.sql, a.pkg)
    elif a.cmd == "files":
        require_run_as(a.pkg)
        rows = list_app_files(a.pkg, a.folder)
        if not rows:
            raise SystemExit(f"no files under {a.folder!r} in {a.pkg}'s data folder")
        for size, path in sorted(rows, key=lambda r: r[1]):
            print(f"{size:>10}  {path}")
    elif a.cmd == "file":
        app_file(a.alias, a.pkg, a.out)
    elif a.cmd == "clear-crashes":
        adb("logcat", "-b", "crash", "-b", "events", "-c")
        print("crash and event buffers cleared")
    elif a.cmd == "crashes":
        # THE APP's only. The crash buffer also collects the harness's own — two concurrent
        # `uiautomator dump` calls give "UiAutomationService … already registered!" — and that used
        # to be reported as if the app had crashed. `--all` shows the whole buffer.
        raw = adb("logcat", "-b", "crash", "-d").strip()
        if a.all:
            crash = raw
        else:
            blocks, current = [], []
            for line in raw.splitlines():
                if "FATAL EXCEPTION" in line and current:
                    blocks.append(current)
                    current = []
                current.append(line)
            if current:
                blocks.append(current)
            crash = "\n".join(
                "\n".join(b) for b in blocks if any(mentions_app(l, a.pkg) for l in b)
            ).strip()
        # /data/anr needs root; ANRs show up in the events buffer instead (`am_anr`).
        anr = "\n".join(
            l for l in adb("logcat", "-b", "events", "-d").splitlines()
            if "am_anr" in l and (a.all or mentions_app(l, a.pkg))
        )
        print(crash or "0 crashes")
        print(anr or "0 ANR")
        sys.exit(1 if crash or anr else 0)


if __name__ == "__main__":
    main()
