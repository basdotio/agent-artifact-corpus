#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-https://spond.mcp.fn.flaatten.org}"
AUTH_TOKEN="${MCP_AUTH_TOKEN:-}"
SSE_OUTPUT=$(mktemp)
trap 'kill $SSE_PID 2>/dev/null; rm -f "$SSE_OUTPUT"' EXIT

AUTH_HEADER=()
if [[ -n "$AUTH_TOKEN" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer $AUTH_TOKEN")
fi

echo "=== spond MCP Service Test ==="
echo "URL: $BASE_URL"
[[ -n "$AUTH_TOKEN" ]] && echo "Auth: enabled" || echo "Auth: disabled"
echo ""

# Health check
echo -n "Health check... "
HEALTH=$(curl -sf "$BASE_URL/health")
[[ "$HEALTH" == "ok" ]] && echo "OK" || { echo "FAILED: $HEALTH"; exit 1; }

# Connect SSE in background
curl -sN "${AUTH_HEADER[@]}" "$BASE_URL/sse" > "$SSE_OUTPUT" 2>&1 &
SSE_PID=$!
sleep 2

# Extract message endpoint URL from SSE event
# Python MCP SDK sends: data: /messages/?session_id=UUID
MESSAGE_PATH=$(grep '^data:' "$SSE_OUTPUT" | head -1 | sed 's/^data: //' | tr -d '[:space:]')
if [[ -z "$MESSAGE_PATH" ]]; then
  echo "Failed to get message endpoint from SSE"
  cat "$SSE_OUTPUT"
  exit 1
fi

# Build full message URL (handle both relative and absolute paths)
if [[ "$MESSAGE_PATH" == /* ]]; then
  MESSAGE_URL="${BASE_URL}${MESSAGE_PATH}"
else
  MESSAGE_URL="$MESSAGE_PATH"
fi

echo "Message endpoint: $MESSAGE_URL"
echo ""

LINES_SEEN=0

post() {
  curl -sf -X POST "$MESSAGE_URL" \
    "${AUTH_HEADER[@]}" \
    -H "Content-Type: application/json" -d "$1" || true
}

read_response() {
  sleep 3
  local all_data
  all_data=$(grep '^data: ' "$SSE_OUTPUT" | tail -n +$((LINES_SEEN + 1)))
  LINES_SEEN=$(grep -c '^data: ' "$SSE_OUTPUT" || true)
  local last
  last=$(echo "$all_data" | tail -1 | sed 's/^data: //')
  echo "$last" | python3 -m json.tool 2>/dev/null || echo "$last"
}

# Initialize
echo "--- Initialize ---"
post '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
read_response

# List tools
echo ""
echo "--- Tools ---"
post '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
read_response

# List groups
echo ""
echo "--- List Groups ---"
post '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"list_groups","arguments":{}}}'
read_response

# Get upcoming events (7 days)
echo ""
echo "--- Upcoming Events (7 days) ---"
post '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_upcoming_events","arguments":{"days":7}}}'
read_response

# Get upcoming events for Emma (Norwegian character test)
echo ""
echo "--- Upcoming Events: Emma ---"
post '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"get_upcoming_events","arguments":{"kid_name":"Emma"}}}'
read_response

# Search for "trening"
echo ""
echo "--- Search: trening ---"
post '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"search_events","arguments":{"query":"trening"}}}'
read_response

# Get attendance
echo ""
echo "--- Attendance: Oliver ---"
post '{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"get_attendance","arguments":{"kid_name":"Oliver"}}}'
read_response

echo ""
echo "=== Done ==="
echo ""
echo "To test RSVP (changes real data!):"
echo "  Accept:  curl -sf -X POST \"\$MSG_URL\" -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"id\":10,\"method\":\"tools/call\",\"params\":{\"name\":\"respond_to_event\",\"arguments\":{\"event_id\":\"EVT_ID\",\"kid_name\":\"Oliver\",\"accept\":true}}}'"
echo "  Decline: curl -sf -X POST \"\$MSG_URL\" -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"id\":11,\"method\":\"tools/call\",\"params\":{\"name\":\"respond_to_event\",\"arguments\":{\"event_id\":\"EVT_ID\",\"kid_name\":\"Oliver\",\"accept\":false,\"decline_message\":\"Syk\"}}}'"
