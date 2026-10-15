# Photonics Printer MCP

Move a 3D printer from Python steps, a Terminal command, or a FastMCP client.
Sequences are queued together to avoid a pause between every short movement.
An on-printer watchdog checks firmware position reports and requests an emergency
stop when a check fails.

**Tested hardware:** Creality Ender-3 V3 KE, firmware V1.1.0.17, root SSH enabled.
The host was macOS with Python 3.14.7; the printer runs Python 3.8.2. This is a
controller for that setup, not a universal driver for any 3D printer. Another
model needs a review of its SSH access, Klipper API, coordinates and limits first.

> Real commands move machinery. Stay beside the printer, verify the entire path
> is clear, and keep other printer controls idle during a run. The watchdog uses
> firmware estimates; it cannot detect every collision or guarantee a stop before
> a physical boundary. See [safeguards and limitations](#safeguards-and-limitations).

## 1. Install and simulate first

Run these commands on your **Mac**, not inside the printer's SSH shell:

```bash
git clone https://github.com/WhoEvenAm/photonics-printer-mcp.git
cd photonics-printer-mcp
python3 --version                       # Python 3.10 or newer
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./printerctl --mock
```

The terminal runner uses the Python standard library. `requirements.txt` installs
FastMCP 4.1.0 for the MCP server and full test suite. `requirements.lock.txt` records
the dependencies from the original tested macOS environment; use it when reproducing
that environment, rather than assuming its platform-specific packages fit every OS.

`--mock` is simulation and makes no SSH connection. **Without `--mock`, terminal
commands target hardware.** The MCP server, separately, defaults to simulation.

The included `simple.py` draws a **1 × 1 mm square at 20 mm/s**. It is deliberately
small and may be hard to see. Examples below show how to choose larger steps.

## 2. Connect to your printer

The printer must be reachable from the Mac on the local network and have root
SSH access enabled through its own settings. Find its current IP on its screen.
No printer address or password is bundled with the code.

Create a local configuration:

```bash
cp .env.example .env
open -e .env
```

Replace the example address with **your printer's IP**. The file contains shell
`export` statements. It is ignored by Git and is **not loaded automatically**.
Do not put passwords in it.

In **Terminal tab 1**:

```bash
cd /path/to/photonics-printer-mcp
source .env
./printerctl connect
```

Verify the SSH host fingerprint when first connecting. Enter the root password
locally; password characters are hidden. After login the tab stays open and idle.
This is expected: the command opens a shared SSH session with `ssh -N`. Leave it
open. If it exits or the printer restarts, reconnect.

In **Terminal tab 2**:

```bash
cd /path/to/photonics-printer-mcp
source .env
./printerctl status
```

Both tabs must use the same `SSH_HOST` and `SSH_CONTROL_PATH`. Alternatively,
export those variables directly in both tabs. The default control socket is
`/tmp/photonics-printer-control`; give each printer a distinct socket if using
more than one. Physical movement still requires a preview and confirmation.

## 3. Make your first movement

Home the required axes using the printer controls. X/Y-only steps require X and
Y homed; any Z step requires all three axes homed. Moving an axis by hand does
not establish firmware homing. The runner does not perform homing.

For a short X test:

```bash
./printerctl test-move
```

This previews **X +5 mm and back**, normally at 20 mm/s. If mesh compensation is
active, it first offers to unload it: type `CLEAR` only after reviewing that action.
Saved calibration is retained. It then prints the checked movement plan; type
`MOVE` to execute. Any other response cancels that action. A slower visible test:

```bash
./printerctl test-move --speed 5
```

The full requested path must fit the bounds, including the starting position.
For example, the +5 mm test requires starting X at or below 195 mm.

For your steps in `simple.py`:

```bash
./printerctl --mock       # simulate
./printerctl --preview    # read hardware state and validate; never moves or clears mesh
./printerctl              # prepare, show the plan, then ask for MOVE
```

If a preview reports active mesh, use `./printerctl mesh-clear`, type `CLEAR`,
and preview again. Normal execution can offer that same separate confirmation.
After movement testing, restore the saved mesh before printing:

```bash
./printerctl mesh-load default
```

Type `LOAD`. Use your actual profile name if it differs from `default`.

## 4. Write your own steps

Open `simple.py` in an editor:

```bash
open -e simple.py
```

`fw(axis, distance)` increases an axis coordinate. `bc(axis, distance)` decreases
it. Distances are positive **millimetres**; 50 mm is 5 cm. These functions build
step dictionaries, and `run(...)` executes them in order. Merely importing the
file or writing a standalone `fw(...)` expression does not move the printer.
On the Ender-3 V3 KE, Y movement moves the bed; increasing Z raises the gantry.

### A 50 × 50 mm square

```python
from simple_runner import fw, bc, x, y, z, run

SPEED = 20.0        # X/Y mm/s; maximum 20
Z_SPEED = 2.0      # Z mm/s; maximum 2
STEPS = [
    fw(x, 50),
    fw(y, 50),
    bc(x, 50),
    bc(y, 50),
]

if __name__ == '__main__':
    raise SystemExit(run(STEPS, SPEED, z_speed=Z_SPEED))
```

This direction of square needs starting X and Y within 0..150 mm. It returns to
its start. At 20 mm/s each 50 mm side takes about 2.5 seconds plus acceleration
and cornering time. This traces motion only: it does not extrude or print a line.

### Raise Z by 10 mm

Replace only the `STEPS` list with:

```python
STEPS = [fw(z, 10)]
```

This adds 10 mm to the current Z; it does **not** set Z to 10. At 2 mm/s it takes
about 5 seconds plus acceleration. For a raise and return:

```python
STEPS = [fw(z, 10), bc(z, 10)]
```

Check the lowering path as well as the raising path. Z must stay within 0..235 mm.
For a 50 mm raise, use `fw(z, 50)` and start at Z no greater than 185 mm.

### Separate movement files

You can keep the square and add another file, for example `raise_z.py`:

```python
from simple_runner import fw, z, run

if __name__ == '__main__':
    raise SystemExit(run([fw(z, 10)], z_speed=2))
```

Run it on the Mac with the same connection variables:

```bash
.venv/bin/python raise_z.py --mock
.venv/bin/python raise_z.py --preview
.venv/bin/python raise_z.py
```

`printerctl` always runs `simple.py`; call your separate file with Python.

## Terminal command reference

| Command | Effect |
| --- | --- |
| `./printerctl connect` | Open the shared SSH session; leave this tab open. |
| `./printerctl status` | Read printer state, homed axes, mesh, temperatures and positions. |
| `./printerctl --mock` | Simulate the steps in `simple.py`; no hardware access. |
| `./printerctl --preview` | Read and validate the full sequence without changing printer state. |
| `./printerctl` | Prepare and execute `simple.py` after confirmations. |
| `./printerctl test-move` | Preview and confirm X +5 mm and return. |
| `./printerctl --speed 5` | Run `simple.py` with X/Y limited to 5 mm/s. |
| `./printerctl --z-speed 1` | Run `simple.py` with Z at 1 mm/s; X/Y speed is unchanged. |
| `./printerctl mesh-clear` | Type `CLEAR` to unload compensation; saved calibration remains. |
| `./printerctl mesh-load default` | Type `LOAD` to load the named saved mesh. |
| `./printerctl xy-start-preview` | Preview the special entry from the known negative homing area. |
| `./printerctl xy-start` | Type `ENTER` to approve that entry move; see below. |
| `./printerctl stop` | Request emergency shutdown; manual recovery is required. |

Speed options combine with `--mock` or `--preview`. Action options such as
`--preview`, `--status`, and `--test-move` are mutually exclusive.

### When `xy-start` is useful

This tested printer has reported X=-12, Y=-15 after X/Y homing. Regular sequences
reject a negative starting coordinate. `xy-start` is a separate, confirmed straight
move to X=0, Y=0 at 5 mm/s, with no Z command. It accepts only starting X in -12..0
and Y in -15..0. During entry, the watchdog checks the displayed rectangle from
that start to zero. This is a specific tested setup, not a generic homing routine.

If already inside X/Y 0..200, it explains that entry is unnecessary and sends no
move. It does not certify readiness for the next sequence. With Z unhomed or
reported as zero, physical nozzle clearance must be checked by the operator.
It never resets coordinates and never homes an axis.

## Troubleshooting

| Message or symptom | What to check |
| --- | --- |
| `Set SSH_HOST...` | Run `source .env` in this tab, with your printer's current IP. |
| `No route to host` / connection timeout | Printer power, its displayed IP, and local network reachability. |
| `Shared SSH session unavailable` / SSH 255 | Reopen `./printerctl connect` in tab 1; check its error output. |
| `./printerctl: no such file` | Change into the cloned folder first. |
| `.venv/bin/python: not found` at a `root@...` prompt | You are inside the printer shell. Use a Mac Terminal tab and the cloned folder. |
| No password characters or success message | SSH hides password entry; an idle connected tab is normal with `-N`. |
| `Home ... axes` | Use printer homing controls; hand-positioning is insufficient. |
| `outside operator bounds` | Read the reported coordinate and check the whole planned path. Use `xy-start` only for its documented negative starting area. |
| Toolhead/G-code positions disagree | Check mesh state. Unload it explicitly for testing, then re-preview; do not relabel coordinates with G92. |
| `Unexpected Z change`, stop requested, or screen error 2001 | Inspect the printer and preserve the terminal error. Do not automatically retry. An emergency stop can require manual restart and homing. |
| `Another simplified runner is already active` | Let the other run finish; do not bypass the lock. Emergency stop uses a separate path. |

The original error 2001 incident followed our watchdog's emergency-stop request
for `Unexpected Z change`. It is not evidence that every error 2001 has that cause.

## Safeguards and limitations

The current operator-approved limits are **X/Y 0..200 mm**, **Z 0..235 mm**,
**X/Y speed ≤20 mm/s**, and **Z speed ≤2 mm/s**. Those are specific operating limits,
not a claim about every printer's physical clearance. They live in `printer_policy.py`.
Review changes with the person operating the machine; do not increase them simply
to bypass a rejection. Firmware limits are also checked and are never rewritten.

The runner validates the complete path, including rounded command coordinates,
before dispatch. It rechecks the starting position immediately before sending one
queued script (`G90`, movement commands, `M400`). The watchdog runs beside Klipper
on the printer and checks live and queued position, homing, idle state, heater
targets, speed override, offsets, timestamps, velocity and final completion.
It requests an emergency stop on execution faults, stale/missing telemetry or a
deadline failure. It does not automatically retry uncertain motion.

Important limits of that protection:

- It observes firmware estimates, not independent physical sensors. Skipped steps,
  collisions and controller failure may not be detected correctly.
- Polling is approximately 100 ms; firmware position refresh may be about 250 ms.
  A normal missing-response timeout is 1 second. A boundary can be crossed before
  detection and shutdown. Keep physical clearance beyond the planned path.
- A documented firmware quirk may report exact live XYZ `[0,0,0]` and velocity
  zero briefly after dispatch. The approved exception allows at most **0.5 seconds**
  for valid live telemetry to arrive. Fixed/planned Z checks for that missing sample
  are deferred; other checks continue. The window closes on the first nonzero
  position/velocity report and cannot reopen. Preflight/final checks stay strict.
  Movement is possible during that uncertain interval: up to 10 mm at 20 mm/s,
  plus physical stopping latency. The watchdog stops if the window expires.
- Status bounds allow only 1e-9 arithmetic roundoff; command targets remain strict.
  The separate fixed/planned Z comparison tolerance is 0.002 mm.
- Ctrl-C attempts a stop if execution is in progress, but queued moves can continue
  if communication fails. Keep access to the physical power cutoff. `stop` is an
  emergency shutdown, not a pause/resume feature.
- The runner's lock excludes other copies of this runner, not touchscreen commands
  or unrelated applications. Leave those idle during execution.
- Heating, extrusion, arbitrary G-code, coordinate resets and automatic homing are
  not exposed. There is no global skew-compensation detection; don't treat these
  checks as validation of every possible custom firmware transform.

## FastMCP / AI clients

Start the stdio server in simulation:

```bash
.venv/bin/python fastmcp_server.py
```

| Tool | Behavior |
| --- | --- |
| `printer_status()` | Read state. |
| `preview_sequence(steps, speed_mm_s=20, z_speed_mm_s=2)` | Validate a sequence and return a token valid for 120 seconds. |
| `execute_sequence(token, operator_confirmed=False)` | Execute the reviewed sequence once after operator confirmation. |
| `emergency_stop()` | Request shutdown independently of the sequence lock. |

Example step dictionaries:

```json
[{"axis": "z", "distance_mm": 10}, {"axis": "z", "distance_mm": -10}]
```

To configure an MCP client, use the absolute path to `.venv/bin/python` as its
command and the absolute path to `fastmcp_server.py` as its argument. Set environment
variables explicitly in that client; it does not inherit another Terminal tab's
exports automatically. `PRINTER_MODE=mock` is the default. Real status/preview access
requires `PRINTER_MODE=real`, `SSH_HOST`, and the shared SSH session. Real execution
also requires the operator to set `PRINTER_ALLOW_MOTION=1`; that flag alone does not
replace approval of each reviewed path. Pass `operator_confirmed=true` only after
that approval. Mesh management and `xy-start` remain terminal-only operations.

The requested “FastMCP dictionaries” are Python dictionary steps and dictionary
tool results through the FastMCP library. No separate FastMLP component is used.

## Development and test evidence

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip check
```

Tests use mock printers, local Unix sockets, stubbed SSH transport, and in-process
and stdio FastMCP clients. They do not contact a physical printer. The included
GitHub Actions workflow runs this suite on Linux and macOS.

On October 13, 2026, the original controller reported successful hardware tests:

| Test | Result and evidence |
| --- | --- |
| X +5 mm and return at 20 mm/s | Firmware confirmed completion; operator did not see the brief motion. |
| X 120 → 150 → 120 mm at 5 mm/s | Firmware confirmed completion; a mid-run report showed motion, and the operator confirmed seeing it. |
| Z 5 → 15 mm at 2 mm/s | Watchdog confirmed final Z=15; X/Y stayed at 110. |
| Z 15 → 65 mm at 2 mm/s | Watchdog confirmed final Z=65; X/Y stayed at 110. |

These are historical test coordinates, not the current position or a startup
assumption. The sharing copy changes host configuration and test portability;
its movement policy is retained. For the detailed architecture and AI continuation
notes, read [docs/AI_HANDOFF.md](docs/AI_HANDOFF.md) and [AGENTS.md](AGENTS.md).

## License

[MIT](LICENSE). No passwords, private SSH keys, personal printer IP, local virtual
environment or diagnostic logs are included.
