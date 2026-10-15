import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from .store import Conflict, Store

STATIC = Path(__file__).parent / 'static'


class MemberInput(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class TaskInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    owner_id: str
    due_at: str
    priority: Literal[1, 2, 3] = 2
    request_id: str = Field(min_length=1, max_length=128)


class ChangeInput(BaseModel):
    actor_id: str
    version: int = Field(ge=1)
    action: Literal['propose', 'accept', 'decline', 'complete']
    target_id: str | None = None


class AccessGuard:
    """Protect both REST and MCP without buffering streaming responses."""
    def __init__(self, app, token):
        self.app, self.token = app, token

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http' and scope['path'].startswith(('/api', '/mcp')):
            headers = dict(scope.get('headers', []))
            auth = headers.get(b'authorization', b'').decode(errors='replace')
            origin = headers.get(b'origin')
            host = headers.get(b'host', b'').decode()
            if origin and origin.decode() not in ('http://' + host, 'https://' + host):
                await JSONResponse({'detail': 'Cross-origin access is disabled'}, status_code=403)(scope, receive, send)
                return
            if self.token:
                if not secrets.compare_digest(auth, 'Bearer ' + self.token):
                    await JSONResponse({'detail': 'A household access token is required'}, status_code=401)(scope, receive, send)
                    return
            else:
                client = (scope.get('client') or ('',))[0]
                local_host = host.split(':')[0] in ('localhost', '127.0.0.1', 'testserver') or host.startswith('[::1]')
                if client not in ('127.0.0.1', '::1', 'testclient') or not local_host:
                    await JSONResponse({'detail': 'Set HOMERELAY_TOKEN for network access'}, status_code=403)(scope, receive, send)
                    return
        await self.app(scope, receive, send)


def create_app(db_path=None, token=None):
    store = Store(db_path or os.getenv('HOMERELAY_DB', 'data/homerelay.db'))
    mcp = FastMCP('HomeRelay', stateless_http=True, json_response=True, streamable_http_path='/',
                  instructions='Trusted single-household demo. Ask the person to confirm every write. '
                  'Read the latest version before changes. Never infer that a proposed handoff was accepted. '
                  'Actor IDs describe the selected member; this demo does not authenticate individual people.')

    @mcp.tool(annotations={'readOnlyHint': True})
    def household_board() -> dict[str, Any]:
        """Read members and current tasks before proposing or confirming a change."""
        return {'members': store.members(), 'tasks': store.list_tasks()}

    @mcp.tool(annotations={'readOnlyHint': True})
    def household_briefing(member_id: str) -> dict[str, Any]:
        """Get a grounded spoken briefing, overdue tasks and pending handoffs for a member."""
        return store.briefing(member_id)

    @mcp.tool()
    def create_household_task(title: str, owner_id: str, due_at: str, priority: int, request_id: str) -> dict[str, Any]:
        """After confirmation, create an errand. Due time needs a timezone. Reuse request_id on retries."""
        return store.create(title, owner_id, due_at, priority, request_id)

    @mcp.tool()
    def propose_handoff(task_id: str, actor_id: str, recipient_id: str, version: int) -> dict[str, Any]:
        """After owner confirmation, propose a handoff. Ownership stays until the recipient accepts."""
        return store.change(task_id, actor_id, version, 'propose', recipient_id)

    @mcp.tool()
    def respond_to_handoff(task_id: str, actor_id: str, version: int, accept: bool) -> dict[str, Any]:
        """After recipient confirmation, accept or decline a pending handoff using the latest version."""
        return store.change(task_id, actor_id, version, 'accept' if accept else 'decline')

    @mcp.tool()
    def complete_household_task(task_id: str, actor_id: str, version: int) -> dict[str, Any]:
        """After the current owner confirms completion, close the task and record the action."""
        return store.change(task_id, actor_id, version, 'complete')

    @asynccontextmanager
    async def lifespan(app):
        async with mcp.session_manager.run():
            yield

    app = FastAPI(title='HomeRelay', version='0.1.0', lifespan=lifespan)
    app.state.store = store
    app.state.mcp = mcp
    app.add_middleware(AccessGuard, token=token if token is not None else os.getenv('HOMERELAY_TOKEN', ''))

    @app.exception_handler(Conflict)
    async def conflict(request: Request, exc: Conflict):
        return JSONResponse({'detail': str(exc)}, status_code=409)

    @app.exception_handler(ValueError)
    async def invalid(request: Request, exc: ValueError):
        return JSONResponse({'detail': str(exc)}, status_code=422)

    @app.exception_handler(KeyError)
    async def missing(request: Request, exc: KeyError):
        return JSONResponse({'detail': 'Task not found'}, status_code=404)

    @app.get('/')
    def index():
        return FileResponse(STATIC / 'index.html')

    @app.get('/health')
    def health():
        return {'status': 'ok', 'version': '0.1.0'}

    @app.get('/api/board')
    def board():
        return {'members': store.members(), 'tasks': store.list_tasks(), 'history': store.history()}

    @app.post('/api/members', status_code=201)
    def add_member(body: MemberInput):
        return store.add_member(body.name)

    @app.post('/api/tasks', status_code=201)
    def add_task(body: TaskInput):
        return store.create(**body.model_dump())

    @app.post('/api/tasks/{task_id}/change')
    def change(task_id: str, body: ChangeInput):
        return store.change(task_id, **body.model_dump())

    @app.get('/api/briefing/{member_id}')
    def briefing(member_id: str):
        return store.briefing(member_id)

    app.mount('/static', StaticFiles(directory=STATIC), name='static')
    app.mount('/mcp', mcp.streamable_http_app())
    return app


app = create_app()
