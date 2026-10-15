# Harness — the contract

The rules in `SKILL.md` are platform-independent. A **harness** is what makes them executable on
one particular platform.

`android/` is the reference implementation — used on a real release, and proven against a second,
unrelated app with nothing but a different `qa.config.json`. Everything else you write yourself,
and this page is the contract it has to satisfy so that SKILL.md's instructions keep working
unchanged.

## What a harness must provide

Seven capabilities, each behind named commands. If your platform can do these, the process runs on
it. The **Commands** column is the interface SKILL.md and the templates rely on.

| Capability | Why the process needs it | Commands | Android (`ui.py`) | Web | iOS simulator | Desktop |
|---|---|---|---|---|---|---|
| **Enumerate** the current screen as **text** | R3 (inventory), R5 (UI oracle). Text can be asserted on; pixels can't. | `dump` (switches print ON/off beside their label), `find <sel>` (exit 1 when nothing matches), `state <sel>`, `watch <seconds> [--until <sel>]` (for messages too short for one dump) | `uiautomator dump` | DOM / accessibility tree via the driver | `idb ui describe-all --json` (needs `pip install fb-idb`, then `brew tap facebook/fb && brew install idb-companion` — Homebrew asks you to `brew trust facebook/fb` first); or XCUITest `debugDescription` | platform a11y API |
| **Act** | driving the app at all, and **gating** a script on what it sees | `tap`, `longpress`, `type`, `clear` (each with `--expect <sel>`; `type --into <sel>` taps the field first and types nothing if that tap is refused, and every `type` reads the field back and fails when the text differs, unless `--no-check`; `tap` refuses a label whose nearest clickable covers half the screen: act only on that screen; every input command refuses when another app is in front, unless `--any-app`), `--in <sel>` on tap/longpress/find/assert (only inside the item that selector names; refuses when ambiguous), `installed [--apk f]` (is the device running that build?), `key`, `back`, `scroll-to`, `launch`, `open <url>`, `wait <sel> [--gone]`, `assert <sel> [--absent]` (exit 1 when wrong), `show-keyboard`, `hide-keyboard [--expect <sel>]` (BACK only if the keyboard is up, and fails if the screen went with it) | `adb shell input`, `am start` | CDP / Playwright | `idb ui tap/text/key/swipe`, `simctl openurl` | a11y actions |
| **Read the local store** | R5 (STORE oracle) — catches optimistic UI lying about what was saved | `db <alias> "<sql>"`, `files`, `file <alias>` — secrets hidden | `run-as` + SQLite, with `-wal`; any file in the data folder | IndexedDB / localStorage via the driver | `simctl get_app_container data` + SQLite | app data dir |
| **Screenshot**, deterministically | R5 (EYE oracle) | `shot <name>` (refuses a name already saved; `--overwrite`), `demo on|off` | `screencap` + frozen status bar | full-page capture | `simctl io screenshot` | window capture |
| **Cut the network** | offline-first processes | `net on|off|status|slow <profile>|full` (a sibling script is fine) — and it must **wait until the change is real**, refusing when it cannot prove it; `net reach` checks the test server **from the device** | airplane mode via `cmd connectivity` | offline mode / proxy | the simulator has **no airplane mode**: cut at the host (Network Link Conditioner 100 % loss, a `pf` rule, a proxy), or give the app under test a launch argument that fails its HTTP layer — that is app code the campaign has to add, not a tool | firewall / proxy |
| **Recreate the UI** without a cold start | R9 — where badly-saved state falls over | `rotate <0-3>` (must read the result back), `size phone|unfolded|tablet` on a resizable emulator (read back too), `kill` (process death that keeps saved state) | `wm user-rotation lock` polled via `dumpsys window`; HOME + `am kill` | reload, bfcache restore | `idb simulate-memory-warning`; `simctl terminate` + relaunch for state restoration; rotation has **no CLI** — AppleScript to Simulator.app, which needs Accessibility permission | window resize, sleep/wake |
| **Read crashes and the log**, filtered to the app | R8 — the harness's own crashes must not be reported as the app's; R5's LOG oracle — where secrets leak | `crashes` (exit 1 when any), `clear-crashes`, `log [--grep text]` (secrets hidden after the grep, never clears) | `logcat -b crash`, filtered by package; `logcat --pid=<pidof app>` | `window.onerror` / console | `idb crash list`, or `~/Library/Logs/DiagnosticReports/<App>-*.ips` by process name (`simctl diagnose` is a multi-minute sysdiagnose, not this) | crash reporter |

### Selector grammar (shared by every harness)

`key=value` pairs separated by spaces, **all** must match: `text=` exact, `text~=` contains
(case-insensitive), `desc=`/`desc~=` accessible description, `id=` test id / resource id (suffix
match), `id~=`, `class=`/`class~=`, and the booleans `clickable= scrollable= enabled= checked=
selected=`. First match wins, but a selector that hits several **different** controls is **refused**,
not guessed: `--index N` names one and `--any` takes the first on purpose. `dump` prints one node per line:
`<flags> text="…" desc="…" id=…  [x1,y1][x2,y2]`; `db` prints `col | col` then one row per line;
`files` prints `size  path`.

### Configuration

Read `qa.config.json` and nothing else. The key names are per platform — see
`qa.config.example.json`; Android reads `android.package`, `android.databases` (alias → SQLite file,
for `db`), `android.files` (alias → path in the data folder, for `file`), `android.secretKeys`,
`android.packagePrefix`, plus `devices` (alias → `avd:<name>` or a serial), `managedDevices` and
`campaign`. Anything project-specific in the script is a bug in the harness.

Before choosing, `avds` (Android) lists every emulator image with its version and whether it is
already running, without touching any device — two campaigns on one computer can't share a running
AVD.

Once `devices` lists anything, it is an **allow-list**: every command refuses a device that is not
on it, even when it is the only one attached. A work phone plugged into the same machine is exactly
the device a default would pick. Emulators go in by AVD (`"avd:<name>"`), resolved to this boot's
serial on every command: a serial is a console port handed out at boot, not a device. `serial
<alias>` prints it for project-side scripts. `claim` takes the device without doing anything else — `net.sh` uses it. Every command also **claims** the device for its
project, and a command from another project within 30 minutes is refused; `release` frees it.

`redcheck.py` (next to `net.sh`) runs one test command and says RED, GREEN or NOT RUN from the JUnit
reports **that run** created or changed — a build error or an up-to-date task is NOT RUN, never the old
report's colour (R6). `--break FILE OLD NEW` (repeatable) makes the break for that run and undoes it
afterwards, checking every file is back byte for byte — also after a timeout or Ctrl-C.

`fake_server.py` (next to `net.sh`) answers every request with the status and body you give it and
prints what the app sent — the error paths of R10 without touching the real server.

**A session that points at the fake server.** Most error paths worth testing — a session that
expires with writes in the queue, a server that answers 500 halfway through a sync — need the app
**signed in to the fake server**, not only cut off from the real one. The harness can't inject a
session (every app stores its own, R11), so add one variant to the project's injection, with an
**invented** account and the fake server's address. Invented values against a local server are
ordinary test input: nothing to hide, nothing to ask.

```bash
python3 harness/fake_server.py --port 18099 --routes routes.json > fake_server.log 2>&1 &   # its request lines are evidence: keep them
# … and when you are done: kill %1   (or pkill -f fake_server.py)
adb reverse tcp:18099 tcp:18099                                      # the app reaches 127.0.0.1, not 10.0.2.2 (R10)
scripts/qa/relogin.sh fake                                          # the project's injection, fake variant
```

The variant is the same injection as the real accounts with two values changed: server
`http://127.0.0.1:18099`, account `qa-fake` / an invented password. A debug build that refuses
cleartext HTTP needs `127.0.0.1` allowed in its debug network-security config — ask before adding
it. Inject a real account again when done: the fake session **replaced** it.

## Rules for the harness itself

**It is under test (R8)** — literally: `tests/run` drives these scripts against a fake `adb`, with no
device and no network, and every case there is something the harness must refuse. Four things follow,
and each cost a session to learn:

1. **Never report a silent all-clear.** No device, no configuration, an unknown alias, a mistyped
   `QA_CONFIG` — the tool must *refuse* and say what is missing, not return "0 warnings" or blame
   the app ("has that screen been opened yet?").
2. **Distinguish what the app did from what you did.** Crashes of the harness, elements clipped by a
   viewport, things that overlap because they float by design — these are reported as **notes**, not
   findings, or filtered out entirely.
3. **Read state back from the system, don't assume it.** A rotation you asked for is not a rotation
   until the window manager says so; a network you cut is not gone until no validated network
   remains.
4. **Never print a secret.** The store the harness reads is where the session lives. Values of
   secret-looking columns and keys come out hidden (an empty one stays empty, so a logout can still
   be checked), and a file the harness cannot read as plain text is never printed at all.

**Prove every harness change in both directions.** The false positives are gone, *and* a real
finding is still caught. Re-introduce one and check.

## Adding a platform

Implement the seven capabilities behind the command names in the table, reading `qa.config.json`
and nothing else, with the selector grammar and exit codes above. Then run the reference
implementation's smoke on it: `dump`, `a11y` on a real screen, `db` on a real store, `rotate` and
`kill` with the result read back, `net off` then `on`, `crashes` after a deliberate crash.

A PR that adds `harness/web/` or `harness/ios/` is the most useful contribution this repo can get.
