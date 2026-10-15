# fastmcp-mcp

A learning project for building a production-ready MCP server with FastMCP, starting with general Python knowledge and no prior FastMCP experience.

The goal is to understand and implement the protocol's core capabilities, secure authentication and authorization, reliable application behavior, testing, deployment, and ongoing operations. The current code is a learning example, not a production-ready service.

## Learning Approach

Each lesson follows this cycle:

1. Explain the concepts and give a small coding exercise.
2. The learner writes the Python code.
3. Review the implementation and verify its behavior.
4. Update this README with the concepts, results, and any troubleshooting notes.

The learner writes the Python; the assistant teaches and reviews it. Exercises stay small and build on the existing server. Keep this learning log focused on FastMCP and MCP rather than agent-framework integrations.

## Learning Checkpoint

Last updated: 2026-10-11. Paused after Lesson 5; resume with Lesson 6.

| Lesson | Topic | Progress |
| --- | --- | --- |
| 1 | Create a server and register a tool | Completed; verified in memory |
| 2 | Connect a client and discover tools | Completed; verified in memory |
| 3 | Call a tool and inspect its response | Completed; verified in memory |
| 4 | Input schemas and validation | Completed; valid and invalid calls verified |
| 5 | Handle tool errors and recover | Completed; rejected call followed by successful call in one connection |
| 6 | Connect over stdio to a separate process | Introduced; not implemented or verified yet |

### Current Implementation

- [server.py](server.py) registers `greet(name: str) -> str` and `add_numbers(left: int, right: int) -> int`.
- [client.py](client.py) imports the server object and connects through `Client(mcp)`, using the same Python process.
- The client discovers tools, calls `greet`, catches `ToolError` for invalid addition input, and then successfully adds `1 + 25`, returning `26`.
- The server's main guard supports starting it with `mcp.run()`, but separate-process stdio communication has not yet been tested.
- HTTP transport, authentication, authorization, deployment, and operational hardening are future work.
- A small follow-up is to add a descriptive docstring to `add_numbers`; its discovered description is currently empty.

### How to Resume

From the repository root, run the existing client to refresh the verified behavior:

```bash
arch -arm64 .venv/bin/python client.py
```

Expect a handled validation message for `left="a"`, followed by `26`. Tool definitions and a server-side warning are also printed. No separately running server is needed for this in-memory checkpoint.

To continue the learning conversation: "Resume from Lesson 6: stdio. I write the code; review it and update the README after the lesson."

## Environment

Versions reported for this learning project:

- FastMCP: 4.1.0
- MCP: 2.3.0
- Python: 3.14.0
- Platform: macOS 15.8.1, Apple Silicon (arm64)

Initial setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install fastmcp
fastmcp version
```

## Lesson 1: Your First Server

Status: implementation reviewed; tool discovery and invocation verified in memory.

### Concepts

- **MCP (Model Context Protocol)** standardizes how AI applications discover and use capabilities exposed by other programs.
- A **host** is the AI application. Its **client** communicates with an MCP **server**, which exposes capabilities.
- FastMCP handles protocol details so ordinary Python functions can become MCP tools. The server does not need an LLM or an API key.
- `from fastmcp import FastMCP` imports the standalone framework.
- `FastMCP()` creates the server object; a descriptive server name can optionally be supplied.
- `@mcp.tool` registers a function as a tool. Type hints describe its inputs and output, and its docstring describes its purpose.
- `mcp.run()` defaults to stdio transport: protocol messages use standard input and output rather than an HTTP port.
- The `if __name__ == "__main__":` guard starts the server only when the file is executed directly, not when it is imported.

### Implementation and Verification

[server.py](server.py) exposes `greet(name: str) -> str`. Calling it with `{"name": "Harshit"}` returns `Hello Harshit`.

An in-memory FastMCP client successfully discovered the tool and invoked it through MCP. This verifies registration and tool behavior, but does not test a separate server process over stdio.

To start the server from the activated environment:

```bash
python server.py
```

The server waits for a client to send requests; starting it alone does not call `greet`. Stop it with `Ctrl+C`. Avoid `print()` in stdio servers because stdout carries protocol messages; use logging to stderr instead.

### Troubleshooting

The verification terminal initially launched Python as Intel (`x86_64`), while the installed `pydantic_core` extension was Apple Silicon (`arm64`). This caused an import error before the server code ran. Running Python natively resolved it without changing the code or reinstalling dependencies:

```bash
arch -arm64 .venv/bin/python server.py
```

Use this workaround only if the same architecture mismatch occurs.

## Lesson 2: Connecting and Discovering Tools

Status: connection and tool discovery covered in [client.py](client.py). The client now lists tools before invoking them.

- `Client(mcp)` configures a client for the imported FastMCP server object. This uses an in-memory connection, so no separate server process needs to be started.
- `asyncio.run(main())` runs the asynchronous entry point.
- `await client.list_tools()` requests the available tool definitions, including their names, descriptions, and input schemas. It does not execute those tools.
- Printing `client` displays the client object, not the server's tools or a tool result.
- Applications such as Cursor provide their own MCP clients. A standalone client is useful for learning and testing; it is not required when the host application already supplies one.

### Side Note: Understanding `async with`

```python
async with Client(mcp) as client:
	tools = await client.list_tools()
```

Read this as: "Open a connection to this MCP server, call the connected client `client`, and close the connection when the block finishes."

1. `Client(mcp)` creates and configures the client; constructing it alone does not open the connection.
2. `async with` enters an asynchronous context manager. FastMCP opens and initializes the connection on entry and closes it on exit, including when an exception occurs inside the block.
3. `as client` binds the value returned by entering the context to a variable named `client`. The name is your choice.
4. The indented block defines the connection's scope. Make requests while inside it.

A regular `with`, such as `with open("README.md") as file:`, manages synchronous setup and cleanup. `async with` allows setup and cleanup to await asynchronous operations; Python handles those awaits automatically.

In this client, `async with` belongs inside `async def main()`. The `await` on `client.list_tools()` waits for that request's result. Asynchronous execution does not automatically mean a new thread or process is created.

## Lesson 3: Calling a Tool

Status: `greet` invocation and response inspection covered in [client.py](client.py). The current exercise also calls `add_numbers`.

```python
result = await client.call_tool("greet", {"name": "Hridayesh"})
```

- `list_tools()` discovers tool definitions; `call_tool()` executes a named tool through MCP.
- The first argument is the tool name. The argument dictionary maps parameter names to their values.
- `await` waits for the tool call to return its result.
- The returned object contains response content, not just the Python function's returned string.
- For this greeting, `result.content[0]` is a text content block. Printing it shows the block's fields; `result.content[0].text` extracts `Hello Hridayesh`.
- Other tools can return different content types or multiple blocks, so the first-block text shortcut is specific to this example.

To print only the greeting:

```python
print(result.content[0].text)
```

Run the in-memory client without starting a separate server process:

```bash
arch -arm64 .venv/bin/python client.py
```

## Lesson 4: Input Schemas and Validation

Status: `add_numbers(left: int, right: int) -> int` implemented in [server.py](server.py). The learner observed a successful call with valid input and a validation error with invalid input.

- FastMCP uses parameter annotations to generate the tool's input schema. Both `left` and `right` are required integer inputs because neither has a default value.
- Python type hints alone do not enforce argument types at runtime. FastMCP validates incoming MCP tool arguments against the declared inputs.
- Valid integers reach the tool body, which returns `left + right`.
- A nonnumeric string such as `"a"` cannot be converted to an integer and is rejected before the tool body executes. This is expected validation behavior, not a broken server.
- Numeric strings may be converted to integers, so a clearly nonnumeric string is a better rejection test.

Examples:

| Arguments | Expected outcome |
| --- | --- |
| `{"left": 7, "right": 5}` | Returns `12` |
| `{"left": "a", "right": 25}` | Validation error for `left` |

By default, the client raises an exception for a failed tool call. The assignment to the result variable and the following print do not finish successfully. An uncaught exception stops the coroutine, but exiting `async with` still cleans up the connection.

## Lesson 5: Handling Tool Errors

Status: completed in [client.py](client.py). A rejected call is caught, and a subsequent valid call succeeds in the same connection and run.

```python
from fastmcp.exceptions import ToolError
```

- Put the awaited tool call inside `try` and catch `ToolError` with `except ToolError as error`.
- Valid arguments return normally and allow the result print inside `try` to run.
- Invalid arguments still fail validation. Catching the exception does not make invalid input acceptable; it lets the client display a useful message and continue.
- When the tool call raises, execution skips the remaining statements inside `try` and enters the matching handler. Code after the handler can run normally.
- Keep the recovery call inside the same `async with` block to demonstrate that a rejected tool call does not require reconnecting.
- A server-side validation warning may still be logged even when the client catches the error. A logged warning is different from an uncaught exception traceback.

Recovery check: `{"left": "a", "right": 25}` produces a handled validation message. The subsequent call with `{"left": 1, "right": 25}` returns `26` without reopening the connection. Both calls remain inside the same `async with` block.

This demonstrates the difference between a tool-call failure and a connection failure: rejecting these arguments does not make the existing MCP connection unusable.

## Next Lesson

Lesson 6 will replace the in-memory connection with stdio transport and run the server as a separate process. The client will launch the server and exchange MCP messages over stdin/stdout. The exercise will set `keep_alive=False` so exiting the connection context also cleans up the server process; the default transport can retain the process for reuse.

The pending exercise is to remove the server-object import from the client, configure `StdioTransport` with `command=sys.executable` and `args=["server.py"]`, and connect with `Client(transport)`. Keep tool discovery and the invalid-then-valid recovery calls. Run from the repository root, confirm the same results across two processes, and confirm subprocess cleanup. Do not start the server manually for this exercise.

## Future Learning Roadmap

The following topics are planned, not completed. Each checkpoint can take multiple small lessons. We will confirm APIs against the installed FastMCP and MCP versions as we reach them rather than assuming every version or host supports every feature.

### Phase 1: Core MCP Capabilities

- [ ] **Separate-process stdio:** complete Lesson 6; understand process ownership, interpreter selection, environment forwarding, working directories, stderr logging, and cleanup.
- [ ] **Streamable HTTP:** start a server independently, connect through its MCP endpoint, and understand request lifetimes, sessions, reconnects, and differences from stdio. Recognize legacy SSE without choosing it for new deployments.
- [ ] **Protocol lifecycle:** initialization, version and capability negotiation, request identifiers, notifications, protocol errors versus tool errors, and connection shutdown. Keep transport code in the framework rather than reimplementing MCP.
- [ ] **Richer tools:** defaults, optional inputs, nested models, constraints, descriptions, structured results and output schemas, content blocks, and tool annotations. Annotations describe behavior; they are not security enforcement.
- [ ] **Resources:** resource URIs, MIME types, resource templates, discovery and reads, and subscriptions/change notifications where supported. Distinguish application-supplied context from executable tools.
- [ ] **Prompts:** reusable prompt templates, arguments, message roles, and prompt discovery/retrieval. Understand how hosts choose to use prompts rather than assuming automatic execution.

Checkpoint: use tools, resources, and prompts through supported real transports and explain their different roles.

### Phase 2: Application Architecture and Reliability

- [ ] **Context and lifecycle:** request context, logging, progress, cancellation, lifespan-managed dependencies, connection pools, and graceful resource cleanup.
- [ ] **Async execution:** coroutine scheduling, blocking work, safe offloading, concurrency limits, timeouts, and cancellation. Avoid blocking the event loop or sharing mutable request state unsafely.
- [ ] **Project structure:** organize tools and shared services, use composition/mounting where appropriate, and learn middleware or other supported cross-cutting hooks without adding unnecessary abstractions.
- [ ] **Configuration:** separate development and production settings, validate configuration at startup, pin dependencies, use a lockfile, and define supported Python/FastMCP/MCP versions.
- [ ] **External integrations:** bounded upstream calls, safe retries, connection pooling, persistent storage, transactions, idempotency, and useful domain errors. Retrying a destructive operation is not automatically safe.
- [ ] **Session and tenant state:** separate durable business data from connection state, isolate users and tenants, and reason about stateful versus stateless deployment and multiple workers.

Checkpoint: replace demonstration-only logic with a small real workflow backed by an external service or database, with predictable failure and cleanup behavior.

### Phase 3: Authentication and Authorization

- [ ] **Security boundaries:** distinguish authentication (who is calling) from authorization (what they may do). Local stdio relies on local process/OS permissions; remote HTTP requires an explicit security design.
- [ ] **Token verification:** learn bearer-token handling and a supported identity-provider integration, including issuer, audience, expiry, signature verification, JWKS/key rotation, and revocation policy. A development static token is not a complete production identity system.
- [ ] **MCP OAuth flows:** protected-resource and authorization-server discovery, OAuth 2.1 concepts, authorization code with PKCE, client registration where supported, consent, redirect validation, scopes, and refresh behavior. Distinguish OAuth authorization from OIDC identity; use established providers and framework integrations rather than inventing an authorization server.
- [ ] **Server-side access control:** default-deny permissions, per-tool/resource checks, least-privilege scopes, roles or attributes, and trusted identity in request context. Check access during execution; hiding a tool from discovery alone is insufficient.
- [ ] **Multi-user isolation:** separate identities and credentials per user/tenant, prevent cross-user data access, and avoid putting request-specific identity into shared global state.
- [ ] **Upstream credentials:** handle service-to-service and user-delegated access, store secrets safely, and prevent token passthrough and confused-deputy problems. Do not forward an MCP bearer token blindly to another API.
- [ ] **Auth failure tests:** missing, expired, tampered, wrong-issuer and wrong-audience tokens; insufficient scopes; revoked access; and cross-tenant requests. Verify discovery and execution behavior and ensure logs do not expose credentials.

Checkpoint: a compatible MCP host can authenticate against a protected server, authorized actions succeed, and unauthorized actions fail with no data leakage.

### Phase 4: Security Hardening and Testing

- [ ] **Untrusted inputs and outputs:** validate paths, URLs, commands, and payload sizes; defend against traversal, SSRF, injection, and unintended access to files or services. Treat tool results and prompt content as untrusted data.
- [ ] **Sensitive operations:** explicit server-side permissions for writes/destructive actions, safe defaults, confirmations where appropriate, and audit trails. Model intent and host approval are not substitutes for server authorization.
- [ ] **HTTP boundaries:** TLS, origin/host validation, DNS-rebinding protections, reverse-proxy trust, secure bind addresses, and bounded request/session lifetimes.
- [ ] **Abuse controls:** per-identity rate limits, quotas, concurrency limits, maximum result/request sizes, timeouts, and protection against expensive or repeated operations.
- [ ] **Automated tests:** unit tests for business logic, schema and error tests, in-memory integration tests, actual stdio/HTTP tests, and fixtures that clean up servers and external dependencies.
- [ ] **Host interoperability:** verify with MCP Inspector and a real host such as Cursor or VS Code; test capability compatibility and authenticated connections, not only the custom client.
- [ ] **CI and dependency safety:** formatting, linting, type checks, automated tests, secret scanning, dependency vulnerability checks, reproducible builds, and controlled upgrades with regression tests.

Checkpoint: security and integration failures are reproducible in automated tests, including attempts to bypass authorization and tenant isolation.

### Phase 5: Deployment and Operations

- [ ] **Packaging and release:** reproducible application/container builds, non-root execution, immutable releases, configuration injection, and documented start/stop procedures.
- [ ] **Production hosting:** TLS termination, load-balancer/proxy configuration, health and readiness probes, graceful shutdown, worker/session behavior, and safe horizontal scaling.
- [ ] **Observability:** structured stderr/application logs, correlation IDs, tracing, latency/error metrics, auth/security audit events, and alerts. Redact secrets and sensitive user/tool data.
- [ ] **Capacity and resilience:** load tests, concurrency/backpressure tuning, upstream failures, resource exhaustion, connection loss, and infrastructure-level recovery.
- [ ] **Operations:** secret/key rotation, storage backup and restore when applicable, incident response, rollback, compatibility/migration policy, and operator runbooks.

Checkpoint: deploy a protected staging server, demonstrate an authenticated end-to-end workflow, observe it under load, and exercise shutdown, recovery, and rollback.

### Advanced Features: Evaluate When Needed

- [ ] Sampling and elicitation: supported capabilities, human consent, trust boundaries, and restrictions on requesting sensitive information.
- [ ] Background tasks/long-running work: progress, cancellation, durability, task ownership, and version-specific support.
- [ ] Tool filtering/transformation, proxying, and multi-server composition: naming conflicts, preserved identity, and authorization at every boundary.
- [ ] MCP Apps or richer media/content: host support, UI security boundaries, and safe rendering.

These features are not mandatory for every production server. Implement them when the chosen use case and client support justify them; understanding when not to use a feature is part of the course.

## Production Readiness Criteria

Adding authentication alone does not make a server production-ready. The final project should satisfy the following gates for its chosen deployment and use case:

- [ ] The real business workflow, supported clients, transport, protocol versions, and trust boundaries are documented.
- [ ] Schemas, tool descriptions, responses, and domain errors form a stable, tested contract.
- [ ] Authentication, authorization, and tenant isolation are enforced server-side and covered by negative tests.
- [ ] Untrusted inputs, sensitive operations, secrets, and HTTP/network exposure are handled securely.
- [ ] Timeouts, cancellation, quotas, concurrency limits, idempotency, and dependency failures have defined behavior.
- [ ] Automated tests and CI cover business logic, real transports, security boundaries, and host interoperability.
- [ ] Builds and dependency versions are reproducible; deployment, health checks, and shutdown are verified.
- [ ] Logs, metrics, traces, and audit events provide useful visibility without leaking credentials or sensitive data.
- [ ] Load targets, operational ownership, key rotation, rollback, and recovery procedures are documented and exercised.

## References

- [FastMCP quickstart](https://gofastmcp.com/getting-started/quickstart)
- [FastMCP installation](https://gofastmcp.com/getting-started/installation)
- [FastMCP client transports](https://gofastmcp.com/clients/transports)
- [FastMCP documentation index](https://gofastmcp.com/llms.txt)
- [MCP documentation](https://modelcontextprotocol.io/docs/getting-started/intro)
- [MCP specification](https://modelcontextprotocol.io/specification)
