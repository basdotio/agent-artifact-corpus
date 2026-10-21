# Contributing

Contributions are welcome! Here's how to get started.

## Adding a new tool

Each category lives in `tools/<category>.py` and is self-contained.

1. **Define the tool** — add a `Tool(...)` entry to the list at the top of the file:

```python
Tool(
    name="my_new_tool",
    description="One clear sentence describing what this does and when to use it.",
    inputSchema={
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "The thing to process"},
        },
        "required": ["input"],
    },
),
```

2. **Handle it** — add a branch in the `handle_*` function:

```python
if name == "my_new_tool":
    return await run_cmd("some-binary", args["input"])
```

3. No changes to `server.py` needed — it auto-discovers everything.

## Adding a new category

1. Create `tools/my_category.py` following the same pattern as existing modules
2. In `server.py`, import and register it:

```python
from tools.my_category import my_category_tools, handle_my_category

ALL_TOOLS = ... + my_category_tools

for tool in my_category_tools:
    TOOL_HANDLERS[tool.name] = handle_my_category
```

## Code style

- Python 3.11+, async throughout
- `ruff check .` must pass before submitting a PR
- Tool descriptions should tell Claude *when* to use the tool, not just what it does

## Submitting a PR

1. Fork the repo
2. Create a branch: `git checkout -b feat/my-tool`
3. Make your changes and ensure `ruff check .` passes
4. Open a pull request with a short description of what the tool does and an example prompt that triggers it
