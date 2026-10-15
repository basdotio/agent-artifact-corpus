# Working on this repository

Read README.md for the user workflow and docs/AI_HANDOFF.md for architecture,
hardware evidence, past failures, and remaining limitations.

- A request to edit, document, or test this repository does not authorize physical
  movement. Default to mock tests. Before a hardware test, obtain the operator's
  approval of the axis, direction, distance, speed and clear physical path.
- Do not automatically home, heat, extrude, change firmware limits, reset
  coordinates, enable real MCP motion, or clear/load mesh as part of a code test.
  Mesh commands are explicit operator actions; keep the existing confirmations.
- Do not weaken bounds, telemetry checks, homing requirements, stop behavior,
  or the 0.5-second startup exception to make a failing test pass. Discuss any
  proposed motion-policy change with the operator first.
- Keep printer_policy.py and printer_watchdog.py compatible with Python 3.8.
  Host Python is 3.10+; tests and FastMCP use the host environment.
- Use the shared authenticated SSH master. Never request, store, log or commit a
  printer password; do not fall back to another authentication method silently.
- Preserve full-plan validation, dispatch-time start revalidation, single-use MCP
  tokens and the no-retry rule for uncertain movement outcomes.
- Do not send arbitrary G-code. The remote API validates allowed actions/fields.
- Keep simple.py edits made by the operator; importing it must not move hardware.
- Run meaningful checks for your change: `.venv/bin/python -m unittest discover
  -s tests -v`, plus `.venv/bin/python -m pip check` for dependency changes.
  All automated tests must remain independent of a physical printer.
- Record physical test results separately from simulation results and operator
  observations. Never infer physical clearance from firmware coordinates alone.
- Keep personal IP addresses, credentials, local environments and diagnostic
  logs out of commits. Do not commit a real .env file.
