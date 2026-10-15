"""Fatima Voice Studio as an MCP server, so AI agents (Claude Code, Codex, Antigravity, Hermes, …) can drive it.

The tools call Fatima Voice Studio's own HTTP API, so the same server works two ways:
  * built in:  http://127.0.0.1:<port>/mcp  (streamable HTTP; header  Authorization: Bearer <api key>)
  * stdio:     python studio_mcp.py         (for agents that only launch local commands)

Guard rails: agents can't download models or delete anything; non-commercial models are refused unless
allowed on the Connect page; voice clips and script files are only read from the folders listed there;
everything an agent exports goes into the Exports folder from Settings.
"""
import asyncio
import json
import re
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

INSTRUCTIONS = """Fatima Voice Studio turns text into speech on this PC's GPU (Qwen3-TTS), in voices from its voice library.
Typical flow: list_voices -> create_batch (one or more scripts) -> wait_for_batch -> check parts flagged
"check" (listen or read why) -> regenerate_part / edit_part -> export_batch.
Use speak for one quick line. Each finished script becomes WAV/MP3 plus SRT subtitles in the batch folder.
Add [pause] or [pause 2s] in a script for a silence. Files you pass must be inside the folders allowed on the
Connect page (see get_settings). Exports always go to the Exports folder from Settings."""

MAX_FILE_BYTES = 50 * 1024 * 1024
BUSY = ("running", "queued", "finishing")


class Studio:
    """Thin client for Fatima Voice Studio's HTTP API."""

    def __init__(self, base: str, api_key):
        self.base = base.rstrip("/")
        self._key = api_key  # a string, or a function returning the current key (it can change in Settings)

    def client(self, timeout: float = 60) -> httpx.AsyncClient:
        key = self._key() if callable(self._key) else self._key
        return httpx.AsyncClient(base_url=self.base, timeout=timeout,
                                 headers={"X-Studio": "1", "Authorization": f"Bearer {key}"})

    async def call(self, method: str, path: str, timeout: float = 120, **kw):
        async with self.client(timeout) as c:
            r = await c.request(method, path, **kw)
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail")
            except ValueError:
                detail = r.text
            raise ValueError(detail if isinstance(detail, str) else json.dumps(detail))
        return r.json() if r.headers.get("content-type", "").startswith("application/json") else r.content

    async def settings(self) -> dict:
        return await self.call("GET", "/api/settings")

    async def batch(self, ref: str) -> dict:
        """A batch by id or (case-insensitive) name; 'latest' means the newest."""
        batches = await self.call("GET", "/api/batches")
        if not batches:
            raise ValueError("There are no batches yet.")
        if ref.lower() in ("latest", "last", "newest"):
            hit = batches[0]
        else:
            hit = next((b for b in batches if b["id"] == ref or b["name"].lower() == ref.lower()), None)
        if not hit:
            raise ValueError(f"No batch called {ref!r}. Use list_batches to see names.")
        return await self.call("GET", f"/api/batches/{hit['id']}")

    async def model(self, name: str | None, preset: str | None = None) -> str | None:
        """Resolve a model name to its key, refusing non-commercial ones unless allowed. Without a name, the model
        the preset or Settings would pick is checked the same way (None: keep that choice)."""
        state = await self.call("GET", "/api/state")
        models = [m for m in state["models"] if m["installed"] and m["kind"] == "voice"]
        if not name:
            p = next((p for p in await self.call("GET", "/api/presets") if preset and
                      preset.lower() in (p["id"], p["name"].lower())), None)
            key = (p and p["settings"].get("model")) or state["default_model"]
            hit = next((m for m in state["models"] if m["key"] == key), None)
            if hit and hit["noncommercial"] and not (await self.settings()).get("agents_noncommercial"):
                ok = [m["key"] for m in models if not m["noncommercial"]]
                raise ValueError(f"{hit['label']} is the {"preset's" if p else 'default'} voice model and has a "
                                 "non-commercial licence agents aren't allowed to use (Connect page). Pass model="
                                 f"{' or '.join(ok) or 'a commercial model'}.")
            return None
        n = name.lower()
        hit = next((m for m in models if n in (m["key"], m["label"].lower())), None) \
            or next((m for m in models if n in m["label"].lower() or n in m["key"]), None)
        if not hit:
            raise ValueError(f"No installed voice model matches {name!r}. Installed: {', '.join(m['key'] for m in models)}")
        if hit["noncommercial"] and not (await self.settings()).get("agents_noncommercial"):
            raise ValueError(f"{hit['label']} has a non-commercial licence and agents aren't allowed to use it "
                             "(Connect page). Pick another model.")
        return hit["key"]

    async def voice(self, name: str | None) -> str | None:
        if not name:
            return None
        voices = await self.call("GET", "/api/voices")
        n = name.lower()
        hit = next((v for v in voices if n in (v["id"], v["name"].lower())), None)
        if not hit:
            raise ValueError(f"No voice called {name!r}. Voices: {', '.join(v['name'] for v in voices) or 'none yet'}")
        return hit["id"]

    async def read_file(self, source: str) -> tuple[bytes, str]:
        """A file from an allowed folder (or an http(s) link): (bytes, file name)."""
        source = source.strip()
        if re.match(r"^https?://", source):
            async with httpx.AsyncClient(follow_redirects=True, timeout=120) as c:
                r = await c.get(source)
                r.raise_for_status()
            if len(r.content) > MAX_FILE_BYTES:
                raise ValueError(f"{source} is larger than 50 MB.")
            return r.content, source.rsplit("/", 1)[-1].split("?")[0] or "download"
        path = Path(source).expanduser()
        if not path.is_absolute():
            raise ValueError(f"{source!r} isn't an absolute path or a link.")
        s = await self.settings()
        allowed = [Path(d) for d in [*s.get("agent_read_dirs", []), s["batches_dir"], s["exports_dir"]]]
        real = path.resolve()
        if not any(real == a.resolve() or a.resolve() in real.parents for a in allowed):
            raise ValueError(f"{path} isn't in a folder agents may read. Allowed: {', '.join(map(str, allowed))} "
                             "(change them on the Connect page).")
        if not real.is_file():
            raise ValueError(f"No file at {path}.")
        if real.stat().st_size > MAX_FILE_BYTES:
            raise ValueError(f"{path} is larger than 50 MB.")
        return real.read_bytes(), real.name


def part_view(b: dict, it: dict) -> dict:
    out = {"part": it["id"], "status": it["status"], "text": it["text"], "seed": it["seed"],
           "seconds": it.get("audio_s"), "path": str(Path(b["folder"]) / it["file"]) if it["status"] == "done" else None}
    if it.get("check"):
        out["check"] = it["check"]
    if it.get("error"):
        out["error"] = it["error"]
    return out


def script_view(b: dict, s: dict, parts: bool) -> dict:
    out = {"script": s["n"], "title": s["title"], "status": s["status"], "voice": s.get("voice_name"),
           "language": s.get("language"), "parts": s["segments"], "parts_done": s["done"],
           "parts_to_check": s["checks"], "seconds": s["output"].get("seconds"),
           "whisper_heard": s["output"].get("match"),
           "files": {k: str(Path(b["folder"]) / f) for k, f in (s["output"].get("files") or {}).items()}}
    if s["output"].get("error"):
        out["error"] = s["output"]["error"]
    if parts:
        out["part_list"] = [part_view(b, it) for it in b["items"] if it["script"] == s["n"]]
    return out


def summary(b: dict, parts: bool = False) -> dict:
    out = {k: b.get(k) for k in ("id", "name", "status", "total", "done", "failed", "remaining", "checks",
                                 "eta_seconds", "elapsed_seconds", "audio_seconds", "folder")}
    s = b["settings"]
    out["settings"] = {k: s.get(k) for k in ("model", "voice", "language", "seed", "loudness", "formats", "subtitles")}
    if "scripts" in b:
        out["scripts"] = [script_view(b, sc, parts) for sc in b["scripts"]]
    return out


def build(base: str, api_key, *, host_port: int | None = None) -> FastMCP:
    studio = Studio(base, api_key)
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[f"127.0.0.1:{host_port}", f"localhost:{host_port}"] if host_port else ["127.0.0.1:*", "localhost:*"],
        allowed_origins=[f"http://127.0.0.1:{host_port}", f"http://localhost:{host_port}"] if host_port else [])
    mcp = FastMCP("Fatima Voice Studio", instructions=INSTRUCTIONS, stateless_http=True, json_response=True,
                  streamable_http_path="/mcp", transport_security=security)

    # ---- discovery ------------------------------------------------------------------

    @mcp.tool()
    async def list_voices() -> list[dict]:
        """Voices in the library: name, language, clip length, notes. Pass a name wherever a voice is asked for."""
        s = await studio.settings()
        return [{"name": v["name"], "language": v.get("language"), "seconds": v.get("seconds"),
                 "notes": v.get("notes"), "default": v["id"] == s.get("default_voice"), "found": v.get("source") == "found",
                 "tips": v.get("advice") or []} for v in await studio.call("GET", "/api/voices")]

    @mcp.tool()
    async def list_models() -> list[dict]:
        """Installed voice models with their licence and whether agents may use them."""
        state = await studio.call("GET", "/api/state")
        s = await studio.settings()
        return [{"model": m["key"], "name": m["label"], "default": m["key"] == state["default_model"],
                 "licence": m["license"], "languages": m.get("languages"),
                 "agents_may_use": not m["noncommercial"] or bool(s.get("agents_noncommercial"))}
                for m in state["models"] if m["installed"] and m["kind"] == "voice"]

    @mcp.tool()
    async def get_settings() -> dict:
        """Folders (batches, exports, folders agents may read), defaults and supported languages."""
        s = await studio.settings()
        state = await studio.call("GET", "/api/state")
        return {"batches_folder": s["batches_dir"], "exports_folder": s["exports_dir"],
                "agents_may_read": s["agent_read_dirs"], "default_voice": s.get("default_voice"),
                "default_language": s.get("default_language"), "loudness_lufs": s.get("loudness"),
                "formats": s.get("formats"), "subtitles": s.get("subtitles"), "languages": state["languages"],
                "subtitles_ready": state["subtitles_ready"]}

    @mcp.tool()
    async def add_voice(name: str, source: str, speaker_permission: bool, language: str | None = None,
                        notes: str = "", reduce_noise: bool = False) -> dict:
        """Add a voice to the library from an audio clip (WAV/MP3/FLAC/OGG, 6-15 s of one person speaking):
        an absolute path inside an allowed folder, or an http(s) link. speaker_permission must be true: only
        add voices of people who agreed to it (or the user's own voice)."""
        if not speaker_permission:
            raise ValueError("Only add a voice with the speaker's permission (set speaker_permission=true once you know you have it).")
        data, filename = await studio.read_file(source)
        form = {"name": name, "language": language or "", "notes": notes, "denoise": "1" if reduce_noise else "0"}
        async with studio.client(180) as c:
            r = await c.post("/api/voices", data=form, files={"file": (filename, data)})
        if r.status_code >= 400:
            raise ValueError(r.json().get("detail"))
        v = r.json()
        return {"name": v["name"], "seconds": v["seconds"], "language": v["language"], "tips": v.get("advice") or []}

    # ---- making speech ----------------------------------------------------------------

    def batch_settings(voice, language, model, seed, loudness, formats, subtitles, speed=None, preset=None) -> dict:
        s = {}
        for k, v in (("voice", voice), ("language", language), ("model", model), ("seed", seed),
                     ("loudness", loudness), ("formats", formats), ("subtitles", subtitles), ("speed", speed),
                     ("preset", preset)):
            if v is not None:
                s[k] = v
        return s

    @mcp.tool()
    async def list_presets() -> list[dict]:
        """Channel presets (voice, language, speed, loudness, pauses, files saved under a name). Pass preset=<name>
        to speak or create_batch to use one."""
        return [{"name": p["name"], "settings": p["settings"]} for p in await studio.call("GET", "/api/presets")]

    @mcp.tool()
    async def list_pronunciations(language: str | None = None) -> list[dict]:
        """The pronunciation dictionary: how names and abbreviations are said (applied to every script)."""
        return [{"written": e["from"], "said_as": e["to"], "language": e["language"] or "all", "exact_capitals": e["case"]}
                for e in await studio.call("GET", "/api/dictionary") if not language or e["language"] in ("", language)]

    @mcp.tool()
    async def add_pronunciation(written: str, said_as: str, language: str = "", exact_capitals: bool = False) -> dict:
        """Teach the voice how to say a name or abbreviation, spelled the way it sounds in that language
        (e.g. written "CJNG", said_as "ce jota ene ge", language "es"). Applies to new and regenerated parts."""
        e = await studio.call("POST", "/api/dictionary", json={"written": written, "said": said_as, "language": language,
                                                               "case": exact_capitals})
        return {"added": e["from"], "said_as": e["to"], "language": e["language"] or "all"}

    @mcp.tool()
    async def preview_reading(text: str, language: str | None = None) -> dict:
        """What the voice will actually read for some text (pronunciation dictionary + numbers as words), without speaking."""
        return await studio.call("POST", "/api/speakable", json={"text": text, "language": language})

    @mcp.tool()
    async def speak(text: str, voice: str | None = None, language: str | None = None, seed: int | None = None,
                    speed: float | None = None, preset: str | None = None, wait: bool = True) -> dict:
        """Speak one piece of text now (ahead of queued batches), saved in today's Singles batch. speed 0.8-1.25
        (same pitch). preset = a channel preset's name. Returns the file paths (WAV/MP3/SRT) when wait=true
        (up to 15 minutes), else the batch to wait on."""
        voice_id = await studio.voice(voice) if voice else None
        r = await studio.call("POST", "/api/singles", json={"text": text, "settings": batch_settings(
            voice_id, language, await studio.model(None, preset), seed, None, None, None, speed, preset)})
        bid, n = r["batch"]["id"], r["script"]["n"]
        if not wait:
            return {"batch": r["batch"]["name"], "script": n, "status": "queued", "note": "Use wait_for_batch."}
        deadline = asyncio.get_running_loop().time() + 900
        while True:
            b = await studio.call("GET", f"/api/batches/{bid}")
            s = next(x for x in b["scripts"] if x["n"] == n)
            if s["status"] not in BUSY or asyncio.get_running_loop().time() > deadline:
                return {"batch": b["name"]} | script_view(b, s, parts=s["status"] != "done")
            await asyncio.sleep(2)

    @mcp.tool()
    async def create_batch(scripts: list, name: str | None = None, voice: str | None = None,
                           language: str | None = None, model: str | None = None, seed: int | None = None,
                           loudness: float | None = None, formats: list[str] | None = None,
                           subtitles: bool | None = None, speed: float | None = None, preset: str | None = None) -> dict:
        """Queue a batch: each script becomes its own WAV/MP3 (+ SRT). scripts: a list of texts, or of
        {"text" | "file", "title", "voice", "language"} where "file" is a .txt/.md path in an allowed folder.
        voice/language apply to scripts without their own. preset = a channel preset's name (its settings fill
        in anything not given here). loudness in LUFS (-16 default; -14 louder). speed 0.8-1.25 (same pitch).
        formats: ["wav", "mp3"]. Returns the batch id and name; use wait_for_batch next."""
        out = []
        for s in scripts:
            s = {"text": s} if isinstance(s, str) else dict(s)
            if s.get("file") and not s.get("text"):
                data, fname = await studio.read_file(s.pop("file"))
                s["text"] = data.decode("utf-8-sig", errors="replace")
                s.setdefault("title", Path(fname).stem.replace("_", " "))
            if s.get("voice"):
                s["voice"] = await studio.voice(s["voice"])
            out.append({k: s[k] for k in ("text", "title", "voice", "language") if s.get(k)})
        settings = batch_settings(await studio.voice(voice) if voice else None, language, await studio.model(model, preset),
                                  seed, loudness, formats, subtitles, speed, preset)
        b = await studio.call("POST", "/api/batches", json={"name": name, "scripts": out, "settings": settings})
        return {"id": b["id"], "name": b["name"], "scripts": b["scripts_total"], "parts": b["total"], "folder": b["folder"],
                "note": "Use wait_for_batch to wait for it."}

    @mcp.tool()
    async def list_batches(limit: int = 20) -> list[dict]:
        """Recent batches, newest first, with status and progress."""
        return [summary(b) for b in (await studio.call("GET", "/api/batches"))[:max(1, min(limit, 200))]]

    @mcp.tool()
    async def get_batch(batch: str, include_parts: bool = False) -> dict:
        """A batch's scripts, file paths and status (batch = id, name or 'latest'). include_parts lists every
        part with its text, seed, path and any 'check' note."""
        return summary(await studio.batch(batch), parts=include_parts)

    @mcp.tool()
    async def wait_for_batch(batch: str, timeout_seconds: int = 900) -> dict:
        """Wait until a batch has finished (spoken, joined and subtitled) or the timeout passes (max 1800 s).
        Parts listed with a 'check' note may be worth regenerating. If it's still running, call again."""
        deadline = asyncio.get_running_loop().time() + min(max(timeout_seconds, 5), 1800)
        while True:
            b = await studio.batch(batch)
            if b["status"] not in BUSY or asyncio.get_running_loop().time() > deadline:
                out = summary(b, parts=False)
                out["finished"] = b["status"] not in BUSY
                out["parts_to_check"] = [part_view(b, it) for it in b["items"] if it.get("check") or it.get("error")]
                return out
            await asyncio.sleep(3)

    # ---- fixing ----------------------------------------------------------------------

    @mcp.tool()
    async def regenerate_part(batch: str, part: str, new_seed: bool = True) -> dict:
        """Speak one part again (part ids look like '2.5' = script 2, part 5); the script's files are rebuilt after."""
        b = await studio.batch(batch)
        await studio.call("POST", f"/api/batches/{b['id']}/segments/{part}/regenerate", json={"new_seed": new_seed})
        return {"queued": part, "note": "Use wait_for_batch."}

    @mcp.tool()
    async def edit_part(batch: str, part: str, text: str) -> dict:
        """Change one part's text (fix a word, spell a name as it sounds) and speak it again."""
        b = await studio.batch(batch)
        await studio.call("PATCH", f"/api/batches/{b['id']}/segments/{part}", json={"text": text})
        return {"queued": part, "note": "Use wait_for_batch."}

    @mcp.tool()
    async def edit_script(batch: str, script: int, text: str | None = None, title: str | None = None,
                          voice: str | None = None, language: str | None = None) -> dict:
        """Change a script's text, title, voice or language. Parts whose text didn't change keep their audio."""
        b = await studio.batch(batch)
        body = {k: v for k, v in (("text", text), ("title", title), ("language", language)) if v is not None}
        if voice:
            body["voice"] = await studio.voice(voice)
        r = await studio.call("PATCH", f"/api/batches/{b['id']}/scripts/{script}", json=body)
        return summary(r)

    @mcp.tool()
    async def retry_failed(batch: str) -> dict:
        """Queue every failed or cancelled part of a batch again."""
        b = await studio.batch(batch)
        return summary(await studio.call("POST", f"/api/batches/{b['id']}/retry"))

    @mcp.tool()
    async def control_batch(batch: str, action: str) -> dict:
        """pause, resume or cancel a batch."""
        if action not in ("pause", "resume", "cancel"):
            raise ValueError("action must be pause, resume or cancel")
        b = await studio.batch(batch)
        return summary(await studio.call("POST", f"/api/batches/{b['id']}/{action}"))

    @mcp.tool()
    async def rename_batch(batch: str, new_name: str) -> dict:
        """Rename a batch (its folder is renamed too)."""
        b = await studio.batch(batch)
        return summary(await studio.call("PATCH", f"/api/batches/{b['id']}", json={"name": new_name}))

    @mcp.tool()
    async def move_in_queue(batch: str, position: str = "first") -> dict:
        """Move a queued batch to the 'first' or 'last' place in the queue."""
        b = await studio.batch(batch)
        state = await studio.call("GET", "/api/state")
        order = [i for i in state["queue"] if i != b["id"]]
        order = [b["id"], *order] if position == "first" else [*order, b["id"]]
        await studio.call("POST", "/api/queue/order", json={"ids": order})
        return {"queue": order}

    @mcp.tool()
    async def export_batch(batch: str, format: str = "folder", content: str = "final") -> dict:
        """Copy a batch's finished files into the Exports folder: format 'folder' or 'zip'; content 'final'
        (WAV/MP3/SRT per script), 'segments' (every part) or 'both'."""
        b = await studio.batch(batch)
        return await studio.call("POST", f"/api/exports/{b['id']}", json={"format": format, "content": content})

    @mcp.tool()
    async def transcribe(source: str, language: str | None = None, translate_to_english: bool = False,
                         timeout_seconds: int = 1800) -> dict:
        """Transcribe an audio or video file (absolute path in an allowed folder, or a link) with Whisper.
        Returns the text and the paths of the TXT / SRT / VTT files (kept on the Transcribe page)."""
        data, filename = await studio.read_file(source) if re.match(r"^https?://", source) else (None, None)
        if data is None:
            path = Path(source).expanduser().resolve()
            s = await studio.settings()
            allowed = [Path(d) for d in [*s.get("agent_read_dirs", []), s["batches_dir"], s["exports_dir"]]]
            if not any(path == a.resolve() or a.resolve() in path.parents for a in allowed):
                raise ValueError(f"{path} isn't in a folder agents may read (Connect page).")
            if not path.is_file():
                raise ValueError(f"No file at {path}.")
            data, filename = path.read_bytes(), path.name  # videos can be large: no 50 MB limit here
        form = {"translate": "1" if translate_to_english else "0", **({"language": language} if language else {})}
        async with studio.client(300) as c:
            r = await c.post("/api/transcripts", data=form, files={"file": (filename, data)})
        if r.status_code >= 400:
            raise ValueError(r.json().get("detail"))
        tid = r.json()["id"]
        deadline = asyncio.get_running_loop().time() + min(max(timeout_seconds, 10), 3600)
        while True:
            t = next((x for x in await studio.call("GET", "/api/transcripts") if x["id"] == tid), None)
            if not t:
                raise ValueError("The transcript was deleted.")
            if t["status"] in ("done", "failed") or asyncio.get_running_loop().time() > deadline:
                break
            await asyncio.sleep(3)
        if t["status"] != "done":
            return {"status": t["status"], "progress": t["progress"], "error": t.get("error"),
                    "note": "Still running: check the Transcribe page, or call transcribe again later."}
        text = (await studio.call("GET", f"/api/transcripts/{tid}/txt")).decode("utf-8")
        folder = Path((await studio.settings())["data_dir"]) / "transcripts" / tid
        return {"text": text, "language": t.get("detected_language"), "seconds": t.get("seconds"),
                "files": {k: str(folder / f) for k, f in t["files"].items()}}

    return mcp
