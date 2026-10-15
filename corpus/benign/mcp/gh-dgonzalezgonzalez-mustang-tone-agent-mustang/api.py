from __future__ import annotations

import secrets
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import audio, references
from .config import DATA, ROOT, token
from .mcp_server import make_server
from .models import CaptureRequest, Feedback, ReferenceRequest, SessionRequest, TonePlan
from .service import Service


class ApplyBody(BaseModel):
    plan: TonePlan
    request_id: str | None = Field(default=None, max_length=100)


class RestoreBody(BaseModel):
    best: bool = False


class CandidateBody(BaseModel):
    direction: str | None = None


def create_app(service=None):
    service = service or Service()
    mcp = make_server()
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app):
        async with mcp.session_manager.run():
            yield
        service.cancel.set()
        service.pool.shutdown(wait=False, cancel_futures=True)

    app = FastAPI(title="Mustang Tone Agent", version="0.1.0", lifespan=lifespan)
    app.state.service = service
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

    @app.middleware("http")
    async def protect(request: Request, next_handler):
        if request.url.path.startswith(("/api/", "/mcp")):
            expected = f"Bearer {token()}"
            if not secrets.compare_digest(request.headers.get("authorization", ""), expected):
                return JSONResponse({"detail": "Local access token required"}, status_code=401)
            origin = request.headers.get("origin")
            if origin and origin not in {
                "http://127.0.0.1:8765",
                "http://localhost:8765",
                "http://testserver",
            }:
                return JSONResponse({"detail": "Untrusted origin"}, status_code=403)
        response = await next_handler(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.exception_handler(ValueError)
    async def bad_request(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(KeyError)
    async def not_found(request, exc):
        return JSONResponse({"detail": "Record not found"}, status_code=404)

    @app.get("/health")
    def health():
        return {"ok": True, "version": "0.1.0"}

    @app.get("/api/connections")
    def connections():
        return service.connections()

    @app.get("/api/capabilities")
    def capabilities():
        return service.capabilities()

    @app.get("/api/state")
    def state():
        return {
            "sessions": service.store.list("session"),
            "presets": service.store.list("preset"),
            "jobs": service.store.list("job")[:20],
            "active_job": service.active_job,
        }

    @app.post("/api/sessions")
    def create_session(body: SessionRequest):
        return service.create_session(body)

    @app.get("/api/sessions/{key}")
    def session(key: str):
        return service.session(key)

    @app.post("/api/sessions/{key}/apply")
    def apply(key: str, body: ApplyBody):
        return service.apply(key, body.plan, body.request_id)

    @app.post("/api/sessions/{key}/save")
    def save(key: str, request: Request):
        return service.save(key, request.headers.get("idempotency-key"))

    @app.post("/api/sessions/{key}/restore")
    def restore(key: str, body: RestoreBody, request: Request):
        return service.restore(key, request.headers.get("idempotency-key"), best=body.best)

    @app.post("/api/stop")
    def stop():
        return service.stop()

    @app.post("/api/sessions/{key}/reference")
    def reference(key: str, body: ReferenceRequest, request: Request):
        return service.acquire(key, body, request.headers.get("idempotency-key"))

    @app.post("/api/sessions/{key}/upload")
    async def upload(
        key: str, file: UploadFile = File(...), permitted: bool = Form(False), quality: str = Form("mixed")
    ):
        service.session(key)
        if not permitted:
            raise HTTPException(400, "Confirm that you may process this recording")
        if service.active_job:
            raise HTTPException(409, "Wait for the active operation")
        name = str(uuid.uuid4())
        temporary = DATA / "audio" / f"{name}.upload"
        destination = DATA / "audio" / f"{name}.wav"
        total = 0
        try:
            with temporary.open("wb") as output:
                while chunk := await file.read(1024 * 1024):
                    total += len(chunk)
                    if total > 80_000_000:
                        raise HTTPException(413, "Audio file exceeds 80 MB")
                    output.write(chunk)

            # Decoding lives in the same cancellable job queue as other work.
            def work(s, progress):
                try:
                    references.clip(temporary, destination, 0, 30, service.cancel)
                    return service.attach_reference(
                        key, destination, Path(file.filename or "local audio").name, quality=quality
                    )
                finally:
                    temporary.unlink(missing_ok=True)

            return service.submit(key, "upload", work)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    @app.post("/api/sessions/{key}/separate")
    def separate(key: str, request: Request):
        return service.separate(key, request.headers.get("idempotency-key"))

    @app.post("/api/sessions/{key}/capture")
    def capture(key: str, body: CaptureRequest, request: Request):
        return service.capture(key, body, request.headers.get("idempotency-key"))

    @app.post("/api/sessions/{key}/feedback")
    def feedback(key: str, body: Feedback):
        return service.feedback(key, body)

    @app.post("/api/sessions/{key}/candidate")
    def candidate(key: str, body: CandidateBody):
        return service.candidate(key, body.direction)

    @app.get("/api/jobs/{key}")
    def job(key: str):
        return service.store.get(key, "job")

    @app.get("/api/sessions/{key}/comparisons")
    def comparisons(key: str):
        return service.comparisons(key)

    @app.get("/api/audio/{key}")
    def metadata(key: str):
        item = service.store.get(key, "audio").copy()
        item.pop("path", None)
        return item

    @app.get("/api/audio/{key}/play")
    def play(key: str):
        item = service.store.get(key, "audio")
        path = Path(item["path"])
        if not path.resolve().is_relative_to((DATA / "audio").resolve()):
            raise HTTPException(400, "Audio path invalid")
        destination = path.with_name(path.stem + "-matched.wav")
        if not destination.exists():
            audio.matched_audio(path, destination)
        return FileResponse(destination, media_type="audio/wav")

    @app.get("/api/demo-plan")
    def demo_plan():
        path = ROOT / "examples/atom-city-queen.json"
        if not path.exists():
            raise HTTPException(404, "Demo catalog calibration in progress")
        import json

        return json.loads(path.read_text(encoding="utf-8"))

    if (ROOT / "web/dist/assets").exists():
        app.mount("/assets", StaticFiles(directory=ROOT / "web/dist/assets"), name="assets")

    @app.get("/")
    def index():
        path = ROOT / "web/dist/index.html"
        return (
            FileResponse(path)
            if path.exists()
            else JSONResponse({"detail": "Build UI with npm run build in web"})
        )

    app.mount("/", mcp_app)
    return app
