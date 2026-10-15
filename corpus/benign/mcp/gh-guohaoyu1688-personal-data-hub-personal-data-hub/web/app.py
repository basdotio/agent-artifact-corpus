"""Loopback REST API and offline Swagger UI sharing the same masked storage layer."""

import secrets
import sqlite3
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ..core.store import Conflict, Hub, NotFound


def envelope(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data, "warnings": []}


def create_app(hub: Hub, token: str | None = None) -> FastAPI:
    app = FastAPI(title="Personal Data Hub", version="0.1.1", docs_url=None, redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])
    bearer = HTTPBearer(auto_error=False)
    static = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static), name="static")
    app.mount(
        "/docs-assets", StaticFiles(directory=static / "vendor" / "swagger-ui"), name="docs-assets"
    )

    @app.middleware("http")
    async def same_origin(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin and request.method not in {"GET", "HEAD", "OPTIONS"}:
            parsed = urlparse(origin)
            if parsed.netloc != request.headers.get("host"):
                return JSONResponse(
                    {
                        "ok": False,
                        "error": {
                            "code": "FORBIDDEN",
                            "message": "cross-origin writes are blocked",
                        },
                    },
                    status_code=403,
                )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    def authorize(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
        if token and (
            credentials is None or not secrets.compare_digest(credentials.credentials, token)
        ):
            raise HTTPException(status_code=401, detail="valid bearer token required")

    auth = [Depends(authorize)]

    @app.exception_handler(NotFound)
    async def not_found(request: Request, exc: NotFound):
        return JSONResponse(
            {"ok": False, "error": {"code": "NOT_FOUND", "message": str(exc)}}, status_code=404
        )

    @app.exception_handler(Conflict)
    @app.exception_handler(sqlite3.IntegrityError)
    async def conflict(request: Request, exc: Exception):
        return JSONResponse(
            {"ok": False, "error": {"code": "CONFLICT", "message": str(exc)}}, status_code=409
        )

    @app.exception_handler(ValueError)
    async def invalid(request: Request, exc: ValueError):
        return JSONResponse(
            {"ok": False, "error": {"code": "INVALID_ARGUMENT", "message": str(exc)}},
            status_code=422,
        )

    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, exc: RequestValidationError):
        # Do not echo invalid input values (they may contain sensitive personal fields).
        return JSONResponse(
            {
                "ok": False,
                "error": {
                    "code": "INVALID_ARGUMENT",
                    "message": "request parameters/body failed validation",
                },
            },
            status_code=422,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return JSONResponse(
            {
                "ok": False,
                "error": {
                    "code": "UNAUTHORIZED" if exc.status_code == 401 else "HTTP_ERROR",
                    "message": str(exc.detail),
                },
            },
            status_code=exc.status_code,
        )

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(static / "index.html")

    @app.get("/docs", include_in_schema=False)
    def docs():
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title="Personal Data Hub API",
            swagger_js_url="/docs-assets/swagger-ui-bundle.js",
            swagger_css_url="/docs-assets/swagger-ui.css",
            swagger_favicon_url="/static/favicon.svg",
            swagger_ui_parameters={"validatorUrl": None},
        )

    @app.get("/api/tables", dependencies=auth)
    def tables():
        return envelope(hub.tables())

    @app.get("/api/schema/{table}", dependencies=auth)
    def schema(table: str, reveal: bool = False):
        return envelope(hub.describe(table, reveal))

    @app.get("/api/rows/{table}", dependencies=auth)
    def query_rows(
        table: str,
        where: str | None = None,
        fields: str | None = None,
        limit: int = Query(50, ge=1, le=10000),
        offset: int = Query(0, ge=0),
        search: str | None = None,
        reveal: bool = False,
    ):
        return envelope(
            hub.query(
                table, where, fields.split(",") if fields else None, limit, offset, search, reveal
            )
        )

    @app.get("/api/rows/{table}/{row_id}", dependencies=auth)
    def get_row(table: str, row_id: str, reveal: bool = False):
        return envelope(hub.get(table, row_id, reveal))

    @app.post("/api/rows/{table}", dependencies=auth, status_code=201)
    def insert_row(
        table: str,
        data: Annotated[dict[str, Any], Body()],
        reveal: bool = False,
        actor: Annotated[str, Header(alias="X-Actor")] = "web",
    ):
        return envelope(hub.insert(table, data, actor, reveal))

    @app.patch("/api/rows/{table}/{row_id}", dependencies=auth)
    def update_row(
        table: str,
        row_id: str,
        data: Annotated[dict[str, Any], Body()],
        reveal: bool = False,
        expected_updated_at: str | None = None,
        actor: Annotated[str, Header(alias="X-Actor")] = "web",
    ):
        return envelope(hub.update(table, row_id, data, actor, reveal, expected_updated_at))

    @app.delete("/api/rows/{table}/{row_id}", dependencies=auth)
    def delete_row(
        table: str,
        row_id: str,
        confirm: bool = False,
        actor: Annotated[str, Header(alias="X-Actor")] = "web",
    ):
        return envelope(hub.delete(table, row_id, confirm, actor))

    @app.get("/api/history", dependencies=auth)
    def history(
        table: str | None = None,
        row_id: str | None = None,
        limit: int = Query(100, ge=1, le=10000),
        reveal: bool = False,
    ):
        return envelope(hub.history(table, row_id, limit, reveal))

    @app.post("/api/revert/{change_id}", dependencies=auth)
    def revert(
        change_id: str,
        confirm: bool = False,
        reveal: bool = False,
        actor: Annotated[str, Header(alias="X-Actor")] = "web",
    ):
        return envelope(hub.revert(change_id, confirm, actor, reveal))

    @app.get("/api/due", dependencies=auth)
    def due(within: str = "30d", reveal: bool = False):
        return envelope(hub.due(within, reveal))

    @app.get("/api/export/{table}", dependencies=auth)
    def export(
        table: str,
        format: str = "csv",
        where: str | None = None,
        reveal: bool = False,
        search: str | None = None,
    ):
        content, _ = hub.export_text(table, format, where, reveal, search=search)
        return Response(
            content,
            media_type="text/csv" if format == "csv" else "application/json",
            headers={"Content-Disposition": f'attachment; filename="{table}.{format}"'},
        )

    return app
