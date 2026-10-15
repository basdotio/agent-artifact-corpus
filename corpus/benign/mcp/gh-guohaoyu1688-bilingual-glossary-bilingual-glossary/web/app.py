"""Local-only browser editor using the shared storage and validation layer."""

from pathlib import Path
from urllib.parse import urlparse
from xml.etree.ElementTree import ParseError

from defusedxml.common import DefusedXmlException
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ..cli import ok
from ..core.store import Glossary, GlossError, read_terms


def create_app(glossary: Glossary) -> FastAPI:
    app = FastAPI(title="Bilingual Glossary", docs_url=None, redoc_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]"])
    static = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static), name="static")

    @app.middleware("http")
    async def guard(request: Request, call_next):
        origin = request.headers.get("origin")
        if (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and origin
            and urlparse(origin).netloc != request.headers.get("host")
        ):
            return JSONResponse(
                {
                    "ok": False,
                    "error": {"code": "FORBIDDEN", "message": "Cross-origin writes blocked"},
                },
                status_code=403,
            )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(GlossError)
    async def error(request, exc):
        return JSONResponse(
            {"ok": False, "error": {"code": exc.code, "message": str(exc)}},
            status_code=404 if exc.exit_code == 3 else 400,
        )

    @app.exception_handler(DefusedXmlException)
    @app.exception_handler(ParseError)
    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse(
            {"ok": False, "error": {"code": "INVALID_INPUT", "message": str(exc)}}, status_code=400
        )

    @app.get("/")
    def index():
        return FileResponse(static / "index.html")

    @app.get("/api/terms")
    def listing(query: str = "", domain: str | None = None):
        return ok(glossary.search(query, domain, limit=100) if query else glossary.list(domain))

    @app.get("/api/domains")
    def domains():
        return ok(sorted({row["domain"] for row in glossary.list()}))

    @app.post("/api/terms")
    def add(record: dict):
        return ok(glossary.add(record))

    @app.patch("/api/terms/{identifier}")
    def update(identifier: str, payload: dict):
        return ok(
            glossary.update(
                identifier, payload.get("changes", {}), payload.get("expected_updated_at")
            )
        )

    @app.post("/api/import")
    def import_file(payload: dict):
        text = payload.get("text", "")
        if not isinstance(text, str) or len(text) > 10_000_000:
            raise GlossError("Import is too large")
        return ok(
            glossary.import_records(
                read_terms(text, payload.get("format", "json")),
                payload.get("replace") is True,
                payload.get("confirm") is True,
            )
        )

    @app.get("/api/export")
    def export(format: str = "json"):
        return Response(
            glossary.export_text(format),
            media_type="application/json" if format == "json" else "text/plain",
            headers={"Content-Disposition": f'attachment; filename="glossary.{format}"'},
        )

    return app
