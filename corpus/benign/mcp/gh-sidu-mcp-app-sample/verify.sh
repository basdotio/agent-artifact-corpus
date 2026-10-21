#!/usr/bin/env bash
#
# verify.sh — exercise every MCP + MCP Apps capability the sample server
# advertises, and print a pass/fail table.
#
# We drive the server over stdio using hand-written JSON-RPC frames rather than
# the Inspector CLI so that this script has no dependencies beyond node + jq.
# Each check sends the initialize handshake, runs one or more requests, and
# grep/jq's the response.
#
# Usage:  ./verify.sh
# Exit:   non-zero if any [BLOCK] check fails.

set -u
cd "$(dirname "$0")"

if [ ! -f dist/main.js ]; then
  echo "dist/main.js not found — run \`npm run build\` first." >&2
  exit 1
fi

pass=0
fail=0
total=0

# color if TTY
if [ -t 1 ]; then
  GREEN=$(printf '\033[32m')
  RED=$(printf '\033[31m')
  YELLOW=$(printf '\033[33m')
  DIM=$(printf '\033[2m')
  RESET=$(printf '\033[0m')
else
  GREEN=; RED=; YELLOW=; DIM=; RESET=
fi

# run <label> <requests-multiline> — feeds initialize + <requests> to the
# server and writes the response to /tmp/verify.out.
run() {
  local label="$1" requests="$2"
  local wait_s="${VERIFY_WAIT:-1}"
  : > /tmp/verify.out
  # Feed requests via a pipeline that holds stdin open for $wait_s so
  # asynchronous notifications can accumulate before the server exits.
  # Redirect server stdout directly to /tmp/verify.out so subshell capture
  # semantics don't drop data. Force-kill after wait_s + 2s if the server
  # is stuck waiting on an outbound response (sampling/elicit/roots).
  {
    printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{"roots":{},"sampling":{},"elicitation":{}},"clientInfo":{"name":"verify","version":"0"}}}'
    printf '%s\n' '{"jsonrpc":"2.0","method":"notifications/initialized"}'
    printf '%s\n' "$requests"
    sleep "$wait_s"
  } | node dist/main.js --stdio >> /tmp/verify.out 2>/dev/null &
  local pid=$!
  ( sleep "$(awk "BEGIN{print $wait_s+2}")" 2>/dev/null; kill -KILL "$pid" 2>/dev/null ) &
  local killer=$!
  wait "$pid" 2>/dev/null
  kill "$killer" 2>/dev/null
  wait "$killer" 2>/dev/null
}

# check <label> <predicate command> — updates counters; predicate reads
# /tmp/verify.out and exits 0/non-zero.
check() {
  local label="$1"; shift
  total=$((total + 1))
  if "$@" > /dev/null 2>&1; then
    printf "  ${GREEN}✓${RESET} %s\n" "$label"
    pass=$((pass + 1))
  else
    printf "  ${RED}✗${RESET} %s\n" "$label"
    fail=$((fail + 1))
  fi
}

section() { printf "\n${YELLOW}== %s ==${RESET}\n" "$1"; }

# ---------------------------------------------------------------------------
section "Capability advertisement"
run "init" ""
check "[CAP-TOOL]        tools capability advertised" \
  grep -q '"tools":{"listChanged":true}' /tmp/verify.out
check "[CAP-RES-SUBSCRIBE] resources subscribe advertised" \
  grep -q '"resources":{"listChanged":true,"subscribe":true}' /tmp/verify.out
check "[CAP-PROMPT]      prompts capability advertised" \
  grep -q '"prompts":{"listChanged":true}' /tmp/verify.out
check "[CAP-LOG]         logging capability advertised" \
  grep -q '"logging":{}' /tmp/verify.out
check "[CAP-COMPLETE]    completions capability advertised" \
  grep -q '"completions":{}' /tmp/verify.out

# ---------------------------------------------------------------------------
section "Tools"
run "tools/list" '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
for t in echo dashboard long-task summarize-with-llm ask-user list-roots \
         read-large-file poll-metrics shader-preview open-counter \
         toggle-dynamic-tool; do
  check "[CAP-TOOL]        tool \`$t\` listed" \
    grep -q "\"name\":\"$t\"" /tmp/verify.out
done
check "[CAP-TOOL-ANNOT]  echo has readOnlyHint annotation" \
  grep -q '"readOnlyHint":true' /tmp/verify.out
check "[CAP-APP]         dashboard has _meta.ui.resourceUri" \
  grep -q '"ui/resourceUri":"ui://sample/dashboard.html"' /tmp/verify.out
check "[CAP-APP-APPONLY] poll-metrics tagged visibility=[app]" \
  grep -q -F '"visibility":["app"]' /tmp/verify.out

# ---------------------------------------------------------------------------
section "Tool calls"
run "echo" '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"echo","arguments":{"text":"hi"}}}'
check "[CAP-TOOL]        echo returns text content" \
  grep -q '"text":"hi (received' /tmp/verify.out
check "[CAP-TOOL]        echo returns structuredContent" \
  grep -q '"structuredContent":{"echoed":"hi"' /tmp/verify.out

run "dashboard" '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"dashboard","arguments":{"title":"Test"}}}'
check "[CAP-APP-STRUCT]  dashboard returns metrics array" \
  grep -q '"metrics":\[' /tmp/verify.out
check "[CAP-TOOL-RESLINK] dashboard returns resource_link" \
  grep -q '"type":"resource_link"' /tmp/verify.out
check "[CAP-APP-VIEWUUID] dashboard returns _meta.viewUUID" \
  grep -q '"viewUUID"' /tmp/verify.out

# ---------------------------------------------------------------------------
section "Progress + logging + cancellation"
VERIFY_WAIT=2 run "long-task" '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"long-task","arguments":{"steps":3,"delayMs":100},"_meta":{"progressToken":"p1"}}}'
check "[CAP-PROGRESS]    progress notification 1/3" \
  grep -q '"progress":1,"total":3' /tmp/verify.out
check "[CAP-PROGRESS]    progress notification 3/3" \
  grep -q '"progress":3,"total":3' /tmp/verify.out
check "[CAP-LOG]         log message emitted during long-task" \
  grep -q '"method":"notifications/message"' /tmp/verify.out

# ---------------------------------------------------------------------------
section "Resources"
run "resources/list" '{"jsonrpc":"2.0","id":2,"method":"resources/list"}'
check "[CAP-RES-STATIC]  config.json resource listed" \
  grep -q '"uri":"resource:///config.json"' /tmp/verify.out
check "[CAP-RES-BLOB]    logo.png resource listed" \
  grep -q '"uri":"resource:///logo.png"' /tmp/verify.out
check "[CAP-RES-SUBSCRIBE] live-counter resource listed" \
  grep -q '"uri":"resource:///live/counter"' /tmp/verify.out
check "[CAP-APP]         dashboard UI resource listed" \
  grep -q '"uri":"ui://sample/dashboard.html"' /tmp/verify.out

run "resources/templates/list" '{"jsonrpc":"2.0","id":2,"method":"resources/templates/list"}'
check "[CAP-RES-TEMPLATE] item template registered" \
  grep -q '"uriTemplate":"resource:///items/{id}"' /tmp/verify.out

run "read item 42" '{"jsonrpc":"2.0","id":2,"method":"resources/read","params":{"uri":"resource:///items/42"}}'
# Widget is inside a JSON string of a JSON string, so the quotes are escaped.
check "[CAP-RES-TEMPLATE] template resolves for id=42" \
  grep -q 'Widget' /tmp/verify.out

run "read logo" '{"jsonrpc":"2.0","id":2,"method":"resources/read","params":{"uri":"resource:///logo.png"}}'
check "[CAP-RES-BLOB]    binary blob returned as base64" \
  grep -q '"blob":"iVBORw0KGgo' /tmp/verify.out

VERIFY_WAIT=3 run "subscribe" '{"jsonrpc":"2.0","id":2,"method":"resources/subscribe","params":{"uri":"resource:///live/counter"}}'
check "[CAP-RES-SUBSCRIBE] at least one resources/updated notification" \
  grep -q '"method":"notifications/resources/updated"' /tmp/verify.out

# ---------------------------------------------------------------------------
section "Prompts + completion"
run "prompts/list" '{"jsonrpc":"2.0","id":2,"method":"prompts/list"}'
check "[CAP-PROMPT]      code-review prompt listed" \
  grep -q '"name":"code-review"' /tmp/verify.out

run "prompts/get" '{"jsonrpc":"2.0","id":2,"method":"prompts/get","params":{"name":"code-review","arguments":{"language":"go"}}}'
check "[CAP-PROMPT]      prompts/get returns messages" \
  grep -q '"role":"user"' /tmp/verify.out

run "completion" '{"jsonrpc":"2.0","id":2,"method":"completion/complete","params":{"ref":{"type":"ref/prompt","name":"code-review"},"argument":{"name":"language","value":"ty"}}}'
check "[CAP-COMPLETE]    completion returns typescript for prefix ty" \
  grep -q '"typescript"' /tmp/verify.out

# ---------------------------------------------------------------------------
section "list_changed"
run "toggle-dynamic-tool" '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"toggle-dynamic-tool","arguments":{}}}'
check "[CAP-LISTCHANGED] tools/list_changed notification emitted" \
  grep -q '"method":"notifications/tools/list_changed"' /tmp/verify.out

# ---------------------------------------------------------------------------
section "Client-side (host-dependent) — verify server sends outbound request"
# For these three capabilities the server sends a request back to the client.
# We can't fulfil the request without a real host, but we CAN verify the
# server issues the correct outbound method name — that alone proves the
# server-side plumbing exists.

run "summarize-with-llm" '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"summarize-with-llm","arguments":{"text":"foo"}}}'
check "[CAP-SAMPLING]    server issues sampling/createMessage" \
  grep -q '"method":"sampling/createMessage"' /tmp/verify.out

run "ask-user" '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"ask-user","arguments":{}}}'
check "[CAP-ELICIT]      server issues elicitation/create" \
  grep -q '"method":"elicitation/create"' /tmp/verify.out

run "list-roots" '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list-roots","arguments":{}}}'
check "[CAP-ROOTS]       server issues roots/list" \
  grep -q '"method":"roots/list"' /tmp/verify.out

# ---------------------------------------------------------------------------
section "Chunked binary (MCP Apps pattern)"
run "chunk-0" '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"read-large-file","arguments":{"offset":0,"byteCount":1024}}}'
check "[CAP-APP-CHUNK]   read-large-file returns structuredContent chunk" \
  grep -q '"totalBytes":1048576' /tmp/verify.out
check "[CAP-APP-CHUNK]   read-large-file reports hasMore=true" \
  grep -q '"hasMore":true' /tmp/verify.out

# ---------------------------------------------------------------------------
printf "\n%s pass=%d fail=%d total=%d%s\n" "$YELLOW" "$pass" "$fail" "$total" "$RESET"
if [ "$fail" -gt 0 ]; then
  echo "${RED}FAILED${RESET}"
  exit 1
fi
echo "${GREEN}All automated checks passed${RESET}"
echo
echo "${DIM}Manual host-dependent checks: see VERIFY.md${RESET}"
