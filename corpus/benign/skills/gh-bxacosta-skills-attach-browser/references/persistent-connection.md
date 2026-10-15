# Persistent connection

Each new connection in attach mode costs the user one Allow click. Keep one connection
alive and route all work through it. Not needed in dedicated mode (no dialog).

Contents: choosing a shape · in-process · broker process · reconnection · checklist.

## Choosing a shape

| Program shape | Pattern |
|---|---|
| Script that does one task and exits | Connect once, work, disconnect. One click per run is acceptable. |
| Long-running process (server, bot, agent runtime, desktop app) | In-process singleton connection |
| Many short invocations (CLI called repeatedly, several agents/tools) | Broker process that owns the connection; clients use IPC |

## In-process singleton

- One module owns the connection; everything else asks it for the client.
- Connect lazily on first use, not at startup (the user may not be ready for a dialog).
- Single-flight: store the pending connect promise/future and return it to concurrent callers.
  Two callers must never open two sockets.
- No handshake timeout. Surface "waiting for Allow" in the UI/log instead.
- On close: mark the client dead, reject pending calls, keep it dead until the next request
  triggers a reconnect (see Reconnection).

```
getClient():
  if client and client.isOpen: return client
  if pending: return await pending
  pending = connect(discoverEndpoint())   # re-read DevToolsActivePort every time
  try: client = await pending; return client
  finally: pending = null
```

## Broker process

A detached process holds the only connection; short-lived clients send it commands.

Lifecycle
- Keyed by browser (user data dir). One broker per browser.
- Started by the first client that needs it; detached from the client's terminal
  (POSIX: new session; Windows: `CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`).
- Stays up until an explicit `shutdown`, the browser/toggle goes away, or an optional idle
  timeout. Every broker restart costs a click; prefer long or no idle timeouts.

Single-flight spawn
- Take an exclusive lock file before spawning (`O_EXCL` create, `flock`, `msvcrt.locking`).
- Write a state file the broker updates: `starting → waiting-approval → connected | denied | lost`.
- A client that finds `waiting-approval` waits on it; it must not spawn a second broker.
- Pid file with process start time; verify identity before signalling (pids are reused).

IPC
- POSIX: Unix socket, mode 0600, in a 0700 directory.
- Windows: loopback TCP on a random port plus a random token, both in a user-only file; or a
  named pipe. Reject requests without the token. Never bind to `0.0.0.0`.
- Protocol: JSON lines. Request `{id, method, params, sessionId?}` → `{id, result}` or
  `{id, error}`. Add meta requests: `status`, `shutdown`, event subscription or
  `drainEvents` (buffer recent events, capped).
- Stale socket/port file: if connecting fails, delete it and follow the spawn path.

Health
- Health = a real CDP round-trip through the broker (`Browser.getVersion`), not an IPC
  ping. A broker can answer IPC while its browser connection is dead.
- Send WebSocket pings (~30 s) or rely on the library's keepalive; stretch timeouts where a
  library drops connections on short stalls.

## Reconnection

Classify the close before acting:

| Signal | Cause | Action |
|---|---|---|
| Close before open, HTTP 403 | User denied | Report; do not reconnect automatically |
| Close 1006, port closed, `user-enabled: false` | Toggle turned off | Report; wait for the user |
| Close 1006, port closed, toggle true | Browser closed | Report; reconnect when the user restarts it |
| Close with port still open | Network/client issue | Reconnect on next request |

- Reconnect only on demand (next request), never on a timer; each attempt is a new dialog.
- Re-run discovery first: the UUID changes on restart and toggle-on; the port may too.
- Session IDs die with the connection. Persist `targetId`, re-attach after reconnect.
- Tell the user a new dialog is coming.

## Checklist

```
- [ ] Exactly one connect in flight per browser (single-flight)
- [ ] No handshake timeout; "waiting for Allow" is visible to the user
- [ ] Endpoint re-discovered before every (re)connect
- [ ] Close causes classified; no automatic reconnect loops
- [ ] targetId persisted, sessionId treated as disposable
- [ ] IPC restricted to the current user (0600 socket or token)
- [ ] Health checks use a CDP round-trip
```
