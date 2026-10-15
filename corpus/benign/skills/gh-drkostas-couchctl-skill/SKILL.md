---
name: couchctl
description: Take control of the Samsung Tizen televisions and Android TV projectors or boxes on a home network with couchctl. Use when asked to find the screens and their app ids, pair a Samsung set, read or switch power, open apps, press remote keys, send a remote's app buttons to different apps, run the button watcher on an always-on host, install an ad-blocking YouTube client on a TV, or diagnose a screen that reads the wrong state, ignores wake-on-LAN or stops answering adb.
---

# couchctl

couchctl talks to two kinds of screen. A Samsung Tizen set answers plain HTTP on port 8001 and a remote-control websocket on port 8002. An Android TV device (projector, box, Google TV) answers adb on port 5555. Everything else in this skill follows from those two doors and from one fact about both of them. A screen in standby usually leaves the network, so "not answering" and "off" look the same.

Run every check yourself and read its output before you report a step as done. The only steps that need a person are the ones the device itself puts on its own screen (a pairing prompt, an adb trust prompt, a developer menu, a vendor account sign-in).

## Install and the config file

```bash
pip install couchctl
adb version            # needed only for androidtv devices
```

The config is `~/.config/couchctl/config.toml`, or the file named by `$COUCHCTL_CONFIG`, or `--config <path>`. Set `COUCHCTL_ADB` when adb is not on the PATH.

```toml
token_file = "~/.config/couchctl/tokens.json"   # optional, this is the default

[devices.tv-a]
kind = "samsung"
host = "<address>"
mac = "<wifiMac from couchctl info>"              # only for couchctl on

[devices.projector]
kind = "androidtv"
adb = "<address>:5555"                           # or host = "<address>", which adds :5555

[[devices.tv-a.redirect]]
from = "<app id the button opens>"
to = "<app id to open instead>"
name = "Prime Video button to Spotify"           # optional, used in logs
```

Optional Samsung keys are `api_port` (default 8001), `remote_port` (default 8002) and `remote_scheme` (default `wss`). Leave them alone unless a set really differs. Name devices after something stable that the household recognises. A TV name the owner gave in its own settings is better than a guessed room.

Give every screen a fixed address (a DHCP reservation in the router). The config holds addresses, and an address that moves makes a working set look dead.

## Step 1, find the screens

1. List candidate hosts from the router's client list or the local DNS resolver's network table. Prefer a resolver such as Pi-hole, which keeps each client's real hardware address and vendor. A laptop's ARP table often shows only randomised addresses, which hide the vendor.
2. Probe each candidate. A Samsung set that is on answers `curl -s http://<address>:8001/api/v2/` with a JSON description. An Android TV device with network debugging answers `adb connect <address>:5555`.
3. For a Samsung, add the device to the config and run `couchctl info <device>`. It prints `name`, `modelName`, `wifiMac`, `TokenAuthSupport`, `developerMode` and `developerIP`. Copy `wifiMac` into the `mac` key.
4. To tell two identical sets apart, use the `name` each set reports (renaming a set in its own settings is the reliable label), or put one in standby and see which address stops answering. Model numbers differ by screen size even within one product line, which also separates them.
5. For an Android device, `adb -s <address>:5555 shell getprop ro.product.model` names it, and `getprop ro.product.cpu.abi` gives the build an APK must match. Some recent projectors are 32-bit only (`armeabi-v7a`), so check before you install anything.

Proof that this step worked is `couchctl state` printing `on` for every screen that is on in the room.

## Step 2, enable what each device needs

Samsung, for power on. Enable "Power On with Mobile" (on most models under Settings, General, Network, Expert settings). Without it the set ignores wake packets, and `couchctl on` reports `failure` after 25 seconds of trying, because the set never answers.

Samsung, for sideloading only (not needed for couchctl itself). Open Apps, type 1 2 3 4 5 on the remote, set Developer mode to On and set Host PC IP to the address of the machine that runs `sdb`. Then unplug the set for about ten seconds. The power button only sends it to standby, and developer mode is applied only on a full power cycle. The developer port 26101 opens once it is active.

Android TV. Enable developer options (press Build seven times under the device information page), then enable network debugging. On the first `adb connect`, accept the prompt on the screen and tick "Always allow from this computer", or it returns after every reboot. Until then `adb devices` lists the device as `unauthorized`.

## Step 3, pair each Samsung set

```bash
couchctl pair tv-a            # the set must be on
couchctl pair tv-a --again    # forget the held token and ask again
```

The set shows a prompt asking whether to allow a client named couchctl. It appears only while something is connecting, so run the command first and then have the person in the room choose Allow. couchctl waits up to 40 seconds. The token goes into the token file with mode 600. It authorises everything a remote can do, so never print it or copy it into a log.

Outcomes are `success: paired`, `success: already paired`, or `refused` (the prompt was declined or timed out). A set that reports `TokenAuthSupport` other than `"true"` needs no token.

Proof is `couchctl key tv-a KEY_HOME` printing `KEY_HOME sent` and the home screen appearing. Holding a token is not proof. A factory reset or a revoked permission leaves the old string in the file, and the set then answers `the television refused the token`.

## Step 4, everyday control

```bash
couchctl state                     # on, off or unknown for every device
couchctl state --maybe-away        # on a machine that may not be on the screens' network
couchctl on tv-a                   # wake-on-LAN to the configured mac
couchctl off tv-a                  # KEY_POWER on samsung, KEYCODE_POWER on androidtv
couchctl key tv-a KEY_VOLUP        # samsung key names
couchctl key projector KEYCODE_HOME  # android key names or numbers, sent with input keyevent
couchctl launch tv-a 3201606009684
couchctl launch projector com.spotify.tv.android
couchctl front projector           # the package in front
couchctl front tv-a <id> <id>      # which of these Samsung ids is visible
```

`couchctl off` reads the state again first and refuses when the screen is not answering, because on these devices a power key sent to a sleeping screen can wake it. `couchctl on` sends the packet every 2 seconds and reports `success` only once the screen answers, or `failure` after 25 seconds. A set switched off moments earlier is still shutting down for several seconds and ignores a packet sent then, which is why it keeps sending.

On Android, `launch` uses `monkey` with the `LEANBACK_LAUNCHER` category, because TV apps register there and not under the phone launcher. "has no TV launcher activity" means the package has no TV entry point.

## Step 5, find app ids

Samsung store ids are long numbers and are the same on every Samsung set. Sideloaded Tizen apps have ids that start with a prefix taken from the signing certificate, so they differ between sets signed with different certificates. Read the ids from each set.

- `sdb shell 0 vd_applist` (from Tizen Studio, with developer mode on) lists every installed app with its id. On recent firmware `app_launcher -l` and `pkgcmd -l` answer with nothing, so do not trust an empty result from them.
- Without sdb, press the button on the remote and run `couchctl front tv-a <id> <id> ...` with the ids you suspect. `GET http://<address>:8001/api/v2/applications/<id>` returns `running` and `visible` for one id, and answers for any installed app without pairing.
- On Android, press the button and run `couchctl front projector`. Compare whole package names. `com.google.android.youtube.tvmusic` is not `com.google.android.youtube.tv`.

`couchctl front` on a Samsung prints `none of the listed apps` for the home screen and for any app you did not list. It does not mean nothing is on screen.

## Step 6, redirect the app buttons

The app buttons on these remotes cannot be remapped, and time spent trying is wasted. On Tizen the remote websocket only sends (a listener on port 8002 receives the greeting and never a button press), there is no accessibility service, and the dedicated app buttons are missing from the key table an app can register. On the Android TV projectors tested, `adb shell getevent -lq` shows no key event at all for the app buttons, the key layout files are not readable without root, and a key remapper app therefore never sees the press.

What can be seen is the result. Write one `[[devices.<name>.redirect]]` block per button, then test.

```bash
couchctl watch --dry-run           # logs each press, launches nothing
couchctl watch                     # redirects until stopped
couchctl watch tv-a --interval 1
```

Press each button while the dry run is going. Each press logs one line such as `[tv-a] dry-run: Prime Video button to Spotify (would launch the replacement)`. Then run without `--dry-run` and confirm a line ending in `success` and the replacement app on the screen.

What the household sees, and should be told before they see it.

- The original app opens for a second or two before the replacement covers it.
- The watcher acts only when a redirected app becomes visible. A deliberate return to that app is left alone until something else has been in front.
- At start, and when a screen returns after being out of reach, whatever is on screen is taken as the starting point and never as a press. Restarts do not throw anybody out of a programme.
- Some apps retake the foreground a few seconds into their own start. The watcher sees a second appearance and redirects again, so the button still works, with two brief flashes.
- A button that opens no app (a mute toggle, a settings overlay drawn by a service) cannot be redirected reliably. Polling a toggle misses presses that revert between polls. Leave such buttons doing their own job and move the wanted app to a button that opens an app.

## Step 7, keep the watcher running

The redirect works only while the watcher runs on the same network as the screens, so run it on an always-on host, not a laptop that sleeps or roams. A Raspberry Pi on the home network is a good host. `examples/couchctl-watch.service` in the repository is a systemd unit.

```bash
sudo cp examples/couchctl-watch.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now couchctl-watch
journalctl -u couchctl-watch -f    # one "watching <device> every 1.0s" line per device
```

Run exactly one watcher for a set of screens. Two watchers both answer the same press. When moving the watcher to a new host, stop the old one in the same step.

Each device has its own thread, so a set in standby does not delay the others. If adb is missing on the host, the watcher logs that and skips androidtv devices. A watcher started with no `redirect` blocks exits with `no device in the config has a redirect`.

To record each redirect elsewhere, add `--report-url <url>` and optionally `--report-token-env <VARIABLE>`, which sends the variable's value as a bearer token. Each report is JSON with device, from, to, name, outcome, message and time. A failed report is logged and the watcher continues.

To prove the deployed watcher works, wake a screen, open a redirected app with `couchctl launch` from another machine, and confirm the watcher's log shows `success` and the replacement is in front.

## Ad-blocking YouTube on TVs

DNS blocking (Pi-hole and similar) blocks banner and tracker domains, but YouTube serves its ads from its own domains, so DNS cannot remove them. The fix is a different YouTube client, chosen per platform.

- Android TV or Google TV takes SmartTube, or TizenTube Cobalt (the TizenTube author's Android TV port). Install with `adb install`, using the build that matches `ro.product.cpu.abi`.
- Samsung Tizen cannot run Android apps. It takes TizenTube, delivered through TizenBrew, as a signed `.wgt` package sideloaded over `sdb`.

Then redirect the remote's YouTube button to the new client with couchctl, so the household never opens the stock app by habit.

### Signing for Samsung sets

A Samsung set installs only packages signed with a distributor certificate that Samsung issues for that set's DUID (its device id).

1. Install Tizen Studio with the Samsung Certificate Extension, then `sdb connect <address>:26101` for every set you want to cover.
2. In Certificate Manager, create a profile of type Samsung, then TV. Create an author certificate. At the distributor step choose "Create a new distributor certificate" and privilege Public. This step requires a Samsung account sign-in, which the person does, not the agent.
3. Connect all the sets before you create the distributor certificate. The device list is filled from whatever `sdb` sees at that moment, and a set missing from it refuses every package.
4. To add a set later, create a new profile, choose "Select an existing author certificate" at the author step (this avoids a second key and the confusion of two authors), then create a new distributor certificate with every set connected. The edit icon on an existing distributor card only changes which file the profile uses. It does not ask Samsung for a new certificate.
5. Never use the certificates shipped inside `tizen-studio/tools/certificate-generator/`. They look valid in the dialog and every set refuses them.
6. Install with `sdb -s <address>:26101 push <file>.wgt /home/owner/share/tmp/sdk_tools/tmp/app.wgt`, then `sdb -s <address>:26101 shell 0 vd_appinstall <app id> /home/owner/share/tmp/sdk_tools/tmp/app.wgt`. Start it with `shell 0 was_execute <app id>`.
7. Prove it with `sdb shell 0 vd_applist` showing the new ids, and the app appearing on screen after `couchctl launch`.

Routes that fail and cost hours, so skip them. A package signed by its author, the SDK's public or partner certificates, the USB demo package route (its certificate has expired and the service that issued it is closed), and desktop installers that reimplement sdb (they fail against sets that report `secure_protocol:enabled`).

## Device notes

Samsung Tizen sets. Port 8001 answers without pairing and is enough for state, `info`, `front` and `launch`. Keys and power off need the paired websocket on 8002, which uses a self-signed certificate that couchctl does not verify. Power on needs "Power On with Mobile" and a `mac`. The set shell is locked down (no network or Wi-Fi commands), so read network facts from `couchctl info`.

Android TV projectors and boxes. State means "adb answers", which couchctl tests with a real `adb shell echo ok`, not a TCP connect. adb drops a device that enters standby, and couchctl reconnects by itself when it returns. Most of these devices cannot be woken from the network. Some projectors wake only from a Bluetooth signal sent by their own remote or phone app, keep their radio off in standby, and do not expose their hardware address to adb. For those, do not configure a `mac` and do not offer a wake.

## Failure catalogue

| Symptom | Cause | Check | Fix |
|---|---|---|---|
| Every screen reads off while people are watching | This machine is on another network or subnet, so it has no route | Can this machine reach the router of the screens' network | Run couchctl from a host on that network, or use `couchctl state --maybe-away`, which prints unknown |
| An adb device reads on while it is off | adb goes through a forwarded port, whose local end accepts any connection | `couchctl state` (it uses `adb shell echo ok`) | Never judge an adb device by a TCP connect |
| `adb devices` shows a forwarded device as `offline` | Usually the device is in standby, not a broken route | `lsof -i :<local port>` shows the forward still listening | Wait for the device to wake. Restart the forward only if nothing listens |
| `couchctl on` prints success and the set stays dark | "Power On with Mobile" is off, wrong `mac`, or the packet cannot reach the set's segment | `couchctl info` while on, compare `wifiMac` with the config | Enable the setting, copy `wifiMac`, send from a host on the same network |
| Projector never wakes from `couchctl on` | It wakes only over Bluetooth | Its adb port stays closed for hours while other screens answer | Remove its `mac`. Wake it with its own remote |
| `couchctl off` prints refused | The screen is not answering, so it is already off | `couchctl state` | Nothing to do. Do not force a power key |
| `not paired: run couchctl pair` | The set requires a token and none is held | `couchctl info` shows `TokenAuthSupport` | `couchctl pair <device>` with someone at the set |
| `the television refused the token` | Factory reset or revoked permission | Same message on `couchctl key <device> KEY_HOME` | `couchctl pair <device> --again` |
| Pair returns refused with nobody seeing a prompt | Nobody chose Allow within 40 seconds, or the set was off | The set is on and in front of a person | Run pair again while someone watches the screen |
| A Samsung set never answers port 8001 while on | It is on a guest or isolated Wi-Fi, or its IP remote setting is off | Scan the subnet for port 8001, check the set's network page | Join the main network, enable the network remote setting (its name varies by model year) |
| sdb refused although developer mode is on | Developer mode not yet applied, or Host PC IP is wrong | `couchctl info` shows `developerMode` and `developerIP` | Correct Host PC IP, then unplug the set. Treat `developerIP` as a lead, since it can keep showing an old value after the fix |
| `Invalid certificate chain` on install | Package not signed with a Samsung-issued distributor certificate | Which profile signed it | Sign with your own Samsung profile |
| `Invalid format of certificate in signature` | The set's DUID is not in the distributor certificate | The profile's `device-profile.xml` lists its `TestDevice` entries | Re-issue with every set connected to sdb |
| A redirect never fires | Watcher not running, wrong `from` id, or adb missing on the host | `couchctl watch --dry-run` and press the button | Correct the id with `couchctl front`, install adb, run the service |
| A redirect fires on a sideloaded id on one set only | Sideloaded ids carry the certificate prefix | `sdb shell 0 vd_applist` on each set | Give each set its own redirect ids |
| Android launch says no TV launcher activity | The package has no `LEANBACK_LAUNCHER` entry | `couchctl launch <device> <package>` prints the same message | Install the TV build of the app |
| A key remapper app records nothing on a projector | The app buttons never reach the input layer | `adb shell getevent -lq` while pressing shows nothing | Use the couchctl redirect instead |
| The adb trust prompt returns after reboot | "Always allow" was not ticked | `adb devices` shows `unauthorized` | Accept again with the box ticked |
