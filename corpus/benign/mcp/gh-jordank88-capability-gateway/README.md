# Capability Gateway

**Progressive disclosure for MCP tools: hundreds of tools behind four.**

An MCP client puts every tool's name, description and JSON schema into the model's context on every turn. That's fine at 10 tools. At 250 it's a six-figure token bill before the model reads your first message, and a model choosing among hundreds of similar-looking tools picks the wrong one more often.

Capability Gateway exposes exactly **four** tools, however many sit behind it. The model browses short group descriptions, loads only the schemas it needs, and calls any tool by name:

```
list_capabilities()        → a few group descriptions, no schemas
search_tools("git")        → flat search when browsing doesn't land
load_capability("git")     → full schemas for one group, on demand
run_tool("git_status", {}) → call any tool by name
```

In the private toolkit this was extracted from, **249 tools cost about 114,000 tokens of tool definitions exposed directly, and about 630 through the gateway**, roughly 180× less, paid on every turn. Run `python gateway_server.py --measure` to see the numbers for your own registry.

## More than a router: guard rails on every call

`run_tool` is a single choke point, which makes it the natural place to catch the ways models misuse tools. Each of these exists because the failure happened for real:

| Guard | What it catches |
|---|---|
| **Schema validation** | Wrong types and missing required fields, rejected before the tool runs, with the failing field's schema attached so the model can fix the call. |
| **Unknown-argument rejection** | JSON Schema alone *accepts* undeclared properties, so a wrong argument is silently ignored. A ticket-sync tool called with `dry_run=true` (it has no dry-run mode) created a real ticket; a timer called with `hours=4` (it takes `minutes`) ran for its default instead. The gateway rejects the call, suggests the argument you probably meant (`did you mean 'minutes'?`) or the sibling tool that takes it, and warns loudly when the ignored argument was a safety flag. |
| **Placeholder detection** | Models sometimes pass a plausible invented value (`dummy_123`, `TBD`, `xxx`) instead of looking up the real one. Those calls are refused with a pointer to go find the real value. |
| **Wall-clock timeouts** | A hung tool returns a clean `GATEWAY_TIMEOUT` instead of hanging the session. |
| **Opt-in result cache** | Expensive, side-effect-free reads can be cached with a TTL. Caching requires *two* deliberate edits, so it never switches on by accident, and only successful results are ever stored. |
| **Audit log** | Every call is appended to a SQLite audit trail, with secret-looking arguments redacted. |
| **Error enrichment** | A growable map from `(tool, error_code)` to hints and next steps, so a lesson learned debugging one failure reaches every model that hits it afterward. |

The registry is validated at startup: every schema must be well-formed and every tool must belong to exactly one capability group. A tool the model can't find by browsing is a bug, so it fails loudly.

## Quick start

```bash
git clone https://github.com/JorDank88/capability-gateway
cd capability-gateway
pip install -r requirements.txt
python gateway_server.py --validate
python gateway_server.py run_tool '{"name": "git_status", "args": {"repo": "."}}'
```

Register it with your MCP client (Claude Code, Claude Desktop, or any MCP host). For Claude Code, copy `.mcp.json.example` to `.mcp.json` and set the absolute path:

```json
{
  "mcpServers": {
    "capability-gateway": {
      "command": "python",
      "args": ["/absolute/path/to/capability-gateway/gateway_server.py"]
    }
  }
}
```

`python gateway_server.py --doctor` checks package versions, tool imports, and whether your client config actually registers the server.

## What's in the box

```
gateway_server.py          the 4 gateway tools, guard rails, MCP server, CLI
_registry.py               every tool: module, description, input schema   ← you edit
_capabilities.py           how tools are grouped for discovery              ← you edit
_tool_error_enrichment.py  per-tool error hints, grown from real failures   ← you edit
_result_cache.py           opt-in TTL result cache (SQLite)
_utils.py                  ok()/fail(), hang-proof run_cmd, get_secret
tools/
  audit_log.py             built-in: the audit trail
  result_cache_tool.py     built-in: inspect / invalidate the cache
  git_status.py            example: working-tree status
  json_query.py            example: JMESPath over JSON
```

The two built-ins are the gateway's own plumbing. Keep them. The two examples are universal enough to be useful as-is, and they're the reference implementations to copy.

## Adding your own tools

A tool is a Python module with `run(args: dict) -> dict`, one registry entry, and one line in a capability group. See **[docs/adding-a-tool.md](docs/adding-a-tool.md)**.

```bash
python gateway_server.py --validate   # registry and groups agree
python gateway_server.py --selftest   # every tool module imports
python -m pytest tests -q             # includes a scan that every argument run() reads is declared
```

## Design notes

- **Tool modules import lazily.** A tool's module is imported the first time it's called, so a broken or slow-to-import tool can't take down the gateway or the other tools.
- **`load_capability` is a discovery aid, not an access gate.** `run_tool` works for any registered tool whether or not its group was loaded. Gating would only add a failure mode.
- **Failures are data.** Every result is `{"success": ..., ...}` with an `error_code` on failure, so the model can branch on what went wrong instead of parsing prose.
- **One process, one session.** Each MCP client session spawns its own gateway process, which scopes audit entries to a session without any client cooperation.

## License

Apache 2.0. See [LICENSE](LICENSE).
