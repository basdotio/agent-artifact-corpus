---
name: ws-protocol
description: Define/update the WebSocket protocol spec: message types, schemas, idempotency, replay protection, reconnect flow.
---

Update docs/PROTOCOL_WS.md.

Include:
- protocolVersion
- message envelope (type, ts, requestId, tableId, seatToken, payload)
- idempotency keys for action submission
- replay protection strategy (monotonic seq per client or per seat)
- error codes and retry rules
- full example flows:
  1) join -> ws connect -> start hand -> actions -> end hand
  2) disconnect -> reconnect -> state resync
