# AI / developer handoff

Updated: October 13, 2026. Read this alongside README.md and AGENTS.md. This report
describes the repository as published; it is not authorization to operate hardware.

## Purpose and user workflow

The user wants simple Python steps such as `fw(x, 50)` and `bc(z, 10)` and terminal
execution without pauses between every 5 mm segment. They also want FastMCP tools
that accept and return dictionaries. The working transport is SSH to the printer's
local Klipper Unix socket. A cable transport has been discussed but not implemented.

`simple.py` currently contains a 1 mm square, X/Y speed 20 mm/s, Z speed 2 mm/s.
Keep operator edits. The README's 50 mm square is an example, not the shipped plan.

The normal command flow is status → optional explicit mesh CLEAR → full sequence
preview → operator MOVE → remote revalidation → queued execution with watchdog.
`--preview` and status never mutate state. `xy-start` is a separate confirmed entry;
when already in the regular XY area it exits without motion or mesh changes.

## File map and data flow

| File | Responsibility |
| --- | --- |
| `printerctl` | Shell entry point, connection session, friendly action names, venv Python selection. |
| `simple.py` | User-editable speed constants and ordered step list. |
| `simple_runner.py` | Step dictionary helpers, argparse, preview text, CLEAR/LOAD/ENTER/MOVE confirmations. |
| `printer_policy.py` | Pure numeric, state, bounds, rounding, speed and path validation; G-code generation. |
| `printer_client.py` | Mock implementation, SSH transport, checked responses, uncertain-outcome stop request. |
| `printer_watchdog.py` | On-printer socket API, request allowlist, lock, execution monitor and emergency stop. |
| `fastmcp_server.py` | Four async dictionary tools, expiring single-use previews and real-motion gate. |
| `tests/` | Policy, transport, watchdog, CLI flow, Unix-socket and MCP regression tests. |

```text
Terminal / FastMCP
    → SSHPrinter (authenticated shared SSH session)
    → streamed Python policy + watchdog, no firmware installation
    → /tmp/klippy_uds
    → one validated G-code script + repeated status queries
    → dedicated emergency_stop request on a detected execution fault
```

Both the local preview and remote dispatch reconstruct a plan from current state.
A request carries steps, speed(s), and expected start, not arbitrary G-code.
The remote schema rejects extra fields. Targets are rounded to 0.001 mm, feeds to
6 decimal places; both requested and rounded targets are checked. Timeout is
20 + 2 × nominal seconds + 0.1 × step count; sequences exceeding 300 seconds fail.
The nominal duration omits acceleration/cornering time. Up to 1,000 steps are accepted.

## Environment and configuration

- Proven hardware: Ender-3 V3 KE, V1.1.0.17; root SSH was enabled by the operator.
- Host tested with macOS, Python 3.14.7, FastMCP 4.1.0. FastMCP requires Python 3.10+.
- Printer interpreter: `/usr/share/klippy-env/bin/python`, observed Python 3.8.2.
  The streamed policy/watchdog must remain Python 3.8 compatible.
- Klipper API socket: `/tmp/klippy_uds`. Remote sequence lock:
  `/tmp/photonics-simple-motion.lock`. No firmware config is installed/modified.
- Public repository requires `SSH_HOST`; there is no fallback personal IP.
  `SSH_CONTROL_PATH` defaults to `/tmp/photonics-printer-control`.
- `.env.example` is shell configuration to source in both tabs, not automatically
  loaded dotenv configuration. The MCP client needs its own environment settings.
- Terminal defaults to real mode and prompts before mutations. `--mock` prevents
  SSH. FastMCP independently defaults to `PRINTER_MODE=mock`.
- Real MCP execute additionally requires `PRINTER_ALLOW_MOTION=1`, a fresh token,
  and `operator_confirmed=true`. Tokens expire after 120 seconds and are single-use.
- Requirements.txt pins FastMCP. The lock file is the original full environment
  snapshot; don't assume it is a cross-platform lock.

## Motion policy and guarantees that must not be overstated

Normal operator bounds are XY 0..200 and Z 0..235 mm. Maximum commanded XY speed
is 20 mm/s; Z is 2 mm/s. Also check firmware-reported limits. XY-only plans require
XY homing; a Z step requires XYZ. An unhomed Z report is not proof of physical Z.
XY-only with Z unhomed requires inactive mesh. The terminal offers mesh unload
when mesh is active; remote ordinary planning itself does not universally reject
every active mesh if coordinates happen to agree. There is no universal skew
transform detection. Keep that limitation visible.

The special `xy-start` planner accepts the observed negative homing area only:
X -12..0, Y -15..0. It generates a straight XY entry to (0,0) at 5 mm/s, without Z.
The execution bounds are the rectangle from the actual start to zero. It requires
inactive mesh, unchanged preview start and an explicit ENTER confirmation.
Do not generalize it to arbitrary out-of-bounds recovery without operator input.

State guards require ready/idle state, zero heater targets, 100% speed override,
zero coordinate offsets, valid telemetry and stationary, consistent preflight
coordinates. During XY plans, reported Z must stay within 0.002 mm of its start.
For Z plans, reported Z must remain within the planned min/max range with that
tolerance, as well as absolute limits. Status absolute bounds allow 1e-9 arithmetic
roundoff; command targets have no such relaxation.

The monitor checks firmware estimates, not real encoders. Polling is ~100 ms,
firmware live position may refresh ~250 ms, and a normal API response deadline is
1 second. Detection/stop latency permits overshoot. Mixed-axis sequence velocity
is checked against its fastest planned step speed; Z commands themselves use the
separate Z limit. The implementation does not enforce the per-step speed limit
against a precisely identified current segment of a mixed sequence.

Once submitted, the script is queued. Ctrl-C/transport uncertainty attempts an
emergency stop, but delivery and physical stopping are not guaranteed. Never retry
uncertain motion automatically. Stop requires manual recovery, often restart and
homing. A flock prevents concurrent simplified runners; other control apps do not
honor that lock. The emergency-stop endpoint uses a separate connection and
bypasses the sequence lock.

## Firmware zero-report exception

The operator approved exactly this exception after discussion: for at most 0.5 s
from dispatch, exact live XYZ `[0,0,0]` with exact zero velocity may be missing
startup telemetry. Fixed-Z and planned-Z-range checks for that sample are deferred.
Absolute bounds, queued targets, homing, heaters, speed/offsets and timestamps
remain checked. Cap API waits by the remaining startup deadline. A nonzero live
position/velocity closes the exception permanently for that execution. If no valid
sample arrives by the deadline, request stop. Never apply it to preflight or final
verification. During this window real motion can occur (up to 10 mm at 20 mm/s).

Implementation lives in `startup_zero_report`, `check_state`, and `execute`.
Successful results expose `startup_zero_report_seen`. Detailed unexpected-Z errors
include expected Z, queued/live XYZ and velocity for later diagnosis.

## Debugging history

1. **Wrong Terminal context.** Running the Mac's `.venv/bin/python` at the printer's
   root prompt fails. Explain which machine/tab a command belongs to.
2. **SSH reachability and session lifetime.** The printer IP changed previously.
   Root login uses local password entry, then an idle `ssh -N` tab. Shared SSH
   sessions become invalid on reboot. Keepalives detect failures, not repair them.
3. **SSH exit 255 with large payload.** Embedding the full policy/watchdog in an
   SSH exec command risked an embedded-server command-size limit. The fix uses a
   short bootstrap and streams code as a JSON line over stdin, then the request.
   Tests enforce a command shorter than 512 bytes and a simulated 9,000-byte cap.
   Keep binary buffered stdin consistent so read-ahead cannot swallow request data.
4. **Error 2001 / unexpected Z.** Logs confirmed our watchdog requested emergency
   stop roughly 0.25 s after dispatch. The returned error was `Unexpected Z change`.
   Installed firmware source can report zeros when no historical trapq sample is
   available at a new queue's startup. The original incident did not record actual
   XYZ, so that cause is plausible, not conclusively proven for that incident.
   Approved startup handling was tested subsequently with recovering zero reports.
5. **Homing vs physical placement.** Firmware reported only `xy`, so unconditional
   XYZ gating blocked XY-only sequences. Plans now choose the required homed axes
   from the requested steps. Never fake homing with a coordinate-reset command.
6. **Negative homing coordinates.** XY homing can park at (-12,-15), outside the
   normal area. The explicit entry command handles only that known region.
7. **Idle numeric noise.** Observed velocity -7.105e-15 and Y=-15.000000000000002
   were harmless floating-point artifacts; telemetry permits only 1e-9 roundoff.
8. **Entry run when already inside.** At (120,120), users were told to run
   `xy-start`, which rejected the negative-only bounds. The CLI now says entry
   is unnecessary and exits without motion. Bounds errors also include the value.
9. **Mesh reactivation.** Homing/restart or other controls can reload mesh. A
   previously successful clear is not evidence of current state. Terminal runs
   offer a separate CLEAR, then re-preview and separately request MOVE.

## Hardware evidence

These tests took place on October 13, 2026 before public packaging. Do not use
historical coordinates as a current starting position.

| Test | Evidence |
| --- | --- |
| X 120→125→120 at 20 mm/s | Watchdog confirmed return; operator did not see the brief move. |
| X 120→150→120 at 5 mm/s | Mid-run live X≈127.4175, velocity=5; completed at X≈120. Operator explicitly confirmed seeing the larger movement and return. |
| Z 5→15 at 2 mm/s | Result `ok:true`, final [110,110,15], watchdog active. |
| Z 15→65 at 2 mm/s | Result `ok:true`, final [110,110,65], watchdog active. |

Startup zero reports recovered during these controller-confirmed executions.
Mesh was unloaded while saved calibration was retained. No assertion is made
that a physical emergency stop was tested at every boundary. Automated tests
exercise stop requests and responses using simulations only.

## Validation and useful next work

Run `python -m unittest discover -s tests -v` from an installed host environment.
The suite includes Python 3.8 AST checks for printer code, full-plan rejection,
Z ranges, start changes, deadline expiry, stale/missing telemetry, transient and
persistent startup zeros, mesh confirmations, XY entry, transport failure, lock
behavior and MCP gates. Socket tests use a short `/tmp` path for macOS/Linux.
No actual IP or credentials are necessary to run the suite.

Good future work, subject to operator review when policy changes:

- Capability discovery for other firmware versions instead of assuming fixed
  interpreter/socket paths. Don't call the current package universal.
- More informative saved diagnostics without credentials or private host data.
- A carefully reviewed settings model for different printers and clear areas.
- Better independent telemetry evidence before tightening or relaxing startup
  handling. Missing physical position sensing remains a fundamental limitation.
- Explicit handling of custom coordinate transforms and per-segment monitoring.

Do not solve a blocked move by bypassing bounds, deleting the watchdog, increasing
the startup window, disabling SSH host verification, or enabling real MCP motion
without the operator's approval.
