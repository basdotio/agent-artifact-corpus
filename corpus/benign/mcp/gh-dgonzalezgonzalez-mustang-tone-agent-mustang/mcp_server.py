"""Transport-independent tools proxy one local backend, so agents share its hardware lock."""

from __future__ import annotations

import os

import httpx
from mcp.server.fastmcp import FastMCP

from .config import token


def make_server():
    server = FastMCP(
        "Mustang Tone Agent",
        host="127.0.0.1",
        stateless_http=True,
        json_response=True,
        instructions="GT40 control. Call capabilities before planning; only observed models are writable. "
        "Recording requires user readiness. Job completion reports verified results, not tap success.",
    )

    async def call(method, path, body=None, request_id=None):
        base = os.environ.get("MUSTANG_BACKEND", "http://127.0.0.1:8765")
        async with httpx.AsyncClient(
            base_url=base, timeout=45, headers={"Authorization": f"Bearer {token()}"}
        ) as client:
            response = await client.request(
                method, path, json=body, headers={"Idempotency-Key": request_id} if request_id else None
            )
            if response.is_error:
                raise ValueError(
                    response.json().get("detail", response.text)
                    if "json" in response.headers.get("content-type", "")
                    else response.text
                )
            return response.json()

    @server.tool()
    async def get_capabilities() -> dict:
        """Get verified model catalog, units, limits and TonePlan JSON Schema."""
        return await call("GET", "/api/capabilities")

    @server.tool()
    async def get_connections() -> dict:
        """Check phone/USB connection. Does not change amp settings."""
        return await call("GET", "/api/connections")

    @server.tool()
    async def create_session(song: str, artist: str, slot: int = 172) -> dict:
        """Start a session using the user's Telecaster bridge/standard-tuning profile. Only Empty slots editable."""
        return await call("POST", "/api/sessions", {"song": song, "artist": artist, "slot": slot})

    @server.tool()
    async def get_session(session_id: str) -> dict:
        """Get plans, takes, baseline variability, stop status and source evidence."""
        return await call("GET", f"/api/sessions/{session_id}")

    @server.tool()
    async def apply_preset(session_id: str, plan: dict, request_id: str) -> dict:
        """Validate and apply a TonePlan. Returns a job ID; request_id makes retrying this action idempotent."""
        return await call(
            "POST", f"/api/sessions/{session_id}/apply", {"plan": plan, "request_id": request_id}
        )

    @server.tool()
    async def attach_reference(
        session_id: str,
        url: str,
        source: str,
        permitted: bool = False,
        start: float = 0,
        duration: float = 20,
    ) -> dict:
        """Acquire a reference excerpt you may process. Free public sources only; no account/access bypass."""
        return await call(
            "POST",
            f"/api/sessions/{session_id}/reference",
            {"url": url, "source": source, "permitted": permitted, "start": start, "duration": duration},
        )

    @server.tool()
    async def separate_guitar(session_id: str) -> dict:
        """Run optional local Demucs guitar separation on an attached reference. Returns a job."""
        return await call("POST", f"/api/sessions/{session_id}/separate", {})

    @server.tool()
    async def record_take(
        session_id: str, role: str = "baseline", ready: bool = False, request_id: str | None = None
    ) -> dict:
        """Record 10 seconds of Fender USB guitar. ready must reflect the user's explicit readiness to play."""
        return await call(
            "POST", f"/api/sessions/{session_id}/capture", {"role": role, "ready": ready}, request_id
        )

    @server.tool()
    async def get_job(job_id: str) -> dict:
        """Read compact asynchronous operation progress/result."""
        return await call("GET", f"/api/jobs/{job_id}")

    @server.tool()
    async def compare_takes(session_id: str) -> dict:
        """Read baseline variability, diagnostic distances and retained best candidate, without audio bytes."""
        return await call("GET", f"/api/sessions/{session_id}/comparisons")

    @server.tool()
    async def propose_adjustment(session_id: str, direction: str | None = None) -> dict:
        """Get a bounded local candidate. Does not apply it. Optional direction: brighter/darker/gain_up/gain_down."""
        return await call("POST", f"/api/sessions/{session_id}/candidate", {"direction": direction})

    @server.tool()
    async def save_preset(session_id: str, request_id: str | None = None) -> dict:
        """Save, reload and verify the session's preset. Returns a job."""
        return await call("POST", f"/api/sessions/{session_id}/save", {}, request_id)

    @server.tool()
    async def restore_preset(session_id: str, best: bool = False, request_id: str | None = None) -> dict:
        """Restore the original empty checkpoint, or the best measured candidate if best=true."""
        return await call("POST", f"/api/sessions/{session_id}/restore", {"best": best}, request_id)

    @server.tool()
    async def submit_feedback(session_id: str, description: str = "", accepted: bool = False) -> dict:
        """Record listening feedback. accepted=true stops refinement without claiming measured similarity."""
        return await call(
            "POST", f"/api/sessions/{session_id}/feedback", {"description": description, "accepted": accepted}
        )

    @server.tool()
    async def cancel_operation() -> dict:
        """Stop pending control/recording at the next safe boundary; does not automatically restore."""
        return await call("POST", "/api/stop", {})

    return server


if __name__ == "__main__":
    make_server().run(transport="stdio")
