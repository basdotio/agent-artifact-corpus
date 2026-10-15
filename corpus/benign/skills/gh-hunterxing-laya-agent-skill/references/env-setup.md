# Laya-compatible backend configuration

The helper is provider-agnostic. It can be used by any host agent that can execute the CLI, start the MCP server, or call the configured HTTP endpoint. Keep credentials in a secret store with restrictive permissions; never print them or commit them.

## Credential file search order

The helper uses the first existing file, then lets `LAYA_*` environment variables override file values:

| Order | Location | Use |
|---|---|---|
| 1 | `--env-file <path>` | explicit/test configuration |
| 2 | `$LAYA_ENV_FILE` | host-specific configuration |
| 3 | `$LAYA_HOME/laya.env` | standalone Laya home |
| 4 | `~/.config/laya/laya.env` | XDG-style default |
| 5 | `~/.laya.env` | temporary user override |
| 6 | `${HERMES_HOME}/secrets/laya.env` | Hermes-compatible installation |
| 7 | `~/.hermes/secrets/laya.env` | compatibility fallback |

If no file is present, exported environment variables are enough. If `LAYA_BASE_URL` is missing, the helper returns `configuration_error` without making a request.

## Configuration

```text
LAYA_BASE_URL=<OpenAI-compatible gateway root, commonly ending in /v1>
LAYA_API_KEY=<bearer token limited to Laya decision models, if required>
LAYA_MODEL=laya-latest
LAYA_TIMEOUT_SECONDS=30
LAYA_CHAT_PATH=/chat/completions
LAYA_DECISION_PATH=/decisions
LAYA_NATIVE_DECISIONS=false
LAYA_ENV_FILE=<optional explicit env file>
LAYA_HOME=<optional standalone config directory>
LAYA_PYTHON=<optional interpreter for the shell wrapper>
LAYA_MCP_DEBUG=<optional value enables MCP diagnostics on stderr>
```

Model names and preset names are deployment-specific. Query `/models` before relying on a name. A backend may expose `laya-latest`, `laya-preset-triage`, `laya-preset-guardrails`, or other names; the helper does not assume that any particular name exists.

If the backend exposes native `state + questions` at `/decisions`, set `LAYA_NATIVE_DECISIONS=true`. If it exposes the OpenAI-compatible wrapper, keep it `false`. The helper supports both transport shapes but always validates the same `laya.decision.v1` decision contract.

## Entrypoints

```bash
SKILL_ROOT="<absolute-skill-path>"

sh "$SKILL_ROOT/scripts/laya.sh" selftest
python3 "$SKILL_ROOT/scripts/laya.py" models
python3 "$SKILL_ROOT/scripts/laya_mcp.py"
```

Register the MCP server using the host agent's documented MCP configuration. The server and CLI share configuration loading, so credentials need to exist in only one secret location.

## Safe probes

```bash
SKILL_ROOT="<absolute-skill-path>"
sh "$SKILL_ROOT/scripts/laya.sh" models
sh "$SKILL_ROOT/scripts/laya.sh" selftest

printf '%s' '{"request":"Locate the import error","candidates":[{"id":"debug","description":"Read the stack trace and fix the source"},{"id":"docs","description":"Write documentation"}]}' \
  | sh "$SKILL_ROOT/scripts/laya.sh" select
```

For a direct HTTP probe, use a placeholder token only when testing rejection. Do not put a real token in shell history, documentation or logs:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' --max-time 20 \
  -X POST "$LAYA_BASE_URL$LAYA_CHAT_PATH" \
  -H 'Authorization: Bearer ***' \
  -H 'Content-Type: application/json' \
  -d '{"model":"MODEL_FROM_CONFIGURATION","messages":[{"role":"user","content":"x"}]}'
```

## Runtime rules

- The gateway or local service is the authentication boundary; tokens belong only in the host secret store.
- HTTP errors, timeouts, protocol mismatches, unknown models and truncated input produce `status: unknown` and exit code 2. Never interpret them as a negative answer or approval.
- The client applies character guards before sending: option labels ≤64, option descriptions ≤240, instructions ≤600, state ≤24000 and full payload ≤32000 characters. A runtime that holds the actual tokenizer should additionally enforce the model's token budget.
- Local CPU, remote gateways and Apple Silicon MLX have different cold-start and hot-request latency. `LAYA_TIMEOUT_SECONDS` is deployment-specific, not a performance guarantee.
- For `noul`, use the proposition probability. For `choice` and `score`, confidence is normalized entropy, not top probability; thresholds must be calibrated on labeled data from the actual language and workflow.
- `action.act_probability` is advisory metadata only. Do not use it as an authorization signal without deployment-specific validation.
- A legacy `LAYA_CASCADE_THRESHOLD` may exist in an older host configuration; this helper does not use it to authorize actions. No threshold authorizes deletion, secret access, production changes or security-policy changes.
- If a token was exposed, revoke it at the gateway and issue a replacement before updating the secret store.
