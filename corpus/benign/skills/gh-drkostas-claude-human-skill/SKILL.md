---
name: claude-human
description: Use when an assistant has to act on a person's Mac or reach that person on an Android phone, through the claude-human package and @drkostas/expo-ntfy. Covers building and signing the sckshot and vhid_type helpers, the macOS grants each needs and what resets them, capturing the screen or one window, typing a password at the lock screen or into a SecurityAgent password panel with the person's consent, locking the Mac again afterwards, handing one window to the person's phone through the station so they can do a step themselves, delivering ntfy notifications to an Android phone that the OS does not stop, sending a notification to a person from Python or the command line with claude_human.notify, writing a scheduled watcher that tells a person or wakes a running Claude chat when a condition changes, opening a task for a person with claude_human.tasks that is asked once and closed only when a check says it is done, and reading those tasks from a phone app with @drkostas/claude-human-client. Also use it when a capture is black, white or slow, when a window list has empty titles, when typed keys do nothing, when taps from the station do nothing, when phone notifications stop arriving, when someone asks to be told when something happens, or when an agent needs a person for a step it cannot do itself.
---

# claude-human

This skill is for an assistant that works on a Mac a person also uses, and that needs the person now and then. The Python package `claude_human` captures the screen and types where macOS accepts only hardware keys. The npm package `@drkostas/expo-ntfy` brings messages to an Android phone without Firebase. Every rule below came from a failure on a real Mac or a real phone, and the failure catalogue at the end says how each one was caught.

## Rules that come before any command

- Type a password only on the person's own Mac, only for a task the person asked for, and only with an approval for that one use. A stored password that a program types whenever it decides is a program that logs in as the person without asking. Send each request to the person's phone and type only after they approve it.
- The password goes on stdin. Read it from a secret store or from the person's answer and pipe it in. Never pass it as an argument, an environment variable or a log line. The CLI has no option that takes a password, on purpose.
- Observe the result. A command that exits 0 has typed keys, which is not the same as a cleared lock or a closed panel. The functions in `claude_human.unlock` watch the lock bit or the panel, and report failure when it does not change.
- Lock the Mac again with `claude-human relock` when you were the one who opened the lock, and only then.
- Before opening the lock at all, ask whether the work needs the screen. The lock blocks keys and clicks on the console. It does not block a shell process, so command line or network work can run while the Mac stays locked.
- A person grants every macOS permission. Never press a consent pane with synthetic input, never write the TCC database, never answer a consent dialog for the person. Open the pane, tell the person what to choose, and check the result yourself.
- On the phone, wake the screen freely, but never type a PIN or pass the fingerprint step. Those stay with the person.

## Building the helpers

```bash
pip install 'claude-human[macos]'
claude-human build-tools                                   # both helpers into ~/.local/share/claude-human/bin
claude-human build-tools --only sckshot --bundle-id org.example.sckshot --identity "Apple Development: Name (TEAMID)"
claude-human build-tools --only vhid --pqrs-commit <commit>
security find-identity -v -p codesigning                   # which signing identities exist
```

- `build-tools` needs the Xcode command line tools and git. The output folder is `--out`, or `CLAUDE_HUMAN_BIN_DIR`. The CLI finds the helpers there, or through `--sckshot` and `--vhid`, or `CLAUDE_HUMAN_SCKSHOT` and `CLAUDE_HUMAN_VHID`.
- `sckshot` is built as `sckshot.app`, not a bare binary. The Screen Recording list in System Settings accepts only app bundles, so a bare binary can never hold the grant, and ScreenCaptureKit then waits for ever without a prompt.
- Sign `sckshot.app` with a real "Apple Development" identity and keep the bundle id (`--bundle-id`, `CLAUDE_HUMAN_BUNDLE_ID`) the same across builds. macOS ties the grant to the signature. An ad-hoc signature changes on every build, so each rebuild silently loses the grant. `--identity -` signs ad-hoc, `--identity none` skips signing (CI only), and the default `auto` takes the first Apple Development identity and falls back to ad-hoc with a warning.
- `--usage-text` (`CLAUDE_HUMAN_USAGE`) is the text macOS shows when it asks for Screen Recording.
- `vhid_type` speaks to the Karabiner-VirtualHIDDevice daemon, which ships with Karabiner-Elements. It must be compiled against the pqrs client library at the same protocol version as the installed daemon. The default commit matches Karabiner-Elements 15.4.0. After a Karabiner upgrade, find the Karabiner-DriverKit-VirtualHIDDevice submodule commit of the new release and pass it with `--pqrs-commit` (or `CLAUDE_HUMAN_PQRS_COMMIT`). `CLAUDE_HUMAN_PQRS_SRC` names an existing checkout to build from instead of a fresh clone.
- `vhid_type` runs under `sudo -n`, because the daemon's socket is open only to root. Give the user a sudoers rule for the helper's exact path and nothing wider, keep the file owned by root or by the user, and validate the rule set before you rely on it.

```bash
echo "$USER ALL=(root) NOPASSWD: $HOME/.local/share/claude-human/bin/vhid_type" | sudo tee /etc/sudoers.d/vhid_type
sudo chmod 440 /etc/sudoers.d/vhid_type && sudo visudo -c
sudo -n -l "$HOME/.local/share/claude-human/bin/vhid_type"   # prints the path when the rule works, types nothing
```

A sudoers file with mode 0644 is ignored by sudo without any message, so the `chmod 440` matters.

## The macOS grants, and how to check each

| What | Needed by | How to check |
|---|---|---|
| Screen Recording for `sckshot.app` | fast capture | `claude-human screenshot --out /tmp/t.png` prints a size, and the image is not black |
| Screen Recording for the process that lists windows | window titles, the fallback capture | `claude-human windows` shows titles, not empty strings |
| Karabiner driver extension allowed | `vhid_type` | `systemextensionsctl list` shows the Karabiner driver as activated and enabled |
| Full Keyboard Access | `approve` | `defaults read -g AppleKeyboardUIMode` prints 2 or more |
| Automation of another app | any agent that scripts that app | the first call raises a dialog for the person |

- macOS judges a process started by launchd by the binary that runs it, not by the terminal you tested from. The same script captures from a granted terminal and returns nothing from a launch agent. Grant the interpreter or app the agent runs.
- A child process detached from a granted terminal keeps the terminal's grant, so it works until the next reboot and then fails. Treat that as a test, not as a deployment.
- Empty window titles are the reliable sign of a missing Screen Recording grant. macOS redacts titles for a process without it.
- A major macOS upgrade can reset every Screen Recording and Accessibility grant and remove entries from the list. After an upgrade, run the checks above before trusting anything.
- To send the person to the right pane, run `open "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_ScreenCapture"`. The older `com.apple.preference.security?Privacy_ScreenCapture` form opens nothing on recent macOS and reports no error, so confirm which app is in front afterwards.
- A new launch agent that scripts another app (a terminal, for example) raises an Automation consent dialog on its first run. Until the person answers it, every script call to that app that lists windows hangs, from every process. A call that only asks for the app's version still answers, which makes the app look healthy.
- A Homebrew Python upgrade takes away every grant given to Homebrew's Python.app, because Homebrew signs it ad hoc and macOS holds the grant against the hash of that one build (2026-10-10: a dependency install updated python@3.14 and a station lost Screen Recording and Accessibility). `brew pin` does not prevent it. Give each long-running Python program its own signed app instead, and grant that:

  ```bash
  exe="$(claude-human python-app "$HOME/Applications/My Agent.app" --bundle-id dev.example.agent)"
  "$exe" -m my.agent            # the launchd job runs this; the grant is held against the bundle id and certificate
  ```

  It copies Python.app's launcher, links it to the framework through the opt path, and signs it with the first Apple Development identity. It rebuilds only when it is not current, so call it at every install. Do not wrap `exec python3` in a bundle (exec replaces the process image, so python3 is the binary asking) and do not copy bin/python3 into one (same bytes, same verdict).
- A Mac upgrade can also disable Screen Sharing. That matters only for the person's own remote viewing, since Screen Sharing input never reaches the lock screen (see the catalogue).

## Screenshots

```bash
claude-human windows                                        # JSON list of ordinary windows
claude-human screenshot --out shot.png                      # the main display
claude-human screenshot --out app.jpg --app Safari --max-width 1200
claude-human state                                          # {"locked", "auth_prompt", "blocked_by"}
```

```python
from claude_human import screenshot
wid = screenshot.resolve("Safari", None)       # look the id up again on every request
shot = screenshot.frame(wid, max_width=1100)   # (jpeg, width, height), or None
```

- Store an application name, never a window id. A `CGWindowID` changes whenever the app restarts, and a stored id can later reach a different window.
- Use `frame` rather than `capture` in anything that runs unattended. While the session is locked macOS refuses the capture, and the old capture call blocks about 30 seconds and returns black. `frame` returns None at once instead.
- A SecurityAgent password panel sets the same lock bit as the lock screen, while the desktop behind it is live. `auth_prompt()` finds the panel by owner and size (larger than its tiny helper windows, smaller than 70 percent of the display), and `frame` still captures while one is up. The panel is its own window, so a viewer that shows only the task's window never shows it. Poll `auth_prompt()` separately.
- When one window is asked for and its rectangle cannot be found (another desktop, for example), the result is None. Never fall back to the whole screen, because that shows every other window to someone who was given one.
- `blocked_by()` names a system dialog that holds focus. While one is up, synthetic clicks are accepted and delivered nowhere, so stop and look before clicking again.
- macOS 15 and later ask again, every month, whether an app that records the screen without the system picker may keep doing so ("... is requesting to bypass the system private window picker", answered with "Allow For One Month"). The dialog comes up the first time the app captures after the month runs out, so an app that captures only for a remote viewer brings it up when nobody is at the Mac, and from then on every remote click is refused. `capture_approvals()` reads when macOS last asked each app and when it asks again, and `capture_approval_of(approvals, app)` finds one app by bundle id or bundle path. The station's refusal carries the dialog's app as `blocker`, and `QuartzInput(blocked_detail=...)` takes a function of that name, so a caller can say which question is waiting.
- Read the image you captured. A file of the right size can still be black or white.

## Typing at the lock screen and into password panels

The lock screen and SecurityAgent panels take input only from hardware. Synthetic key events, synthetic clicks and Screen Sharing input are all dropped there. The Karabiner virtual keyboard is seen as a physical keyboard, so `vhid_type` can type where nothing else can.

```bash
claude-human state                                  # look first
<approved password on stdin> | claude-human unlock   # only after the person approved this one use
claude-human use-password                           # a Touch ID panel, show its password field
<approved password on stdin> | claude-human approve
claude-human relock                                 # when you opened the lock
```

The password reaches stdin from the approval flow that holds it, never from a store you read
yourself. Piping a keychain item into `unlock` unlocks the Mac with nobody approving it, which is
the thing the first rule above forbids. When the machine has its own approval service (a request
the person answers on their phone, for example), do not call these at all. Ask through that
service, and let it type the password after the person approves.

```python
from claude_human import unlock
ok, detail = unlock.unlock(password)              # (True, "Unlocked.") or (False, reason)
ok, detail = unlock.approve(password)             # refuses with unlock.NO_PROMPT when no panel is up
ok, detail = unlock.relock()                      # watches the lock bit set
```

- `unlock` returns at once when the Mac is not locked, so it never types a password into a live desktop. It wakes the display, taps Shift to show the field, clears the field (Cmd+A, Backspace), types, presses Return, then watches the lock bit. The first keys are often lost while the field takes focus, so it tries a second time. `--attempts` is capped at 2, because every try is a real password entry and wrong entries add a lockout delay.
- The clear step exists because leftover text in the field joined the password and made it wrong.
- On the LocalAuthentication panel, Return does not press OK. Return presses the default button, Space presses the focused button, and the tab order is field, Cancel, OK. So `approve` types the password, Tab, Tab, Space in one burst. That needs Full Keyboard Access, or Tab never reaches the buttons.
- A Touch ID panel opens without a password field. Its default button is "Use Password...", so `use-password` presses Return only, and types nothing.
- `approve` reports success only when the panel closes. A wrong password leaves it open, which is a failure.
- Check the effect of the task in its own source of truth, not in the settings window. A system extension that was approved for removal stays loaded until a reboot, and its toggle in System Settings keeps showing it as on. `systemextensionsctl list` showed the real state.
- `relock` sleeps the display with `pmset displaysleepnow` and watches the lock bit. It locks only when the Mac requires a password right after sleep, which is the Mac's setting, so a failure there is reported, not assumed away.
- Keep the Mac from locking during GUI work. If it locks again mid task, every synthetic click and scroll goes to the lock screen and does nothing, with no error.
- Window managers and placement tools can still list windows on a locked console, but cannot act on them. Clear the lock before placing a window.

- Screen Sharing is not a way past the lock. Its high performance mode drives a separate virtual display, never the console. Its classic mode with the dedicated Screen Sharing password shows a live login window that drops every key it is sent, by design, so that this password cannot be used to guess the login password. Signing in to Screen Sharing with the account name and the account password does attach to that account's session, which is the person's own remote route, not the assistant's.
- To check that the virtual keyboard reaches the system at all without typing a password, read `HIDIdleTime` with `ioreg -c IOHIDSystem` before and after a harmless key. It falls back near zero only when a hardware-class event arrived.

## Handing a window to the person

When a step needs the person (a sign in, a setting only they should change, a choice that is theirs), hand them the window instead of describing it. `claude_human.station` streams one window to their phone and turns their taps into clicks on the Mac.

```bash
claude-human station --app "System Settings"     # token in ~/.config/claude-human/station-token (mode 0600)
claude-human prepare --phase place "System Settings" "open x-apple.systempreferences:com.apple.LoginItems-Settings.extension" "wait 1"
claude-human prepare --phase input "System Settings" "search Login Items"
curl -s -H "Authorization: Bearer $(cat ~/.config/claude-human/station-token)" http://127.0.0.1:8789/health
```

```python
from claude_human.station import Grant, StationAuth, Unavailable, make_server
class TaskAuth(StationAuth):
    def check(self, secret): ...          # Grant(master=False, station=..., holder=...) or None, asked per request
    def app_for(self, grant): ...         # the app's name, None for the whole display, raise Unavailable when unsure
    def perform(self, grant, act, run): return run()       # Spotlight, record who pressed it
    def on_input(self, grant, msg, result): ...            # every handled tap and key
make_server(TaskAuth(), port=8789).serve_forever()
```

- The station listens on 127.0.0.1 and refuses any other address. Reach it from the phone through a proxy that adds its own login and encryption (`tailscale serve`, an SSH tunnel). Never forward the port as it is, because every accepted tap is a real click.
- The token goes in the `Authorization: Bearer` header and nowhere else. The page at `/view` has no secret in it. An app hands the token in with `window.__stationGrant(token)` or a `postMessage` of `{type: "station:grant", grant}`. Never put the token in a URL, a notification or a QR code.
- Give each task its own grant that pins one app, and end it when the task ends. `check` runs on every request, so an ended grant stops at once. Keep one shared master token for your own tools only.
- `app_for` returning None means the whole display. When the answer cannot be found (the database is down), raise `Unavailable`. The station then refuses, which is the only safe answer.
- Text and keys for a named window are refused unless that window is in front (`front_window()`), because they reach whatever window is in front. A tap brings it forward. A scroll is placed inside the named window, because a scroll reaches the window under the pointer.
- Two tasks in two windows of one app need `window_for`: it returns the window id the grant may drive, and the station then shows and drives that window only. When that window has gone the request is refused, never moved to the app's other window. Raise `Unavailable` when it cannot be read, as for `app_for`.
- A pinned app that is not on the visible desktop gets no picture and no taps. A window on another desktop counts as not visible. Bring it to the visible desktop before you hand it over.
- Run `prepare` before the person opens the window. Placement steps (`open`, `wait`) are safe anywhere. Input steps (`activate`, `type`, `key`, `click`, `scroll`, `search`) need the window frontmost on the visible desktop, because macOS sends synthetic keys to the frontmost app. Run them with `--phase input` only when the person is looking at that window, or the keys go into whatever they are doing.
- Read the result of `prepare`. It exits 0 only when its last line is `<app>: still open`. A step the Mac refused (locked, a dialog holding focus, the window not visible) is a failed step.
- A browser that has a JavaScript dialog open in any window answers no AppleScript at all, so `open <url>` for it fails after a few seconds and says so. The dialog belongs to the person, so tell them and never dismiss it for them.
- While the Mac is locked, the picture is withheld and every tap is refused with `locked`. While a system dialog holds focus, taps are refused with `blocked`. Both are shown on the page. Ask the person, or follow the lock screen section above with their approval.
- The station needs Screen Recording (picture and titles) and Accessibility (clicks) for the process that runs it. Check Accessibility with `/health`, whose `trusted` field is the answer from macOS. A test click proves nothing, because a click lands at a point and a window behind another never rises.
- Test the station with a pinned grant for a harmless app and with fake input before you trust it with a real one. The package tests run the server on a free port with a fake screen and a fake input sink.

## A GUI task from start to end

1. Ask whether the task needs the screen. A command, an API or a network call usually does the same job while the Mac stays locked.
2. Run `claude-human state`. Note whether the Mac is locked and whether a panel or a system dialog is up.
3. If it is locked, send the person a request for this one use and wait for the approval. When the machine has its own approval service, that service unlocks after the approval. Otherwise, pipe the approved password into `claude-human unlock` and read its `OK` or `FAIL` line.
4. Keep the Mac awake for the duration (`caffeinate`), and open the task's window where it does not cover the window the person was using.
5. Before each click, capture the window with `screenshot.frame` and read the image. After each click, capture again and confirm the change.
6. Poll `auth_prompt()` the whole time. When a panel appears, capture it with `frame(prompt["wid"])`, show it to the person with the approval request, run `use-password` if it shows no field, then `approve`.
7. Confirm the task's result in its own source of truth.
8. Run `claude-human relock` if you opened the lock, and read its result.

## Notifications on an Android phone

The config plugin writes a Kotlin foreground service that holds the ntfy WebSocket and posts each message to the tray, a receiver that starts it after a reboot or an app update, and the manifest entries. It runs at prebuild, because `expo prebuild --clean` regenerates `android/` and hand edits there are lost.

```json
{ "expo": { "scheme": "myapp", "android": { "package": "org.example.myapp" },
  "plugins": [["@drkostas/expo-ntfy", { "alertChannelName": "My app" }]] } }
```

```bash
EXPO_PUBLIC_NTFY_URL=https://ntfy.example.org/mytopic npx expo prebuild --platform android --clean
adb devices -l                                                    # pick the phone, not an emulator
PHONE=<serial from adb devices>; PKG=org.example.myapp
adb -s "$PHONE" install -r app-release.apk
adb -s "$PHONE" logcat | grep NtfyService                         # "socket failed" means the address is wrong
adb -s "$PHONE" shell dumpsys notification --noredact | grep "$PKG"   # did a message reach the tray
```

- A socket held in JavaScript stops seconds after the screen locks. The server's subscriber count went from 1 to 0 right after screen off. Only a foreground service keeps the connection without Firebase.
- The topic URL is fixed into the build. A phone built with `localhost` connects to itself and receives nothing, while the app looks healthy. The plugin refuses a loopback, empty or non-http(s) URL at prebuild, and replaces an existing value on every build. Build the phone app with the phone's address, never with the address a web preview on the laptop uses.
- A release build refuses plain HTTP by default. Serve ntfy over HTTPS on an address the phone can reach (a private network is fine), and keep the topic on a server with access control.
- Only one part of the app may post to the tray. With the service and JavaScript both posting, every message arrived twice. `TRAY_IS_NATIVE` keeps the JavaScript glue out of the tray on Android. Count the notification records in `dumpsys notification` to check, rather than trusting one delivery.
- Android 14 and later need the service type in the `startForeground` call as well as in the manifest, or the service crashes on start.
- The service type is `specialUse`, never `dataSync`. Android 15 gives a `dataSync` service 6 hours in any 24, then stops it and refuses to start it again until the person opens the app, so a phone went quiet every afternoon. `adb logcat` shows `ForegroundServiceDidNotStopInTimeException` and then `Time limit already exhausted for foreground service type dataSync`, while the server still reports each message as sent.
- Installing an update stops the app and its service, and nothing restarted it until someone opened the app. The receiver listens for `MY_PACKAGE_REPLACED` for that reason. Test by installing and not opening the app.
- That broadcast does not always arrive. One install on a ColorOS phone left the service stopped for hours while every message was reported as sent. `adb shell dumpsys activity services <package>/.NtfyService` lists a `ServiceRecord` while it runs. Start it without opening the app with `adb shell am broadcast --include-stopped-packages -n <package>/.BootReceiver -a <package>.START_LISTENER`, and read `dumpsys` again a few seconds later. The flag matters, because an app the system force-stopped receives no broadcast without it. Android allows the start from the background while the app is exempt from battery optimization (`logcat` says `Background started FGS: Allowed`). A computer that can reach the phone over adb can run this check every minute.
- Some Android skins stop even a foreground service. On ColorOS, the app's battery setting must be "Allow background activity" (the default "Smart mode" stopped the service within seconds of screen off), and "Allow auto-launch" must be on, or the boot broadcast never arrives. Neither can be changed with adb permission commands. Tell the person, or drive the settings screen yourself if the task allows it.
- ColorOS settings that adb cannot change can still be reached by reading the screen with `adb -s "$PHONE" shell uiautomator dump` and tapping the radio button at the bounds it reports, when the person has asked for the task.
- Before every tap on the phone, bring the target app to the front and confirm it is the resumed activity. Always pass `adb -s`, because an attached emulator can take a bare `adb` command and report success from the wrong device. Find a button by its resource id or exact text in the UI tree, never by a coordinate remembered from an earlier screen.
- ntfy reads `since` as a Go duration with no day unit. `7d` returns 400, `24h` and `all` work.
- A first read adopts the newest position instead of announcing the whole backlog (`newSince` with `ZERO`). ntfy stamps whole seconds, so the read mark also keeps the ids seen at its second.
- `pollTopicOnce` with `registerTopicPoll` is a floor under the service. Android decides when it runs.
- Hermes stores any string with a non-ASCII character as UTF-16 in the bundle. Search for both encodings before you decide a string is missing from a build.

## Sending a notification to a person

`claude_human.notify` publishes to a topic on an ntfy server. It uses only the standard library, and every notifier answers `(ok, detail)` instead of raising when the server is down, slow or refuses the message.

```python
import os
from claude_human import notify

n = notify.NtfyNotifier("https://ntfy.example.org/alerts", token=os.environ.get("NTFY_TOKEN"))
ok, detail = n.notify("Backup failed", "The nightly dump exited 1. The log is attached below.",
                      priority="high", link="myapp://task/42", tags=["warning"])
ok, messages = n.poll("10m")             # what the server holds, to prove the send arrived

floor = notify.FileNotifier("~/.local/state/myapp/notifications.jsonl")
ok, detail = notify.FirstThatWorks(n, floor).notify("Backup failed", "...")
```

```bash
export CLAUDE_HUMAN_NTFY_TOKEN=...       # or CLAUDE_HUMAN_NTFY_USER and CLAUDE_HUMAN_NTFY_PASSWORD
claude-human notify --url https://ntfy.example.org/alerts --title "Backup failed" --priority high "The nightly dump exited 1."
echo "long text" | claude-human notify --url https://ntfy.example.org/alerts --file ~/notify.jsonl -
```

- Record both halves of the answer. A sender that hides its own failure turns "nobody was told" into "nobody knows whether anybody was told". `detail` is the message id on success and the reason on failure.
- A successful send means the message left the Mac. It does not mean the person read it. `poll` shows that the server holds it, and only a receipt from the phone shows it was opened.
- The token and the password come from the environment. The command has no option that takes either, so neither appears in the process list. `--token-env` names a different variable.
- Messages go to the server as JSON. ntfy's header form puts the title in an HTTP header, which Python encodes as latin-1, so a title with a check mark, a Greek word or an emoji used to crash the send.
- Publishing to `127.0.0.1` from the server's own host is correct. A `link`, `attach` or action URL on a loopback address is not, because the phone opens it and reaches itself. Such a message is refused with a reason. `allow_loopback_links=True` turns the check off for a case you have thought about.
- A test run must never reach a person. Set `CLAUDE_HUMAN_NOTIFY_HOLD=1` in the test environment, or pass `hold="test run"`, and every send answers `held` without a request. A program that adds its own rules (quiet hours, muted categories, a daily budget) applies them before it calls `notify`, in one place.
- `poll` turns days into hours, because ntfy reads `since` as a Go duration and answers `7d` with a 400.
- The priority is a name (`min`, `low`, `default`, `high`, `max`, `urgent`) or a number from 1 to 5.

## Watching a condition, then telling someone

A watcher is a short script that a scheduler (launchd, cron, systemd) runs every few minutes. It checks one source (a repository, an inbox, a health check, a deadline) and, only when something changed, sends one signal. The signal goes to a person through `claude_human.notify`, or into a running Claude chat through the claude-ops package (`claude_ops.inject.inject`, or `claude-ops inject --target NAME --text ...`). Decide which before you write the script. A person gets a notification for something they should know or do. A chat gets a prompt for work it should do now.

```python
from pathlib import Path
from claude_ops.watch import State, lock, run_source
from claude_human import notify

with lock(Path("/tmp/repo-watch.lock")) as got:
    if got:
        state = State(Path.home() / ".local/state/repo-watch/state.json")
        tell = notify.watch_sender(notify.from_env(), title="New issues", priority="high")
        run_source(state, "issues", fetch=list_issue_ids, describe=lambda new: f"{len(new)} new issue(s)",
                   target="me", send=tell)          # leave out send= to wake the chat named by target
```

The rules, each from a watcher that went wrong.

- Stay silent when nothing changed. A watcher that sends "nothing new" every five minutes teaches the person to ignore it, and then misses the one message that mattered.
- Advance the state only after the signal was delivered. `run_source` marks items seen only when `send` answers `{"result": "sent"}`, so a closed chat or a failed send offers the same items again next run. `watch_sender` gives a notifier that answer.
- The first run records what is already there and sends nothing, so history is not replayed as news.
- A source that keeps failing (an expired token, a blocked address) sends one alert after a few runs in a row, and nothing more until it works again. Silence from a broken source looks the same as silence from a quiet one.
- Take the lock, so two scheduled runs cannot both send.
- Never send with a loose `osascript -e 'display notification ...'` or `terminal-notifier` call. It ignores quiet hours, mutes and budgets, reaches only the person sitting at the Mac, and leaves no record that it fired. Use one notification path for everything, and add rules to that path.
- A prompt sent into a chat is influence without a gate. Send only text you would trust that chat to act on, and keep secrets out of it. claude-ops records a hash of the text by default, not the text.
- A job that cuts the network it reports over (joining a device's setup network, restarting the network stack) reports after it is back online, never during.

## Asking a person to do a step

When the work needs a person (a permission only they can grant, a sign in, a cable), open a task with `claude_human.tasks`. Do not write the request into the chat and wait. A question in a terminal reaches only someone who is looking at it, and nothing records whether it was done.

```python
from claude_human import notify, tasks

engine = tasks.TaskEngine(tasks.SqliteTaskStore(), notifier=notify.from_env(), link="myapp://task/{id}")
task_id, new = engine.request(
    "connect", "device://backup-disk", "The nightly backup needs its disk.", owner="backup-bot",
    steps="Connect the backup disk to the Mac with its USB cable and wait for it to appear in Finder.",
    verify=["test", "-d", "/Volumes/Backup"])
closed = engine.verify_pending()        # run this on a schedule, or when the person says done
```

```bash
claude-human task open connect device://backup-disk --reason "The nightly backup needs its disk." \
    --steps "Connect the backup disk with its USB cable." -- test -d /Volumes/Backup
claude-human task verify                # `task verify ID` exits 1 while that task is not done
claude-human task comment ID "The disk is at the office today."
claude-human task withdraw ID --reason "The backup moved to the network drive."
```

- Write the check before the task. It is a list of arguments that exits 0 only when the step is really done, and it runs with no shell. A task with no check never closes on its own, so it waits until someone withdraws it.
- A "done" from the person asks for the check. It never closes the task. If the check still fails, tell the person what is still the case in the task's own terms, and leave it open.
- Ask once. A second `request` for the same capability and subject joins the open task and sends nothing. Use a new subject only when it is a different thing.
- Say why a person is needed in `reason`, and give steps a person can follow without asking anything (at least one full sentence, never "see what to do"). The steps are the floor of every chain, so a reader that can show only words still has something to do.
- Add handoffs for what a phone can open (`url`, a station window as `vnc`), best first. The reader sends `supports` and `platform`, the server orders the chain, and the app shows `head` without ranking again.
- Read comments before acting again. A comment does not close a task, and a person who says "the setting is not there" is telling you the steps are wrong.
- Withdraw a task nobody needs any more, with a reason. A task left open for weeks teaches the person to ignore the next one.
- The HTTP server (`claude-human task serve`) listens on 127.0.0.1 only. Put TLS and access control in front of it (`tailscale serve`, for example) to reach it from a phone. Never bind it to the network.
- Tests use a temporary task file and a fake notifier, or set `CLAUDE_HUMAN_NOTIFY_HOLD=1`, so a test run never reaches a person.
- A program with its own records keeps them by implementing `TaskStore` (and `HandoffResolver`, `Authorizer` or `Verifier` when needed) and passing it to `TaskEngine`.

## Reading tasks from an app

An app reads the task server through `@drkostas/claude-human-client` (in `client/`). Use it instead of writing fetch calls by hand, so the routes and the JSON stay the same as the server's.

```ts
import { createTaskClient } from "@drkostas/claude-human-client";

const tasks = createTaskClient({ baseUrl, token, supports: ["steps", "url"], platform: Platform.OS, retries: 1 });
const pending = await tasks.pending();
const ready = await tasks.open(id);     // prepared false means it is not ready, so do not show it as ready
const answer = await tasks.done(id);    // the check decides, and answer.detail says what it saw
```

- Pass the base URL and the token from the app's configuration. Never write a host or a token into the code.
- Send the real platform and only the kinds the app can open. The server orders the chain for that reader, and the app shows `head` without sorting the chain again.
- Show the steps on every task page (`floorSteps(task)`). They are the one thing every reader can do.
- Label the button as a request for the check ("I've done it, check") and show `detail` from the answer. Do not mark the task done in the app.
- Show a refusal from `comment` or `withdraw` (`ok` false) to the person. It is an answer, not an error.
- A program with its own server and more fields extends the types (`interface MyTask extends PendingTask`) and passes them to the call, so nothing it sends is lost to a narrow type.
- An app that uses the client and `@drkostas/expo-ntfy` through `file:` dependencies needs Metro to watch their real folders and `preserveSymlinks` in `tsconfig.json`. `examples/expo-tasks` shows both.
- Tests use a fake `fetch`. The client's own integration test starts the real server on a free loopback port with a temporary task file and a test token, and holds every notification with `CLAUDE_HUMAN_NOTIFY_HOLD=1`.

## Failure catalogue

| Symptom | Cause | How it was caught | Fix |
|---|---|---|---|
| Captures take about 30 seconds each | the old capture call is throttled on recent macOS | timing each call against ScreenCaptureKit | use `sckshot`, keep the old call as fallback |
| ScreenCaptureKit never returns from Python | its async completion does not fire through PyObjC | a probe with a running run loop never saw the callback | the compiled `sckshot` helper |
| `sckshot` hangs with no prompt | a bare or ad-hoc binary cannot hold the grant | `codesign -dv` showed no team id | signed `.app` bundle, stable bundle id |
| Every capture fails, even Apple's | the capture service is wedged system wide | `screencapture -x` failed with "could not create image from display" | a reboot, the fallback serves meanwhile |
| Frames white or invalid JPEG from an agent | image encoding breaks in some launchd contexts | the same code worked from a shell | `sckshot` scales and encodes itself |
| Black frame and a long hang | capture while locked | `claude-human state` said locked | `frame`, which returns None at once |
| Stream blank while a password panel was up | the panel sets the lock bit | the panel showed in the window list | `auth_prompt()` exempts it |
| Window titles empty | no Screen Recording for that process | same script worked from a terminal | grant the agent's interpreter |
| Typed keys reached nothing at the lock screen | synthetic and Screen Sharing input are dropped there | `HIDIdleTime` in `ioreg -c IOHIDSystem` reset only for the virtual keyboard | `vhid_type` |
| `vhid_type` sends but nothing types | helper built for another daemon protocol version | the daemon version did not match the client headers | `--pqrs-commit` of the installed release |
| Password rejected after a failed try | leftover text joined the password | a test field held "GARBAGEtext" | the clear step |
| `approve` typed but the panel stayed | Return does not press OK there | a wrong password plus Tab, Space left it open, Cancel closed it | Tab, Tab, Space |
| A password check accepted any password | passwordless sudo never prompted | a deliberately wrong password returned success | never use sudo to check a password |
| Clicks and scrolls did nothing for an hour | the Mac had locked again | the lock bit, read at last | keep it awake, check `state` first |
| Phone silent once locked | JavaScript socket suspended | server subscriber count fell to 0 | foreground service |
| Phone silent for days | `localhost` baked into the build | `logcat` showed the cleartext refusal for localhost | plugin refuses loopback |
| Every message twice | two parts posted to the tray | two notification records per message | `TRAY_IS_NATIVE` |
| Silent after each update | update stops the service | install without opening, `dumpsys` showed no service | `MY_PACKAGE_REPLACED` receiver |
| Silent after one update, server says sent | the update broadcast did not arrive | `dumpsys` showed no service hours after an install | `START_LISTENER` broadcast, checked every minute |
| Silent every afternoon, server says sent | Android 15 stops a `dataSync` service after 6 hours in 24 | `logcat` showed the timeout and then "Time limit already exhausted" | service type `specialUse` |
| Service dies on one brand of phone | skin battery policy | service gone seconds after screen off | "Allow background activity", auto-launch |
| A tap landed in the wrong app | coordinates reused without foregrounding | a screenshot after the tap | foreground and confirm before every step |
| Taps on the phone did nothing and said nothing | a refused input was reported as success | the Mac was locked while the page showed ok | refusals return `ok: false` and the page shows the reason |
| A tap meant for a task window clicked the person's own screen | a window on another desktop was mapped onto the display | the click landed in the person's browser | a named window that is not visible is refused |
| A grant streamed the whole screen | the app was not found and the capture fell back to the display | the person's notifications appeared on the phone | the stream ends instead |
| "Session expired" seconds after opening | the old token was revoked before the new one reached the page | the server log said why it refused | keep a short handover window for a replaced grant |
| Typed text did not appear in a settings search field | synthetic characters do not reach SwiftUI fields | Command+A visibly worked, the typing did not | paste with Command+V |
| A gesture change did not take effect | the WebView cached the page | the hint text on the page was the old one | serve `/view` with no-store |
| Alerts stopped with a Greek title | ntfy's header form encodes the title as latin-1 | `UnicodeEncodeError` in the sender's log | publish as JSON |
| Every test run sent real notifications | the test asked for a file, but the network sender joined anyway | the person reported alerts about a task that did not exist | `CLAUDE_HUMAN_NOTIFY_HOLD` in the test environment |
| No notifications for weeks, no error | the sender had no topic URL in the process that ran it | the sender said "not configured" from a process whose config file named the URL | read configuration in the module that sends, and record each failure |
| A comment on a task made the task disappear from the person's list | "open" was read as "no event at all", and a comment is an event | the person asked a question about a task and could no longer find it | only a closing event closes a task |
| The person opened the app at once and reported "it has no task" | the list was sorted by risk, then oldest first, so the new task was fourth | the task was there, under three that had waited a day | list open tasks newest first |
