# Adding a tool

A tool is three edits: a module, a registry entry, and a capability-group listing. The gateway enforces that all three agree at startup, so an incomplete addition fails loudly instead of quietly never being found.

## 1. Write the module: `tools/my_tool.py`

```python
"""
my_tool — one line on what it does.

Usage:
    python tools/my_tool.py '{"city": "Denver"}'
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, for _utils
from _utils import read_args, emit, ok, fail


def run(args: dict) -> dict:
    city = (args.get("city") or "").strip()
    if not city:
        return fail("'city' is required", "MissingArg")
    # ... do the work ...
    return ok(city=city, temperature_f=72)


if __name__ == "__main__":
    emit(run(read_args()))
```

The contract:

- **`run(args: dict) -> dict`** is the only thing the gateway calls. Return `ok(...)` or `fail(message, error_code)`. Don't raise for expected failures. The gateway turns an uncaught exception into `TOOL_CRASHED`, which tells the model nothing useful.
- **Give failures an `error_code`.** It's what lets the model (and `_tool_error_enrichment.py`) tell "bad input" from "auth expired" from "upstream down".
- **Every module runs on its own** via `read_args()`, which is the fastest way to debug it outside any MCP client.
- **Shell out with `_utils.run_cmd`**, not `subprocess` directly. It can't hang the gateway (see its docstring for the three ways plain `subprocess` does).
- **Read secrets with `_utils.get_secret("NAME")`**, which checks the OS keyring before environment variables.

## 2. Register it: `_registry.py`

```python
"my_tool": {
    "module": "tools.my_tool",
    "description": (
        "Current weather for a city. Read-only. "
        "Use for 'what's it like outside in X' style questions."
    ),
    "input_schema": {
        "type": "object",
        "required": ["city"],
        "properties": {
            "city": {"type": "string", "description": "City name, e.g. 'Denver'"},
        },
    },
},
```

- **The description is the tool's entire interface to the model.** Say what it does, when to use it, its modes, and **anything it writes or sends**. A model can't avoid a side effect it was never told about.
- **Declare every argument `run()` reads.** The gateway rejects undeclared arguments rather than silently ignoring them. That is a feature: `dry_run=true` sent to a tool without a dry-run mode would otherwise run it for real. `tests/test_registry.py` scans your module and fails if `run()` reads a key the schema doesn't declare.

## 3. Group it: `_capabilities.py`

Add the name to exactly one group, or create a group:

```python
"weather": {
    "description": "Weather and forecast lookups for any location.",
    "tools": ["my_tool"],
},
```

The group description is all the model sees before choosing a group, so write it as "would the tool I need be in here?"

## 4. Check it

```bash
python gateway_server.py --validate     # schemas valid; registry and groups in sync
python gateway_server.py --selftest     # every tool module imports
python gateway_server.py run_tool '{"name": "my_tool", "args": {"city": "Denver"}}'
python -m pytest tests -q
```

## Optional: result caching

For an expensive, side-effect-free read, add `"cache_ttl_s": 3600` to its registry entry **and** list it in `_capabilities.CACHEABLE_TOOLS`. Validation fails if only one of the two is present. That's deliberate: caching should never switch on by accident. Never cache anything that sends, creates, updates or deletes.

## Optional: error guidance

When a failure confuses you, it will confuse the model too. Add an entry to `_tool_error_enrichment.py` keyed on the tool and its `error_code`, with a `hint` or `next_step`. It's merged into every future failure with that code.
