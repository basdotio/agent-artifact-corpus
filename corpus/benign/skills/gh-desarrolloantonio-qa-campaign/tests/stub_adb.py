#!/usr/bin/env python3
"""A device that isn't there: the fake `adb` the harness's own tests drive.

Each test describes a device in the environment (`STUB_*`) and this answers the adb calls the harness
makes. Every call is appended to `$STUB_LOG`, so a test can assert what the harness did **not** do —
that a refusal happened before any input was sent, that no shell command ran on a device that was not
on the allow-list.

    STUB_STATE=device|none      what `get-state` says
    STUB_SERIAL                 the serial `get-serialno` and `devices` report
    STUB_FRONT                  package of the resumed activity (the input guard reads it)
    STUB_DUMP                   file served as the `uiautomator dump` XML; unset = the dump fails
    STUB_VALIDATED=yes|no       is there a validated default network
    STUB_AIRPLANE=0|1           `settings get global airplane_mode_on`
    STUB_SETTINGS_LOST=1        that read fails, the way adb over Wi-Fi dies with airplane mode
    STUB_NC=yes|no              does the device have `nc`
    STUB_NC_EXIT                exit code of a plain `nc` connect (0 = the port takes it)
    STUB_NC_APP                 the same, for a probe made through `run-as` (defaults to STUB_NC_EXIT)
    STUB_NC_APP_ERR             what that probe prints when it fails
    STUB_NC_CONTROL             exit code for the control name `run-as` resolves to prove its DNS works
    STUB_HTTP                   the status line the HTTP probe gets back; empty = silence
    STUB_RUNAS=yes|no           is the app debuggable (`run-as <pkg> id`)
    STUB_EMU                    what the emulator console answers (`OK`, `KO: …`)
    STUB_DENSITY                `wm density` output; empty = unreadable
    STUB_DISPLAYS               `dumpsys window displays` output; empty = unreadable
    STUB_WM_SIZE                `wm size` output; empty = unreadable
    STUB_PACKAGES               comma-separated installed packages, for `pm list packages <prefix>`
    STUB_IME                    `dumpsys window InputMethod` output
    STUB_DATA                   a folder served as the app's data folder to `exec-out run-as <pkg> cat <path>`
    STUB_CRASHES                what `logcat -b crash -d` prints; unset = an empty crash buffer
"""
import os
import sys

args = sys.argv[1:]
if os.environ.get("STUB_LOG"):
    with open(os.environ["STUB_LOG"], "a") as fh:
        fh.write(" ".join(args) + "\n")


def out(text="", code=0):
    if text:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")
    sys.exit(code)


def err(text, code=1):
    sys.stderr.write(text + "\n")
    sys.exit(code)


env = os.environ.get
serial = env("STUB_SERIAL", "emulator-5554")

if not args:
    out("Android Debug Bridge version 1.0.41 (stub)")
if args[0] == "get-state":
    out("device") if env("STUB_STATE", "device") == "device" else err("error: no devices/emulators found")
if args[0] == "get-serialno":
    out(serial)
if args[0] == "devices":
    out(f"List of devices attached\n{serial}\tdevice\n")
if args[0] == "emu":
    answer = env("STUB_EMU", "OK")
    out(answer) if answer else out()
if args[0] in ("reverse", "forward", "wait-for-device", "install", "uninstall", "push", "pull"):
    out()
if args[0] == "exec-out" and env("STUB_DATA") and args[1:2] == ["run-as"] and args[3:4] == ["cat"]:
    path = os.path.join(env("STUB_DATA"), args[4])
    if os.path.isfile(path):
        with open(path, "rb") as fh:
            sys.stdout.buffer.write(fh.read())
        sys.exit(0)
    out(f"cat: {args[4]}: No such file or directory", 1)
if args[0] == "exec-out":
    sys.stdout.buffer.write(b"\x89PNG\r\n\x1a\n" + b"\0" * 2048)
    sys.exit(0)
if args[0] == "logcat":
    out(env("STUB_CRASHES", "") if "crash" in args else "")
if args[0] != "shell":
    out()

cmd = " ".join(args[1:])

if cmd.startswith("command -v nc"):
    out("/system/bin/nc") if env("STUB_NC", "yes") == "yes" else out("", 1)
if "nc -w" in cmd:
    # The harness sends the pipeline and appends `; echo exit=$?` itself, so answer like a shell would.
    if "printf" in cmd:                                   # the HTTP probe
        out(env("STUB_HTTP", ""))
    as_app = cmd.startswith("run-as")
    control = env("QA_CONTROL_HOST", "android.com") in cmd
    if control:                                           # the "does any name resolve here" control
        code, why = env("STUB_NC_CONTROL", "0"), "nc: bad address 'android.com'"
    elif as_app:
        code, why = env("STUB_NC_APP", env("STUB_NC_EXIT", "0")), env("STUB_NC_APP_ERR", "nc: connect: Connection refused")
    else:
        code, why = env("STUB_NC_EXIT", "0"), "nc: connect: Connection refused"
    if code != "0":
        sys.stderr.write(why + "\n")
    # With `; echo exit=$?` the shell's own status is echo's (0) and the code is in the output; without
    # it, the caller reads nc's status, so the stub has to exit with it.
    if "echo exit=" in cmd:
        out(f"exit={code}", 0)
    out("", int(code))
if cmd.startswith("dumpsys connectivity"):
    if env("STUB_VALIDATED", "yes") == "yes":
        out("Active default network: 100\n"
            "NetworkAgentInfo{network{100}  Capabilities: NOT_METERED&INTERNET&VALIDATED}\n")
    out("Active default network: none\n"
        "NetworkAgentInfo{network{100}  Capabilities: INTERNET}\n")
if cmd.startswith("settings get global airplane_mode_on"):
    if env("STUB_SETTINGS_LOST") == "1":
        err("error: device 'emulator-5554' not found")
    out(env("STUB_AIRPLANE", "0"))
if cmd.startswith("cmd connectivity airplane-mode"):
    out("Airplane mode " + ("enabled" if cmd.endswith("enable") else "disabled"))
if cmd.startswith("dumpsys activity activities"):
    front = env("STUB_FRONT", "com.example.app")
    out(f"  topResumedActivity=ActivityRecord{{abc u0 {front}/.MainActivity t42}}")
if cmd.startswith("dumpsys window displays"):
    out(env("STUB_DISPLAYS",
            "Display: mDisplayId=0\n  init=1080x2400 420dpi cur=1080x2400 app=1080x2400\n"
            "Display: mDisplayId=1\n  init=1920x1200 240dpi cur=1920x1200 app=1920x1200"))
if cmd.startswith("dumpsys window InputMethod"):
    out(env("STUB_IME", "isVisible=false"))
if cmd.startswith("wm density"):
    out(env("STUB_DENSITY", "Physical density: 420"))
if cmd.startswith("wm size"):
    out(env("STUB_WM_SIZE", "Physical size: 1080x2400"))
if cmd.startswith("pm list packages"):
    prefix = cmd.split()[-1] if len(cmd.split()) > 3 else ""
    installed = [p for p in env("STUB_PACKAGES", "com.example.app").split(",") if p.startswith(prefix)]
    out("\n".join(f"package:{p}" for p in installed))
if cmd.startswith("uiautomator dump"):
    if env("STUB_DUMP") and os.path.isfile(env("STUB_DUMP")):
        out(f"UI hierchary dumped to: {args[-1]}")
    out("ERROR: could not get idle state.")
if cmd.startswith("cat ") and cmd.endswith("qa_ui.xml"):
    out(open(env("STUB_DUMP")).read()) if env("STUB_DUMP") else out("", 1)
if cmd.startswith("run-as ") and cmd.endswith(" id"):
    if env("STUB_RUNAS", "yes") == "yes":
        out("uid=10123(u0_a123) gid=10123(u0_a123)")
    err("run-as: Package 'com.example.app' is not debuggable")
if cmd.startswith("pidof"):
    out(env("STUB_PID", ""))
out()
