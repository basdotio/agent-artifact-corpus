#!/usr/bin/env bash
# Network modes for a QA campaign.
#
#   net.sh off              no network (airplane mode) — and WAIT until the network is really gone
#   net.sh on               network back — and WAIT until it is validated
#   net.sh slow [edge]      throttled: speed and latency (gprs | edge | umts). Emulator only
#   net.sh full             removes the throttle
#   net.sh status           airplane mode, validated network, speed, and the test server if configured
#   net.sh reach [url]      can the APP reach the test server? DNS, TCP and then HTTP — an open port is
#                           not a server. Default: server.urlFromDevice or server.url in qa.config.json.
#                           Exit 1 when a layer it checked failed, 2 when it could not check at all
#
# Device: `--device <alias>` (from `devices` in qa.config.json), `QA_DEVICE=<alias>`, or ANDROID_SERIAL.
# Exit 1 whenever no device answers: a status printed for a device that is not there is a lie (R8).
#
# Airplane mode via `cmd connectivity airplane-mode`, NOT `svc wifi/data`: poking the radios left an
# emulator with no network at all once, and only a Cold Boot fixed it.
set -euo pipefail

find_adb() {
  local c
  # Same rule as ui.py: a mistyped $ADB used to fall through to PATH — a different adb than the one
  # the project's scripts use, and nothing said so.
  if [ -n "${ADB:-}" ] && [ ! -f "$ADB" ]; then
    echo "\$ADB is '$ADB', which is not a file. Fix it or unset it." >&2; exit 1
  fi
  for c in "${ADB:-}" "$(command -v adb || true)" \
           "${ANDROID_HOME:+$ANDROID_HOME/platform-tools/adb}" \
           "${ANDROID_SDK_ROOT:+$ANDROID_SDK_ROOT/platform-tools/adb}" \
           "$HOME/Library/Android/sdk/platform-tools/adb"; do
    [ -n "$c" ] && [ -x "$c" ] && { echo "$c"; return; }
  done
  echo "adb not found: set \$ADB, put adb on PATH, or set \$ANDROID_HOME / \$ANDROID_SDK_ROOT" >&2; exit 1
}
ADB="$(find_adb)"

# Reads qa.config.json (QA_CONFIG, or upwards from cwd). `config <key>` prints one top-level value
# as JSON (empty when there is no config or no such key); devices' `_` keys are comments.
config() {
  python3 - "$1" <<'PY'
import json, os, sys
key = sys.argv[1]
explicit = os.environ.get("QA_CONFIG")
if explicit and not os.path.isfile(explicit):
    sys.exit(f"QA_CONFIG={explicit} does not exist")
paths = [explicit] if explicit else []
here = os.getcwd()
while True:
    paths.append(os.path.join(here, "qa.config.json"))
    parent = os.path.dirname(here)
    if parent == here: break
    here = parent
for p in paths:
    if p and os.path.isfile(p):
        value = json.load(open(p)).get(key)
        if key == "devices" and isinstance(value, dict):
            value = {k: v for k, v in value.items() if not k.startswith("_")}
        if value: print(json.dumps(value))
        sys.exit(0)
PY
}
DEVICES_JSON="$(config devices)" || exit 1
# `avd:<name>` entries → the serial that AVD has on this boot (its -port on the process list; a lone
# running emulator otherwise). An emulator's serial is only its console port: see ui.py resolve_device.
if [ -n "$DEVICES_JSON" ]; then
  DEVICES_JSON=$(ADB="$ADB" python3 -c '
import json, os, re, subprocess, sys
devices = json.loads(sys.argv[1])
procs = subprocess.run(["ps", "-ax", "-o", "command"], capture_output=True, text=True).stdout.splitlines()
running = {}
for line in procs:
    m = re.search(r"(?:^|\s)-avd\s+(\S+)", line)
    if m and ("qemu" in line or "emulator" in line):
        p = re.search(r"(?:^|\s)-port\s+(\d+)", line)
        running.setdefault(m.group(1), "emulator-" + p.group(1) if p else None)
out = {}
for alias, value in devices.items():
    if not value.startswith("avd:"):
        out[alias] = value
        continue
    name = value[4:]
    serial = running.get(name)
    if name in running and serial is None:
        listed = subprocess.run([os.environ["ADB"], "devices"], capture_output=True, text=True).stdout.splitlines()[1:]
        serials = [l.split()[0] for l in listed if l.startswith("emulator-")]
        if len(running) == 1 and len(serials) == 1:
            serial = serials[0]
        else:
            sys.exit("AVD %s is running but its serial is not on its command line: start it with -port <even number>" % name)
    out[alias] = serial or "not-running:" + name
print(json.dumps(out))
' "$DEVICES_JSON") || exit 1
fi

# --device <alias> → ANDROID_SERIAL, in any position (`net.sh off --device qa` too, like ui.py). A driver
# that put it after the command got a refusal it didn't check, and carried on "offline" while online.
args=()
while [ $# -gt 0 ]; do
  if [ "$1" = "--device" ]; then
    [ -n "${2:-}" ] || { echo "--device needs an alias from \`devices\` in qa.config.json" >&2; exit 1; }
    export QA_DEVICE="$2"; shift 2
  elif [ "$1" = "--allow-device-change" ]; then
    # It was not parsed at all: on `slow` it was taken as the throttle profile, and the run carried on
    # believing the network was throttled (audit).
    export QA_ALLOW_DEVICE_CHANGE=1; shift
  else args+=("$1"); shift; fi
done
set -- ${args[@]+"${args[@]}"}
if [ -n "${QA_DEVICE:-}" ]; then
  serial=$(python3 -c '
import json, sys
alias, devices = sys.argv[1], json.loads(sys.argv[2] or "{}")
if alias in devices and devices[alias].startswith("not-running:"):
    sys.exit("device %r is AVD %s, which is not running. Starting it is the campaign'"'"'s to ask (R2)." % (alias, devices[alias][12:]))
if alias in devices:
    print(devices[alias])
else:
    listed = ", ".join(sorted(devices)) or "nothing"
    sys.exit("unknown device alias %r; `devices` in qa.config.json has: %s" % (alias, listed))
' "$QA_DEVICE" "$DEVICES_JSON") || exit 1
  export ANDROID_SERIAL="$serial"
fi

if ! "$ADB" get-state >/dev/null 2>&1; then
  echo "no device reachable (ANDROID_SERIAL=${ANDROID_SERIAL:-unset})" >&2
  "$ADB" devices >&2 || true
  exit 1
fi

# Once `devices` lists anything, it is the allow-list: with one device attached adb picks it without
# being asked, and that device can be someone's work phone.
if [ -n "$DEVICES_JSON" ]; then
  serial_now="$("$ADB" get-serialno | tr -d '\r')"
  python3 -c 'import json, sys; sys.exit(0 if sys.argv[2] in json.loads(sys.argv[1]).values() else 1)' \
      "$DEVICES_JSON" "$serial_now" || {
    echo "refusing ${serial_now:-the connected device}: it is not in \`devices\` in qa.config.json ($DEVICES_JSON)." >&2
    echo "The campaign never touches a device it was not given — pass --device <alias>, or add it to the list." >&2
    exit 1
  }
fi

# One campaign drives a device at a time: net.sh cuts the network for everyone on that device, so it
# claims the device the same way every ui.py command does (see ui.py claim_device).
case "${1:-status}" in
  on|off|slow|full) python3 "$(dirname "$0")/android/ui.py" claim --changes-device || exit 1 ;;
  *) python3 "$(dirname "$0")/android/ui.py" claim || exit 1 ;;
esac

# "There is really a network" = the default network exists AND is VALIDATED. A `grep VALIDATED`
# over the whole dump gives false positives: stale networks and *requested* capabilities show up
# too (measured: with airplane mode on, it said yes).
validated() {
  local dump net
  dump=$("$ADB" shell dumpsys connectivity 2>/dev/null | tr -d '\r')
  net=$(printf '%s\n' "$dump" | sed -n 's/^Active default network: *//p' | head -1)
  [ -n "$net" ] && [ "$net" != "none" ] || return 1
  printf '%s\n' "$dump" | grep -E "NetworkAgentInfo.*network\{$net\}" | grep -q "VALIDATED"
}

# The test server as the device sees it: the argument, else server.urlFromDevice, else server.url.
server_url() {
  if [ -n "$1" ]; then echo "$1"; return; fi
  python3 -c '
import json, sys
s = json.loads(sys.argv[1] or "{}")
print(s.get("urlFromDevice") or s.get("url") or "")
' "$(config server)"
}

# "The device has internet" says nothing about the test server: an emulator with a validated network
# could not open a connection to a LAN server the computer reached fine (measured: "No route to host").
# Only a connection from the device itself answers it.
#
# And a connection is not a conversation. `reach` used to stop at the open port: measured on API 37, an
# `adb reverse` port whose other end had nothing listening took the connection and exited 0, so `reach`
# printed "server reachable" with no server anywhere. It now goes up the layers — DNS, TCP, then HTTP —
# and says which ones it proved and from where.
#
# The device has no HTTP client to do that with: measured on an API 37 emulator, `curl`, `wget` and
# `openssl` are all missing and only `nc` is there. So HTTP is spoken by hand over `nc` against a plain
# http:// server, and for https:// the layers above TCP are checked from THIS COMPUTER and labelled as
# such — a handshake or a certificate failing with the port wide open is the server's fault, and that
# is the case a TCP-only check calls "reachable".
PROBE_OUT=""; PREFIX=""; PKG=""; WHO="the device's shell user"

# scheme, host, port and path of a url, one line, in that order.
parse_url() {
  python3 -c '
import sys
from urllib.parse import urlsplit
u = urlsplit(sys.argv[1] if "://" in sys.argv[1] else "http://" + sys.argv[1])
if not u.hostname: sys.exit("reach: cannot read a host from %r" % sys.argv[1])
print(u.scheme or "http", u.hostname, u.port or (443 if u.scheme == "https" else 80), u.path or "/")
' "$1"
}

# Ask AS THE APP when it is debuggable: the shell user's network is not the app's. Measured on API 37:
# the shell connected to 10.0.2.2 while the app's own uid timed out on the same address.
as_the_app() {
  PREFIX=""; PKG=""; WHO="the device's shell user"
  local pkg
  pkg=$(python3 -c 'import json, sys; print(json.loads(sys.argv[1] or "{}").get("package", ""))' "$(config android)")
  if [ -n "$pkg" ] && "$ADB" shell run-as "$pkg" id 2>&1 | grep -q "uid="; then
    PREFIX="run-as $pkg "; PKG="$pkg"; WHO="the app ($pkg)"
  fi
}

have_nc() { [ -n "$("$ADB" shell command -v nc | tr -d '\r')" ]; }

# Layers 1-2: can a connection be opened at all? toybox `nc` exits 0 when it connects and 1 with the
# reason otherwise — measured: refused, no route, timeout, unknown host (that last one is the DNS layer
# answering). The reason, when there is one, is left in PROBE_OUT.
tcp_probe() {
  local out
  out=$("$ADB" shell "${PREFIX}nc -w 5 -q 1 $1 $2 </dev/null; echo exit=\$?" 2>&1 | tr -d '\r')
  if [ "${out##*exit=}" = "0" ]; then PROBE_OUT=""; return 0; fi
  PROBE_OUT=$(printf '%s' "${out%exit=*}" | head -1)
  return 1
}

# Layer 3: does anything on that port speak HTTP? Prints the status code, and nothing when the port
# stays silent. `printf … | nc` on its own loses the exchange: stdin closes at once and the connection
# goes down before the answer arrives — through `adb reverse` the request never even reached the server
# (measured). Keeping stdin open for a few seconds brings the status line back, in both directions.
http_probe() {
  local host=$1 port=$2 path=$3 script
  case "$path" in *[!A-Za-z0-9._~/%=?\&+-]*) path="/" ;; esac
  script="(printf \"GET $path HTTP/1.1\r\nHost: $host\r\nConnection: close\r\n\r\n\"; sleep 3) | nc -w 8 $host $port"
  if [ -n "$PKG" ]; then script="run-as $PKG sh -c '$script'"; fi
  "$ADB" shell "$script" 2>&1 | tr -d '\r' | sed -n 's|^HTTP/[0-9.]* *\([0-9][0-9][0-9]\).*|\1|p' | head -1
}

# Layers 3-4 for https, from here, because the device has no TLS client. A 401 or a 404 proves TLS and
# HTTP just as well as a 200: what is being asked is whether the server answers, not whether we are
# allowed in.
tls_http_from_here() {
  python3 - "$1" <<'PY'
import sys, urllib.error, urllib.request
try:
    with urllib.request.urlopen(sys.argv[1], timeout=8) as r:
        print(r.status); sys.exit(0)
except urllib.error.HTTPError as e:
    print(e.code); sys.exit(0)
except urllib.error.URLError as e:
    text = str(getattr(e, "reason", e))
    if "SSL" in text.upper() or "CERTIFICATE" in text.upper():
        print("refused the handshake — %s" % text); sys.exit(1)
    print("no answer from here — %s" % text); sys.exit(2)
except Exception as e:                      # a bad url, a redirect loop: not the device's fault
    print("no answer from here — %s" % e); sys.exit(2)
PY
}

reach() {
  local url fields scheme host port path layers out status rc ok
  url="$(server_url "$1")"
  [ -n "$url" ] || { echo "reach: no url given and no server.url in qa.config.json" >&2; return 2; }
  fields=$(parse_url "$url") || return 2
  read -r scheme host port path <<EOF
$fields
EOF
  if ! have_nc; then
    echo "reach: the device has no nc, so the server cannot be checked from it (which is not the same as unreachable)" >&2
    return 2
  fi
  as_the_app
  ok=0
  if tcp_probe "$host" "$port"; then
    ok=1
  elif [ -n "$PREFIX" ] && "$ADB" shell "nc -w 5 -q 1 $host $port </dev/null" >/dev/null 2>&1; then
    # The shell reaches it and the app does not. That is either the app being blocked — or `run-as`
    # being unable to resolve ANY name, which is not the same thing at all. Measured on an API 37
    # emulator during a campaign: a control name failed from `run-as` exactly like the test server,
    # the shell resolved both, and the app had been talking to the server the whole time — the tool
    # turned "I could not check" into "the app cannot reach it" and sent the campaign after its own
    # defect (R8). So ask the control before accusing anyone.
    case "$PROBE_OUT" in
      *"No address associated"*|*"unknown host"*|*"Name or service not known"*|*"name resolution"*)
        if ! "$ADB" shell "${PREFIX}nc -w 5 -q 1 ${QA_CONTROL_HOST:-android.com} 80 </dev/null" >/dev/null 2>&1; then
          echo "note: NOT PROVEN as the app — \`run-as $PKG\` resolves no name on this device (the control" >&2
          echo "   ${QA_CONTROL_HOST:-android.com} fails the same way), so nothing about the app's own network can be read" >&2
          echo "   from here. Reporting what the device's shell sees; to prove it as the app, read its traffic (LOG)" >&2
          echo "   or what it stored (STORE)." >&2
          PREFIX=""; PKG=""; WHO="the device's shell user"
          ok=1                      # the shell probe above already succeeded
        fi ;;
    esac
  fi
  if [ "$ok" != 1 ]; then
    echo "⚠️ $WHO cannot connect to $host:$port (${PROBE_OUT:-no answer}). The computer reaching it proves nothing." >&2
    if [ -n "$PREFIX" ] && "$ADB" shell "nc -w 5 -q 1 $host $port </dev/null" >/dev/null 2>&1; then
      echo "   The device's shell DOES reach it, and the app resolves other names fine: the app's own network rules" >&2
      echo "   block that address. For a server on this computer, use \`adb reverse tcp:$port tcp:$port\` and" >&2
      echo "   http://127.0.0.1:$port in the app (measured)." >&2
    else
      echo "   Try another address for the same server first — a VPN or Tailscale name the device already resolves" >&2
      echo "   (measured: LAN IP 'No route to host', Tailscale name reachable) — before building a relay." >&2
    fi
    return 1
  fi
  layers="DNS+TCP ok"
  if [ "$scheme" = "https" ]; then
    out=$(tls_http_from_here "$url") && rc=0 || rc=$?
    case "$rc" in
      0) layers="$layers · TLS+HTTP $out, checked from THIS COMPUTER (the device has no TLS client)" ;;
      1) echo "⚠️ $host:$port takes a connection, but TLS $out (checked from this computer)." >&2
         echo "   An open port is not the server answering: fix the certificate or the handshake before reading" >&2
         echo "   anything the app does with that server." >&2
         return 1 ;;
      *) layers="$layers · TLS+HTTP NOT PROVEN ($out) — only the open port is proven" ;;
    esac
  else
    status=$(http_probe "$host" "$port" "$path")
    if [ -n "$status" ]; then
      layers="$layers · HTTP $status from the server"
    else
      echo "⚠️ $host:$port takes a connection from $WHO but answers no HTTP. An open port is not a server:" >&2
      echo "   a dangling \`adb reverse\` accepts the connection with nothing behind it (measured). Check what is" >&2
      echo "   listening on the other end before trusting an online or an offline result." >&2
      return 1
    fi
  fi
  echo "server reachable from $WHO: $host:$port — $layers"
}

# Airplane mode is Android's state, not the app's: a server on this computer behind `adb reverse`, a
# VPN, or anything on the device itself still answers with the radios off — and a test driven against
# one of those is not an offline test. Ask from the app's side before printing the word.
offline_check() {
  local url fields scheme host port path
  url="$(server_url "")"
  [ -n "$url" ] || return 0
  fields=$(parse_url "$url") || return 0
  read -r scheme host port path <<EOF
$fields
EOF
  have_nc || { echo "   (not checked from the app's side: the device has no nc)" >&2; return 0; }
  as_the_app
  if ! tcp_probe "$host" "$port"; then
    echo "   and $WHO cannot reach $host:$port either (${PROBE_OUT:-no answer}) — offline for the app too"
    return 0
  fi
  case "$host" in
    127.0.0.1|::1|localhost)
      echo "   note: $host:$port still answers — that is the relay or the fake server on this computer, not the" >&2
      echo "   internet. Offline against a fake server is a fine test; say which one the report means." >&2
      return 0 ;;
  esac
  echo "⚠️ airplane mode is on, but $WHO still reaches $host:$port — this is NOT offline for the app" >&2
  echo "   (a VPN, a server on the device or the LAN, or an \`adb reverse\` port). Cut that path too, or say in the" >&2
  echo "   report which server the \"offline\" test was talking to." >&2
  return 1
}

# The emulator console prints "OK" or "KO: …" and exits 0 either way; on a physical device `adb emu`
# fails. Both read as success before.
console_ok() {
  out=$("$ADB" emu $1 2>&1) || { echo "⚠️ \`adb emu $1\` failed: ${out:-no output} — a physical device has no emulator console" >&2; return 1; }
  case "$out" in
    *KO*|*"unknown command"*) echo "⚠️ the emulator refused \`$1\`: $out" >&2; return 1 ;;
  esac
  return 0
}

case "${1:-status}" in
  off)
    "$ADB" shell cmd connectivity airplane-mode enable
    # `off` used to echo the setting and exit 0 whatever the network was doing. A script gating on
    # it was gating on nothing.
    for _ in $(seq 1 10); do
      if ! validated; then
        # "no validated network" is also what adb losing the device looks like — which is exactly what
        # airplane mode does to a phone connected over Wi-Fi (audit). Read the setting back to tell
        # the two apart instead of printing "offline" either way.
        # `|| mode=""`: with `set -e -o pipefail` a failed read would end the script right here,
        # silently — which is the very case this is here to report (measured with a stub adb).
        mode=$("$ADB" shell settings get global airplane_mode_on 2>/dev/null | tr -d '\r') || mode=""
        case "$mode" in
          1) echo "offline (airplane_mode_on=1)"; offline_check || exit 1; exit 0 ;;
          "") echo "⚠️ adb lost the device after enabling airplane mode — connected over Wi-Fi? Nothing can be verified from here." >&2; exit 1 ;;
          *) echo "⚠️ no validated network, but airplane_mode_on=$mode — something else took the network down" >&2; exit 1 ;;
        esac
      fi
      sleep 1
    done
    echo "⚠️ airplane mode is on but a validated network is still there after 10 s" >&2; exit 1
    ;;
  on)
    "$ADB" shell cmd connectivity airplane-mode disable
    # 45 s is enough on an emulator; a physical phone's Wi-Fi took ~70 s (measured): QA_NET_TIMEOUT.
    limit="${QA_NET_TIMEOUT:-45}"
    for _ in $(seq 1 "$limit"); do validated && { echo "network validated"; exit 0; }; sleep 1; done
    serial_now="${ANDROID_SERIAL:-}"      # unset is a normal call, and `set -u` trips on ${unset#…} in bash 4+
    if [ "${serial_now#emulator-}" != "$serial_now" ]; then
      echo "⚠️ network not validated after $limit s — if it persists, Cold Boot the emulator" >&2
    else
      echo "⚠️ network not validated after $limit s. A physical phone's Wi-Fi can take over a minute to come back:" >&2
      echo "   wait and run \`net.sh status\`, or set QA_NET_TIMEOUT=120. The device isn't necessarily broken." >&2
    fi
    exit 1
    ;;
  slow)
    p="${2:-edge}"
    # The console answers "KO: …" on a bad profile and `adb emu` fails outright on a phone; both used
    # to print "throttled" and exit 0, and the campaign believed the network was slow (audit).
    console_ok "network speed $p" && console_ok "network delay $p" || exit 1
    echo "throttled: $p"
    "$ADB" emu network status 2>/dev/null | tr -d '\r' | grep -iE "speed|delay" || true
    ;;
  full)
    console_ok "network speed full" && console_ok "network delay none" || exit 1
    echo "full speed"
    "$ADB" emu network status 2>/dev/null | tr -d '\r' | grep -iE "speed|delay" || true
    ;;
  status)
    echo "airplane_mode_on=$("$ADB" shell settings get global airplane_mode_on | tr -d '\r')"
    validated && echo "network validated: yes" || echo "network validated: no"
    # The emulator reports an unthrottled link as "0 bits/s" — read literally, a dead network, on the
    # same screen that says "validated: yes" (measured). 0 means no limit.
    "$ADB" emu network status 2>/dev/null | tr -d '\r' | grep -iE "speed|delay" \
      | sed -E 's/^( *)(download|upload) speed: *0 bits\/s.*/\1\2 speed: not throttled/' || true
    if [ -n "$(server_url "")" ]; then reach "" || true; fi
    ;;
  reach)
    reach "${2:-}"
    ;;
  *) sed -n '2,14p' "$0"; exit 2 ;;
esac
