"""MCP transport entry points."""

from __future__ import annotations

from dartlab.mcp.server import createServer, mcpLog


def runStdio() -> None:
    """stdio 모드로 MCP 서버를 실행한다.

    Returns:
        None: 서버 event loop 를 종료될 때까지 실행한다.

    Example:
        `runStdio()`

    Raises:
        ImportError: MCP stdio transport 를 import 할 수 없을 때.
    """
    import asyncio

    try:
        from mcp.server.stdio import stdio_server
    except ImportError as initial_exc:
        # editable install 또는 cwd-collision 우회 — sys.path 의 어떤 path 가
        # 'mcp' 를 dartlab.mcp 로 잡았을 가능성. diagnostic dump 후 cleanup.
        import os
        import sys
        from pathlib import Path

        # Diagnostic: stderr 에 sys.path + 발견된 mcp 패키지 dump (CI 회귀 추적용)
        sys.stderr.write(f"[dartlab.mcp] initial import failed: {initial_exc}\n")
        sys.stderr.write(f"[dartlab.mcp] cwd={os.getcwd()}\n")
        sys.stderr.write(f"[dartlab.mcp] sys.path={sys.path}\n")
        for _i, _p in enumerate(sys.path):
            _cand = os.path.join(_p, "mcp", "__init__.py")
            if os.path.exists(_cand):
                sys.stderr.write(f"[dartlab.mcp]   sys.path[{_i}]={_p!r} has mcp at {_cand}\n")
        # 'mcp' 로 잘못 잡힌 path 들을 모두 제거. 판정: standalone mcp SDK 는
        # 'mcp/server/__init__.py' 가 존재. 그게 없는 path 의 mcp 는 collision
        # (dartlab/mcp 또는 tests/mcp 등).
        _badPaths = set()
        for _p in sys.path:
            _cand = os.path.join(_p, "mcp", "__init__.py")
            if not os.path.exists(_cand):
                continue
            _serverInit = os.path.join(_p, "mcp", "server", "__init__.py")
            if not os.path.exists(_serverInit):
                _badPaths.add(os.path.normpath(_p))
        sys.stderr.write(f"[dartlab.mcp] removing bad paths: {_badPaths}\n")
        for _k in [k for k in sys.modules if k == "mcp" or k.startswith("mcp.")]:
            del sys.modules[_k]
        sys.path[:] = [p for p in sys.path if os.path.normpath(p) not in _badPaths]
        try:
            from mcp.server.stdio import stdio_server
        except ImportError as exc:
            raise ImportError("MCP SDK 필요: pip install --upgrade dartlab") from exc

    app = createServer()

    async def main() -> None:
        """stdio stream 을 열고 MCP server 를 실행한다.

        Returns:
            None: stream 이 닫힐 때까지 server run 을 수행한다.

        Example:
            `await main()`

        Raises:
            RuntimeError: stdio transport 연결 또는 server run 이 실패할 때.
        """
        async with stdio_server() as (readStream, writeStream):
            mcpLog.info("DartLab MCP 서버 시작 (stdio)")
            await app.run(readStream, writeStream, app.create_initialization_options())

    asyncio.run(main())


def createSseApp():
    """SSE 전송 기반 ASGI 앱을 생성한다.

    Returns:
        Starlette: `/sse` 와 `/messages/` route 를 가진 ASGI 앱.

    Example:
        `app = createSseApp()`

    Raises:
        ImportError: MCP SSE transport 또는 Starlette 를 import 할 수 없을 때.
    """
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route

    mcpServer = createServer()
    sse = SseServerTransport("/messages/")

    async def handleSse(request):
        """SSE 연결 handshake 로 MCP 양방향 stream 을 연다.

        Args:
            request: Starlette Request 객체.

        Returns:
            None: 연결 생명주기 동안 MCP server run 을 수행한다.

        Example:
            `await handleSse(request)`

        Raises:
            RuntimeError: SSE transport 연결 또는 MCP server run 이 실패할 때.
        """
        async with sse.connect_sse(request.scope, request.receive, request._send) as (read, write):
            await mcpServer.run(read, write, mcpServer.create_initialization_options())

    return Starlette(
        routes=[
            Route("/sse", endpoint=handleSse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


def createStreamableHttpApp(*, jsonResponse: bool = False):
    """Streamable HTTP (MCP 2024-11) 전송 기반 ASGI 앱을 생성한다.

    마스터 플랜 v2 트랙 7 PR-M4 — SSE 는 deprecate 트래커 부착 (옛 client 호환만 유지) 하고
    Streamable HTTP 가 표준. Cursor/Cline 외부 client 는 본 transport 로 연결.

    Args:
        jsonResponse: ``True`` 시 단일 JSON 응답 모드 (stream 없음, batch 요청용).
            기본 ``False`` = SSE 양방향 stream.

    Returns:
        Starlette: ``/mcp`` (GET/POST/DELETE) endpoint 를 가진 ASGI 앱. session 은
        ``Mcp-Session-Id`` 헤더로 추적.

    Example:
        ``app = createStreamableHttpApp()``

    Raises:
        ImportError: MCP Streamable HTTP transport 또는 Starlette 를 import 할 수 없을 때.
    """
    from contextlib import asynccontextmanager

    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from starlette.applications import Starlette
    from starlette.routing import Mount

    mcpServer = createServer()
    sessionManager = StreamableHTTPSessionManager(
        app=mcpServer,
        event_store=None,
        json_response=jsonResponse,
        stateless=False,
    )

    async def handleStreamableHttp(scope, receive, send):
        """Streamable HTTP request 를 session manager 로 dispatch.

        Args:
            scope: ASGI scope.
            receive: ASGI receive callable.
            send: ASGI send callable.

        Returns:
            None: session manager 가 응답 작성.
        """
        await sessionManager.handle_request(scope, receive, send)

    @asynccontextmanager
    async def lifespan(_app):
        """session manager 생명주기 관리 — app start/stop 동행."""
        async with sessionManager.run():
            mcpLog.info("DartLab MCP 서버 시작 (Streamable HTTP)")
            yield

    return Starlette(
        routes=[Mount("/mcp", app=handleStreamableHttp)],
        lifespan=lifespan,
    )


def runStreamableHttp(host: str = "0.0.0.0", port: int = 8002, *, jsonResponse: bool = False) -> None:
    """Streamable HTTP 모드로 MCP HTTP 서버를 실행한다.

    마스터 플랜 v2 트랙 7 PR-M4 — 외부 client (Cursor/Cline) 의 MCP 표준 transport.

    Args:
        host: bind host.
        port: bind port (SSE 와 격리 — 기본 8002, SSE 는 8001).
        jsonResponse: True 시 단일 JSON 응답 모드.

    Returns:
        None: uvicorn 서버를 종료될 때까지 실행한다.

    Example:
        ``runStreamableHttp(host="127.0.0.1", port=8002)``

    Raises:
        ImportError: uvicorn 또는 Streamable HTTP app 의 의존성을 import 할 수 없을 때.
    """
    import uvicorn

    mcpLog.info("DartLab MCP 서버 시작 (Streamable HTTP http://%s:%d/mcp)", host, port)
    uvicorn.run(createStreamableHttpApp(jsonResponse=jsonResponse), host=host, port=port)


def runSse(host: str = "0.0.0.0", port: int = 8001) -> None:
    """SSE 모드로 MCP HTTP 서버를 실행한다.

    Args:
        host: bind host.
        port: bind port.

    Returns:
        None: uvicorn 서버를 종료될 때까지 실행한다.

    Example:
        `runSse(host="127.0.0.1", port=8001)`

    Raises:
        ImportError: uvicorn 또는 SSE app 의 의존성을 import 할 수 없을 때.
    """
    import uvicorn

    mcpLog.info("DartLab MCP 서버 시작 (SSE http://%s:%d/sse)", host, port)
    uvicorn.run(createSseApp(), host=host, port=port)
