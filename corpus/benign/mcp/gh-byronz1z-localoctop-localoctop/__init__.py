"""localoctop — server-side adapter bridging Octop's MCP connector to
employee machines running the localoctop (Go) client.

Layout:
    config.py      environment-driven settings + token store
    errors.py      wire error codes (mirror of localoctop/errors.go)
    protocol.py    JSON-RPC envelope + tool schemas (contract with the client)
    sessions.py    outbound-WSS bridge session registry (per user)
    bridge_ws.py   /mcp/localoctop/ws endpoint the Go client dials
    tools.py       fan-out of MCP tools/call to the user's bridge session
    mcp_app.py     /mcp/localoctop/ streamable_http endpoint (initialize,
                   tools/list, tools/call) for Octop's custom MCP connector
    audit.py       server-side call log (JSON lines)
    app.py         FastAPI assembly + /healthz
    main.py        uvicorn entrypoint

The package is fully self-contained: it imports nothing from the Octop
codebase and references no paths outside its own directory.
"""

__version__ = "0.7.0"
