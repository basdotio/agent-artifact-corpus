"""HTTP layer: the studio UI's /api routes and the OpenAI-compatible /v1 routes."""
import asyncio
import contextlib
import json
import logging
import mimetypes
import os
import random
import shutil
import time
import uuid
import zipfile
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask

from . import APP_NAME, REPO_URL, __version__, audio, autostart, config, hardware, s2engine, subtitles, text as textmod
from .downloads import Downloads
from . import media
from .engine import Engine, EngineError
from .presets import Presets
from .transcribe import Transcripts
from .speech_text import Dictionary, parse_import, speakable
from .store import SCRIPT_OVERRIDES, Store, batch_status, items_of, script_status, settings_for
from .updater import Updater
from .voices import Voices
from .winui import pick_folder
from .worker import Worker

log = logging.getLogger("studio")
WEB = Path(__file__).parent / "web"
HELP = Path(__file__).parent / "help"  # the guides: Markdown, shown on the Help page and readable on GitHub
mimetypes.add_type("image/webp", ".webp")  # the guides' screenshots; older Windows registries don't know it
mimetypes.add_type("text/markdown; charset=utf-8", ".md")
EXPORTS = config.DATA / "exports"
FOUND = config.DATA / "found"        # "Find a voice" samples waiting to be kept
PREVIEWS = config.DATA / "previews"  # voice preview samples
MAX_SCRIPTS = 500
MAX_TEXT = 200_000  # characters per script (about 4 hours of speech)
PREVIEW_TEXT = {
    "en": "Hello! This is how I sound. I can read your scripts, long or short, in a steady, natural voice.",
    "es": "¡Hola! Así es como sueno. Puedo leer tus guiones, largos o cortos, con una voz natural y constante.",
    "fr": "Bonjour ! Voici ma voix. Je peux lire vos textes, longs ou courts, d'une voix naturelle et posée.",
    "de": "Hallo! So klinge ich. Ich kann deine Texte vorlesen, lang oder kurz, mit ruhiger, natürlicher Stimme.",
    "it": "Ciao! Ecco come suono. Posso leggere i tuoi testi, lunghi o brevi, con una voce naturale e calma.",
    "pt": "Olá! É assim que eu soo. Posso ler os seus roteiros, longos ou curtos, com uma voz natural e calma.",
    "ru": "Привет! Вот так звучит мой голос. Я могу читать ваши тексты, длинные и короткие, спокойно и естественно.",
    "ja": "こんにちは。これが私の声です。長い原稿も短い原稿も、自然な声で読み上げます。",
    "ko": "안녕하세요! 이것이 제 목소리입니다. 길거나 짧은 원고를 자연스러운 목소리로 읽어 드립니다.",
    "zh": "你好！这就是我的声音。无论长短，我都能用自然的声音朗读你的稿子。",
    # S2 Pro's languages. Where the verb would say whether the voice is a man or a woman (Hindi, Urdu, Hebrew, Thai),
    # the sentence is put so it doesn't. Languages without one ask for a sentence (Find a new voice).
    "hi": "नमस्ते! यह मेरी आवाज़ है। आपकी स्क्रिप्ट, छोटी हो या लंबी, शांत और स्वाभाविक आवाज़ में पढ़ी जाएगी।",
    "ur": "السلام علیکم! یہ میری آواز ہے۔ آپ کا اسکرپٹ، چھوٹا ہو یا لمبا، پرسکون اور قدرتی آواز میں پڑھا جائے گا۔",
    "ar": "مرحبًا! هذا هو صوتي. أستطيع قراءة نصوصك، طويلة كانت أم قصيرة، بصوت هادئ وطبيعي.",
    "fa": "سلام! صدای من این‌طور است. می‌توانم متن‌های شما را، کوتاه یا بلند، با صدایی آرام و طبیعی بخوانم.",
    "bn": "নমস্কার! আমার কণ্ঠ এমন শোনায়। আপনার স্ক্রিপ্ট, ছোট হোক বা বড়, আমি শান্ত ও স্বাভাবিক কণ্ঠে পড়তে পারি।",
    "ne": "नमस्ते! मेरो आवाज यस्तो छ। तपाईंको स्क्रिप्ट, छोटो होस् वा लामो, म शान्त र स्वाभाविक आवाजमा पढ्न सक्छु।",
    "ta": "வணக்கம்! இதுதான் என் குரல். உங்கள் உரைகளை, நீளமாக இருந்தாலும் சுருக்கமாக இருந்தாலும், அமைதியான இயல்பான குரலில் படிக்க முடியும்.",
    "tr": "Merhaba! Sesim böyle. Metinlerinizi, uzun ya da kısa, sakin ve doğal bir sesle okuyabilirim.",
    "id": "Halo! Beginilah suara saya. Saya bisa membacakan naskah Anda, panjang atau pendek, dengan suara yang tenang dan alami.",
    "ms": "Helo! Beginilah suara saya. Saya boleh membaca skrip anda, panjang atau pendek, dengan suara yang tenang dan semula jadi.",
    "vi": "Xin chào! Đây là giọng của tôi. Tôi có thể đọc kịch bản của bạn, dài hay ngắn, bằng một giọng đọc tự nhiên và điềm tĩnh.",
    "th": "สวัสดี! นี่คือเสียงที่จะอ่านบทของคุณ ไม่ว่าจะยาวหรือสั้น ด้วยน้ำเสียงที่สงบและเป็นธรรมชาติ",
    "tl": "Kumusta! Ganito ang boses ko. Kaya kong basahin ang iyong mga script, mahaba man o maikli, sa kalmado at natural na boses.",
    "sw": "Habari! Hivi ndivyo sauti yangu ilivyo. Ninaweza kusoma maandishi yako, marefu au mafupi, kwa sauti tulivu na ya asili.",
    "he": "שלום! כך נשמע הקול שלי. הטקסטים שלכם, ארוכים או קצרים, ייקראו בקול רגוע וטבעי.",
    "pl": "Cześć! Tak brzmi mój głos. Mogę czytać twoje teksty, długie i krótkie, spokojnym, naturalnym głosem.",
    "nl": "Hallo! Zo klinkt mijn stem. Ik kan je teksten voorlezen, lang of kort, met een rustige, natuurlijke stem.",
    "sv": "Hej! Så här låter jag. Jag kan läsa dina manus, långa som korta, med en lugn och naturlig röst.",
    "da": "Hej! Sådan lyder jeg. Jeg kan læse dine manuskripter, lange eller korte, med en rolig og naturlig stemme.",
    "no": "Hei! Slik høres jeg ut. Jeg kan lese manusene dine, lange eller korte, med en rolig og naturlig stemme.",
    "fi": "Hei! Tältä minä kuulostan. Voin lukea käsikirjoituksesi, pitkät tai lyhyet, rauhallisella ja luontevalla äänellä.",
    "cs": "Ahoj! Takhle zním. Můžu číst tvoje texty, dlouhé i krátké, klidným a přirozeným hlasem.",
    "sk": "Ahoj! Takto znie môj hlas. Môžem čítať tvoje texty, dlhé aj krátke, pokojným a prirodzeným hlasom.",
    "el": "Γεια σας! Έτσι ακούγεται η φωνή μου. Μπορώ να διαβάσω τα κείμενά σας, μεγάλα ή μικρά, με ήρεμη και φυσική φωνή.",
    "uk": "Привіт! Ось так звучить мій голос. Я можу читати ваші тексти, довгі й короткі, спокійно та природно.",
    "bg": "Здравейте! Ето как звучи гласът ми. Мога да чета вашите текстове, дълги или кратки, със спокоен и естествен глас.",
    "ro": "Bună! Așa sună vocea mea. Pot citi textele tale, lungi sau scurte, cu o voce calmă și naturală.",
    "hu": "Szia! Így szól a hangom. Felolvasom a szövegeidet, legyenek hosszúak vagy rövidek, nyugodt, természetes hangon.",
    "hr": "Bok! Ovako zvuči moj glas. Mogu čitati tvoje tekstove, duge ili kratke, mirnim i prirodnim glasom.",
    "sr": "Здраво! Овако звучи мој глас. Могу да читам ваше текстове, дуге или кратке, мирним и природним гласом.",
    "ca": "Hola! Així sona la meva veu. Puc llegir els teus textos, llargs o curts, amb una veu tranquil·la i natural.",
    "af": "Hallo! So klink ek. Ek kan jou tekste lees, lank of kort, met 'n rustige, natuurlike stem.",
}
AUDIO_TYPES = {"mp3": "audio/mpeg", "wav": "audio/wav", "pcm": "audio/L16", "flac": "audio/flac"}


def elapsed_seconds(items: list[dict], running: bool) -> float | None:
    import datetime as dt
    starts = [it["started"] for it in items if it.get("started")]
    ends = [it["finished"] for it in items if it.get("finished")]
    if not starts:
        return None
    first = dt.datetime.fromisoformat(min(starts))
    last = dt.datetime.now() if running or not ends else dt.datetime.fromisoformat(max(ends))
    return max(0.0, (last - first).total_seconds())


def create_app(cfg: dict) -> FastAPI:
    store = Store(cfg["batches_dir"])
    engine = Engine(cfg)
    voices = Voices()
    dictionary = Dictionary()
    presets = Presets()
    worker = Worker(store, engine, voices, cfg, dictionary)
    downloads = Downloads(cfg)
    transcripts = Transcripts(cfg)
    updater = Updater(cfg)
    try:
        from .mcp_server import build as build_mcp
        mcp = build_mcp(f"http://127.0.0.1:{cfg['port']}", lambda: cfg["api_key"], host_port=cfg["port"])
    except ImportError:
        mcp = None

    @contextlib.asynccontextmanager
    async def lifespan(app):
        shutil.rmtree(config.DATA / "tmp", ignore_errors=True)  # leftovers of a crash
        tasks = [asyncio.create_task(worker.run()), asyncio.create_task(updater.watch()),
                 asyncio.create_task(transcripts.run())]
        log.info("%s on http://%s:%s  (batches: %s)", APP_NAME, cfg["host"], cfg["port"], store.root)
        subtitles.GPU_TURN = engine.s2.gpu_turn  # Whisper and S2 Pro take turns on small graphics cards
        downloads.ensure_whisper_gpu()  # e.g. after an update: Whisper's graphics card build, if it's missing
        downloads.ensure_s2_runtime()   # and s2.cpp, if an S2 Pro model is there without it
        if mcp:
            async with mcp.session_manager.run():  # MCP endpoint for AI agents at /mcp
                yield
        else:
            yield
        for t in tasks:
            t.cancel()
        engine.cancel_current()
        engine.s2.stop()

    app = FastAPI(title=APP_NAME, version=__version__, lifespan=lifespan,
                  description="OpenAI-compatible text-to-speech and transcription on this PC, plus batches of scripts. "
                              "Authenticate /v1 calls with `Authorization: Bearer <api key>`.")
    # Browser apps may call /v1 with the API key. The UI-only header below is deliberately
    # not allowed cross-origin, which keeps other websites from driving /api.
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                       allow_headers=["Authorization", "Content-Type"])

    @app.middleware("http")
    async def ui_only(request: Request, call_next):
        if request.url.path.startswith("/mcp") and request.headers.get("authorization") != f"Bearer {cfg['api_key']}":
            return JSONResponse({"detail": "Invalid or missing API key (Authorization: Bearer <key>)"}, status_code=401)
        if (request.url.path.startswith("/api/") and request.method not in ("GET", "HEAD")
                and request.headers.get("x-studio") != "1"):
            return JSONResponse({"detail": "Missing X-Studio header"}, status_code=403)
        response = await call_next(request)
        if request.url.path == "/" or request.url.path.endswith((".html", ".js", ".css", ".md")):
            response.headers["Cache-Control"] = "no-cache"  # revalidate, so an updated app never runs stale scripts
        return response

    # ---- helpers ------------------------------------------------------------------

    def get_batch(batch_id: str) -> dict:
        b = store.batches.get(batch_id)
        if not b:
            b = next((x for x in store.batches.values() if x["name"].lower() == batch_id.lower()), None)
        if not b:
            raise HTTPException(404, "No such batch")
        return b

    def get_script(b: dict, n: int) -> dict:
        s = next((s for s in b["scripts"] if s["n"] == n), None)
        if not s:
            raise HTTPException(404, "No such script")
        return s

    def get_item(b: dict, item_id: str) -> dict:
        it = next((it for it in b["items"] if it["id"] == item_id), None)
        if not it:
            raise HTTPException(404, "No such segment")
        return it

    def script_summary(b: dict, s: dict) -> dict:
        items = items_of(b, s)
        st = settings_for(b, s)
        v = voices.get(st.get("voice") or "")
        return {"n": s["n"], "title": s["title"], "stem": s["stem"], "status": script_status(b, s),
                "voice": st.get("voice"), "voice_name": v["name"] if v else None, "language": st.get("language"),
                "model": st.get("model"), "out": {k: st.get(k) for k in ("speed", "loudness", "formats", "subtitles")}, "own": {k: s[k] for k in SCRIPT_OVERRIDES if s.get(k) not in (None, "")},
                "segments": len(items), "done": sum(it["status"] == "done" for it in items),
                "failed": sum(it["status"] == "failed" for it in items),
                "checks": sum(1 for it in items if it.get("check")),
                "chars": len(s["text"]), "estimate_s": round(textmod.estimate_seconds(s["text"])),
                "output": {k: v for k, v in s["output"].items() if k != "spans"}}

    def summarize(b: dict, full: bool = False) -> dict:
        items = b["items"]
        done = [it for it in items if it["status"] == "done" and it.get("duration")]
        remaining = [it for it in items if it["status"] in ("queued", "running")]
        # Seconds of work per character of text, from what's been spoken so far in this batch.
        rate = (sum(it["duration"] for it in done) / max(1, sum(len(it["text"]) for it in done))) if done else None
        eta = round(rate * sum(len(it["text"]) for it in remaining)) if rate and remaining else None
        status = batch_status(b)
        out = {
            "id": b["id"], "name": b["name"], "created": b["created"], "status": status, "kind": b.get("kind") or "batch",
            "elapsed_seconds": elapsed_seconds(items, running=status == "running"),
            "paused": b["paused"], "settings": b["settings"], "total": len(items),
            "done": sum(it["status"] == "done" for it in items), "failed": sum(it["status"] == "failed" for it in items),
            "cancelled": sum(it["status"] == "cancelled" for it in items), "remaining": len(remaining),
            "eta_seconds": eta, "checks": sum(1 for it in items if it.get("check")),
            "scripts_total": len(b["scripts"]),
            "scripts_done": sum(script_status(b, s) == "done" for s in b["scripts"]),
            "audio_seconds": round(sum(s["output"].get("seconds") or 0 for s in b["scripts"]), 1),
            "first_text": b["scripts"][0]["text"][:200] if b["scripts"] else "",
            "folder": str(store.folder(b)),
        }
        if full:
            out["scripts"] = [script_summary(b, s) | {"text": s["text"]} for s in b["scripts"]]
            out["items"] = items
        return out

    def batches_active() -> bool:
        return bool(worker.current) or any(batch_status(b) in ("running", "queued", "finishing") for b in store.batches.values())

    def check_voice(ref: str | None, required: bool = False) -> str | None:
        if not ref:
            if required:
                raise HTTPException(400, "Pick a voice (add one on the Voices page first).")
            return None
        v = voices.get(ref)
        if not v:
            raise HTTPException(400, f"No voice called “{ref}” in the voice library.")
        return v["id"]

    def check_language(code: str | None) -> str:
        code = (code or cfg["default_language"]).lower()
        if code not in config.LANGUAGE_NAMES:
            raise HTTPException(400, f"Unsupported language “{code}”. Use a language code from GET /api/state.")
        return code

    def check_speaks(model: str, lang: str) -> None:
        """A model that doesn't speak this language is refused up front, in plain words."""
        m = config.MODELS[model]
        if lang not in (m.get("languages") or config.LANGUAGES):
            other = next((x["label"] for k, x in config.MODELS.items()
                          if x["kind"] == "voice" and lang in (x.get("languages") or [])), None)
            raise HTTPException(400, f"{m['label']} doesn't speak {config.LANGUAGE_NAMES.get(lang, lang)}."
                                     + (f" Use {other} for it." if other else ""))

    def check_model(key: str | None) -> str:
        key = key or cfg["default_model"]
        if key not in config.MODELS:  # also accept API ids
            key = next((k for k, m in config.MODELS.items() if m["api_id"] == key), key)
        if key not in config.MODELS or config.MODELS[key]["kind"] != "voice":
            raise HTTPException(400, f"Unknown voice model “{key}”.")
        if problem := engine.ready_problem(key):
            raise HTTPException(400, problem)
        return key

    def model_for(lang: str) -> str:
        """The voice model to speak a sample in this language: the default one if it speaks it, else a downloaded one
        that does (S2 Pro for Hindi or Urdu, say)."""
        installed = config.installed_models(cfg)
        speaks = lambda k: lang in (config.MODELS[k].get("languages") or config.LANGUAGES)
        if speaks(cfg["default_model"]):
            return check_model(None)
        key = next((k for k, m in config.MODELS.items() if m["kind"] == "voice" and k in installed and speaks(k)), None)
        if not key:
            check_speaks(cfg["default_model"], lang)  # says which model to download for it
        return check_model(key)

    def batch_settings(raw: dict) -> dict:
        """Settings for a new batch: the request's, then its preset's (if it names one), then Settings."""
        if raw.get("preset"):
            p = presets.get(str(raw["preset"]))
            if not p:
                raise HTTPException(400, f"No preset called “{raw['preset']}”.")
            raw = p["settings"] | {k: v for k, v in raw.items() if k != "preset" and v not in (None, "")}
        s = {k: raw.get(k, cfg[k]) for k in ("loudness", "formats", "mp3_bitrate", "subtitles", "max_chars",
                                              "pause_segment", "pause_paragraph", "speed", "spell_numbers")}
        s["speed"] = round(max(config.SPEED_RANGE[0], min(config.SPEED_RANGE[1], float(s["speed"] or 1.0))), 3)
        s["spell_numbers"] = bool(s["spell_numbers"])
        s["model"] = check_model(raw.get("model"))
        s["voice"] = check_voice(raw.get("voice") if "voice" in raw else cfg["default_voice"])
        s["language"] = check_language(raw.get("language") or (voices.get(s["voice"]) or {}).get("language"))
        check_speaks(s["model"], s["language"])
        s["seed"] = raw.get("seed")
        s["formats"] = [f for f in (s["formats"] or []) if f in ("wav", "mp3")] or ["wav", "mp3"]
        s["max_chars"] = max(150, min(1200, int(s["max_chars"])))
        s["loudness"] = max(-30.0, min(-9.0, float(s["loudness"])))
        s["pause_segment"] = max(0.0, min(5.0, float(s["pause_segment"])))
        s["pause_paragraph"] = max(0.0, min(10.0, float(s["pause_paragraph"])))
        s["subtitles"] = bool(s["subtitles"])
        return s

    # ---- state ------------------------------------------------------------------

    @app.get("/api/state")
    def state():
        installed = config.installed_models(cfg)
        cur, fin = worker.current, worker.finishing
        return {
            "engine": engine.status(),
            "models": [{"key": k, "label": m["label"], "short": m["short"], "kind": m["kind"], "installed": k in installed,
                        "license": m["license"], "noncommercial": bool(m.get("noncommercial")), "languages": m.get("languages"),
                        "runtime": m.get("runtime", "llama"), "tags": bool(m.get("tags"))}
                       for k, m in config.MODELS.items()],
            "languages": config.LANGUAGE_NAMES,
            "sample_languages": list(PREVIEW_TEXT),  # a ready sentence for voice samples (else one is typed)
            "default_model": cfg["default_model"], "default_language": cfg["default_language"],
            "default_voice": cfg["default_voice"],
            "subtitles_ready": subtitles.whisper_available(cfg),
            "setup_ready": cfg["engine"] in config.installed_engines(cfg) and cfg["default_model"] in installed,
            "update": {"status": updater.state["status"], "latest": updater.state["latest"]},
            "api_base": f"http://{cfg['host']}:{cfg['port']}/v1",
            "current": {"batch": cur[0]["id"], "item": cur[1]["id"], "text": cur[1]["text"][:120]} if cur else None,
            "finishing": {"batch": fin[0]["id"], "script": fin[1]["n"], "progress": worker.finish_progress,
                          "gpu": next(iter(subtitles.whisper_builds(cfg)), {}).get("gpu", False)} if fin else None,
            "api_busy": worker.api_busy,
            "queue": [b["id"] for b in sorted(store.batches.values(), key=lambda b: b["order"])
                      if batch_status(b) in ("running", "queued", "paused", "finishing")],
            "voices": len(voices.list()),
            "version": __version__,
        }

    # ---- batches ----------------------------------------------------------------

    @app.get("/api/batches")
    def list_batches():
        return [summarize(b) for b in sorted(store.batches.values(), key=lambda b: b["created"], reverse=True)]

    @app.get("/api/batches/{batch_id}")
    def batch_detail(batch_id: str):
        return summarize(get_batch(batch_id), full=True)

    class ScriptIn(BaseModel):
        text: str = Field(min_length=1, max_length=MAX_TEXT)
        title: str | None = None
        voice: str | None = None
        language: str | None = None
        seed: int | None = Field(None, ge=0, lt=2**31)

    class BatchIn(BaseModel):
        name: str | None = None
        scripts: list[ScriptIn] = Field(min_length=1, max_length=MAX_SCRIPTS)
        settings: dict = {}

    def create_batch(body: BatchIn) -> dict:
        settings = batch_settings(body.settings)
        scripts = []
        for s in body.scripts:
            d = s.model_dump()
            d["voice"] = check_voice(d.get("voice")) if d.get("voice") else None
            d["language"] = check_language(d["language"]) if d.get("language") else None
            if d["language"]:
                check_speaks(settings["model"], d["language"])
            if not (d["voice"] or settings["voice"]):
                raise HTTPException(400, "Pick a voice for the batch (or for every script).")
            scripts.append(d)
        try:
            b = store.create(name=body.name, scripts=scripts, settings=settings)
        except ValueError as e:
            raise HTTPException(400, str(e))
        worker.notify()
        return b

    @app.post("/api/batches")
    def new_batch(body: BatchIn):
        return summarize(create_batch(body))

    class SingleIn(BaseModel):
        text: str = Field(min_length=1, max_length=MAX_TEXT)
        settings: dict = {}

    @app.post("/api/singles")
    def new_single(body: SingleIn):
        s = batch_settings(body.settings)
        if not s["voice"]:
            raise HTTPException(400, "Pick a voice (add one on the Voices page first).")
        try:
            b, script = store.add_single(text=body.text, settings=s)
        except ValueError as e:
            raise HTTPException(400, str(e))
        worker.notify()
        return {"batch": summarize(b), "script": script_summary(b, script)}

    class Rename(BaseModel):
        name: str = Field(min_length=1, max_length=120)

    @app.patch("/api/batches/{batch_id}")
    def rename_batch(batch_id: str, body: Rename):
        b = get_batch(batch_id)
        if worker.is_busy_with(b) or (worker.finishing and worker.finishing[0] is b):
            raise HTTPException(409, "This batch is working right now. Pause it (and let the current part finish), then rename it.")
        try:
            store.rename(b, body.name)
        except ValueError as e:
            raise HTTPException(409, str(e))
        return summarize(b)

    @app.post("/api/batches/{batch_id}/{action}")
    def batch_action(batch_id: str, action: str):
        b = get_batch(batch_id)
        if action == "pause":
            b["paused"] = True
        elif action == "resume":
            b["paused"] = False
            worker.notify()
        elif action == "cancel":
            worker.cancel(b)
        elif action == "retry":
            worker.retry(b)
        elif action == "rerun":
            nb = store.rerun(b)
            worker.notify()
            return summarize(nb)
        elif action == "open":
            os.startfile(store.folder(b))
        else:
            raise HTTPException(404, "Unknown action")
        store.save(b)
        return summarize(b)

    def remove_batch(b: dict) -> None:
        if worker.is_busy_with(b) or batch_status(b) in ("running", "queued", "finishing"):
            raise ValueError("still working — cancel it first")
        store.delete(b)  # to the Recycle Bin

    @app.delete("/api/batches/{batch_id}")
    def delete_batch(batch_id: str):
        b = get_batch(batch_id)
        try:
            remove_batch(b)
        except ValueError:
            raise HTTPException(409, "This batch is still working. Cancel it first, then delete it.")
        except OSError as e:
            raise HTTPException(409, str(e))
        return {"deleted": b["name"]}

    class BulkDelete(BaseModel):
        ids: list[str] = Field(min_length=1, max_length=1000)

    @app.post("/api/batches-delete")
    def delete_batches(body: BulkDelete):
        deleted, skipped = [], []
        for batch_id in dict.fromkeys(body.ids):
            b = store.batches.get(batch_id)
            if not b:
                continue
            try:
                remove_batch(b)
                deleted.append(b["name"])
            except (ValueError, OSError) as e:
                skipped.append({"name": b["name"], "reason": str(e)})
        return {"deleted": deleted, "skipped": skipped}

    class QueueOrder(BaseModel):
        ids: list[str]

    @app.post("/api/queue/order")
    def queue_order(body: QueueOrder):
        """Reorder batches: the given ids take the queue slots they already occupy, in the new order."""
        chosen = [store.batches[i] for i in body.ids if i in store.batches]
        slots = sorted(b["order"] for b in chosen)
        for b, order in zip(chosen, slots):
            b["order"] = order
            store.save(b)
        worker.notify()
        return {"ok": True}

    # ---- scripts and segments ----------------------------------------------------

    class ScriptEdit(BaseModel):
        text: str | None = Field(None, min_length=1, max_length=MAX_TEXT)
        title: str | None = None
        voice: str | None = None
        language: str | None = None

    def ensure_idle(b: dict, script: dict) -> None:
        if worker.current and worker.current[0] is b and worker.current[1]["script"] == script["n"]:
            raise HTTPException(409, "This script is being spoken right now. Pause the batch, wait for the current part, then edit.")
        if worker.finishing and worker.finishing[0] is b and worker.finishing[1] is script:
            raise HTTPException(409, "This script's files are being written right now. Try again in a moment.")

    @app.patch("/api/batches/{batch_id}/scripts/{n}")
    def edit_script(batch_id: str, n: int, body: ScriptEdit):
        b = get_batch(batch_id)
        s = get_script(b, n)
        ensure_idle(b, s)
        voice = check_voice(body.voice) if body.voice else ("" if body.voice == "" else None)
        language = check_language(body.language) if body.language else None
        try:
            store.edit_script(b, s, text=body.text, title=body.title, voice=voice, language=language)
        except ValueError as e:
            raise HTTPException(400, str(e))
        worker.notify()
        return summarize(b, full=True)

    @app.delete("/api/batches/{batch_id}/scripts/{n}")
    def delete_script(batch_id: str, n: int):
        b = get_batch(batch_id)
        s = get_script(b, n)
        ensure_idle(b, s)
        if len(b["scripts"]) == 1:
            raise HTTPException(409, "That's the batch's only script. Delete the batch instead.")
        try:
            store.delete_script(b, s)
        except OSError as e:
            raise HTTPException(409, str(e))
        return summarize(b, full=True)

    @app.post("/api/batches/{batch_id}/scripts/{n}/refinish")
    def refinish_script(batch_id: str, n: int):
        b = get_batch(batch_id)
        worker.refinish(b, get_script(b, n))
        return summarize(b, full=True)

    class SegmentEdit(BaseModel):
        text: str = Field(min_length=1, max_length=5000)

    @app.patch("/api/batches/{batch_id}/segments/{item_id}")
    def edit_segment(batch_id: str, item_id: str, body: SegmentEdit):
        b = get_batch(batch_id)
        it = get_item(b, item_id)
        if worker.is_busy_with(b, it):
            raise HTTPException(409, "That part is being spoken right now.")
        try:
            store.edit_segment(b, it, body.text)
        except ValueError as e:
            raise HTTPException(400, str(e))
        worker.notify()
        return summarize(b, full=True)

    class Regenerate(BaseModel):
        new_seed: bool = True

    @app.post("/api/batches/{batch_id}/segments/{item_id}/regenerate")
    def regenerate_segment(batch_id: str, item_id: str, body: Regenerate):
        b = get_batch(batch_id)
        try:
            worker.regenerate(b, get_item(b, item_id), body.new_seed)
        except ValueError as e:
            raise HTTPException(409, str(e))
        return summarize(b, full=True)

    @app.post("/api/batches/{batch_id}/segments/{item_id}/retry")
    def retry_segment(batch_id: str, item_id: str):
        b = get_batch(batch_id)
        worker.retry(b, item_id)
        return summarize(b, full=True)

    @app.get("/api/batches/{batch_id}/files/{rel:path}")
    def batch_file(batch_id: str, rel: str, download: int = 0):
        b = get_batch(batch_id)
        path = store.file_path(b, rel)
        if not path:
            raise HTTPException(404, "No such file")
        return FileResponse(path, filename=path.name if download else None,
                            headers={"Cache-Control": "no-cache"})

    # ---- export ------------------------------------------------------------------

    def export_files(b: dict, content: str) -> list[tuple[str, str]]:
        """(path in the batch folder, name in the export)"""
        files = []
        if content in ("final", "both"):
            for s in b["scripts"]:
                for rel in s["output"].get("files", {}).values():
                    files.append((rel, rel))
        if content in ("segments", "both"):
            for it in b["items"]:
                if it["status"] == "done":
                    files.append((it["file"], it["file"]))
        return [(rel, name) for rel, name in files if (store.folder(b) / rel).exists()]

    def scripts_txt(b: dict) -> str:
        return "\n\n".join(f"### {s['stem']} — {s['title']}\n{s['text']}" for s in b["scripts"]) + "\n"

    @app.get("/api/batches/{batch_id}/export.zip")
    def export_zip(batch_id: str, content: str = "final", extras: int = 1):
        b = get_batch(batch_id)
        files = export_files(b, content)
        if not files:
            raise HTTPException(404, "Nothing to export yet: no script is finished.")
        EXPORTS.mkdir(parents=True, exist_ok=True)
        path = EXPORTS / f"{b['id']}-{uuid.uuid4().hex[:6]}.zip"
        folder = store.folder(b)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for rel, name in files:
                z.write(folder / rel, name)
            if extras:
                z.write(folder / "batch.json", "batch.json")
                z.writestr("scripts.txt", scripts_txt(b))
        return FileResponse(path, filename=f"{b['name']}.zip", media_type="application/zip",
                            background=BackgroundTask(path.unlink, missing_ok=True))

    class ExportRequest(BaseModel):
        format: str = Field("folder", pattern="^(folder|zip)$")
        content: str = Field("final", pattern="^(final|segments|both)$")
        extras: bool = True

    @app.post("/api/exports/{batch_id}")
    def export_to_folder(batch_id: str, body: ExportRequest):
        """Write an export into the Exports folder from Settings (what agents use)."""
        b = get_batch(batch_id)
        files = export_files(b, body.content)
        if not files:
            raise HTTPException(404, "Nothing to export yet: no script is finished.")
        root = Path(cfg["exports_dir"])
        root.mkdir(parents=True, exist_ok=True)
        folder = store.folder(b)
        if body.format == "zip":
            path = root / f"{b['name']}.zip"
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
                for rel, name in files:
                    z.write(folder / rel, name)
                if body.extras:
                    z.write(folder / "batch.json", "batch.json")
                    z.writestr("scripts.txt", scripts_txt(b))
            return {"path": str(path), "files": len(files)}
        out = root / b["name"]
        for rel, name in files:
            (out / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(folder / rel, out / name)
        if body.extras:
            shutil.copy2(folder / "batch.json", out / "batch.json")
            (out / "scripts.txt").write_text(scripts_txt(b), encoding="utf-8")
        return {"path": str(out), "files": len(files)}

    # ---- voices ------------------------------------------------------------------

    @app.get("/api/voices")
    def list_voices():
        return voices.list()

    def form_float(form, key: str) -> float | None:
        v = form.get(key)
        try:
            return float(v) if v not in (None, "") else None
        except ValueError:
            raise HTTPException(400, f"{key} must be a number of seconds")

    @app.post("/api/voices")
    async def add_voice(request: Request):
        """A voice from an audio or video file. With separate=1 the voice is first taken out of any music under it.
        A long recording (a video, an interview) uses its best 12 seconds unless start/end are given."""
        form = await request.form()
        upload = form.get("file")
        if not hasattr(upload, "read"):
            raise HTTPException(400, "Choose an audio or video file.")
        language = str(form.get("language") or "")
        if language and language not in config.LANGUAGE_NAMES:
            raise HTTPException(400, "Unsupported language")
        filename = getattr(upload, "filename", "") or "clip.wav"
        separate = form.get("separate") in ("1", "true", "on")
        tmp = config.DATA / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        src = tmp / f"up-{uuid.uuid4().hex[:10]}{Path(filename).suffix.lower()[:6]}"
        with open(src, "wb") as f:  # stream to disk: a video can be large
            await asyncio.to_thread(shutil.copyfileobj, upload.file, f, 1 << 20)
        kwargs = dict(name=str(form.get("name") or ""), filename=filename, language=language,
                      notes=str(form.get("notes") or ""), denoise=form.get("denoise") in ("1", "true", "on"),
                      start=form_float(form, "start"), end=form_float(form, "end"))
        try:
            is_media = src.suffix.lower() in media.VIDEO_EXT or src.stat().st_size > 50 * 1024 * 1024
            if separate or is_media:
                samples, sr = await asyncio.to_thread(media.decode, src, 44100 if separate else None)
                extra = {}
                if separate:
                    # Only separate what's needed: the chosen range, or the most speech-filled minute of a long file.
                    start, end = kwargs.pop("start"), kwargs.pop("end")
                    if start is None and end is None and len(samples) > 90 * sr:
                        start, end = media.best_window(samples, sr, 60.0)
                    if start is not None or end is not None:
                        a, b_ = int((start or 0) * sr), int(end * sr) if end else len(samples)
                        samples = samples[a:b_]
                        extra["range_in_file"] = [round(start or 0, 2), round(b_ / sr, 2)]
                    samples, sr = await asyncio.to_thread(media.separate_voice, samples, sr, cfg)
                    extra["separated"] = True
                    kwargs.update(start=None, end=None)
                v = await asyncio.to_thread(voices.add, decoded=(samples, sr), extra=extra, **kwargs)
            else:
                v = await asyncio.to_thread(voices.add, data=src.read_bytes(), **kwargs)
        except (ValueError, media.MediaError) as e:
            raise HTTPException(400, str(e))
        finally:
            src.unlink(missing_ok=True)
        if any(config.MODELS[k].get("runtime") == "s2" for k in config.installed_models(cfg)):
            asyncio.create_task(transcribe_voice(v["id"]))  # ready for S2 Pro, and editable, before it's needed
        if not cfg["default_voice"]:
            cfg["default_voice"] = v["id"]
            config.save(cfg)
        return v

    async def transcribe_voice(vid: str) -> None:
        """What a new voice's clip says, heard by Whisper in the background (S2 Pro needs it to copy the voice)."""
        try:
            await asyncio.to_thread(s2engine.transcript, cfg, voices.clip(vid))
        except Exception as e:  # Whisper missing or busy: it's done when S2 Pro first uses the voice
            log.info("Couldn't transcribe the new voice %s yet: %s", vid, e)

    class VoiceEdit(BaseModel):
        name: str | None = None
        language: str | None = None
        notes: str | None = None
        transcript: str | None = Field(None, max_length=2000)

    @app.patch("/api/voices/{vid}")
    def edit_voice(vid: str, body: VoiceEdit):
        if body.language and body.language not in config.LANGUAGE_NAMES:
            raise HTTPException(400, "Unsupported language")
        try:
            return voices.update(vid, **body.model_dump())
        except KeyError:
            raise HTTPException(404, "No such voice")
        except ValueError as e:
            raise HTTPException(400, str(e))

    class Prepare(BaseModel):
        denoise: bool = False
        start: float | None = Field(None, ge=0)
        end: float | None = Field(None, gt=0)

    @app.post("/api/voices/{vid}/prepare")
    async def prepare_voice(vid: str, body: Prepare):
        try:
            v = await asyncio.to_thread(voices.reprepare, vid, denoise=body.denoise, start=body.start, end=body.end)
        except KeyError:
            raise HTTPException(404, "No such voice")
        except ValueError as e:
            raise HTTPException(400, str(e))
        for f in PREVIEWS.glob(f"{vid}-*.wav"):
            f.unlink(missing_ok=True)
        return v

    @app.delete("/api/voices/{vid}")
    def delete_voice(vid: str):
        v = voices.get(vid)
        if not v:
            raise HTTPException(404, "No such voice")
        users = [b["name"] for b in store.batches.values() if batch_status(b) in ("running", "queued", "paused")
                 and any(settings_for(b, s).get("voice") == v["id"] for s in b["scripts"])]
        if users:
            raise HTTPException(409, f"Batches in the queue use this voice ({', '.join(users[:3])}). Finish or cancel them first.")
        try:
            voices.delete(vid)
        except OSError as e:
            raise HTTPException(409, str(e))
        if cfg["default_voice"] == v["id"]:
            cfg["default_voice"] = ""
            config.save(cfg)
        return {"deleted": v["name"]}

    @app.get("/api/voices/{vid}/{which}")
    def voice_file(vid: str, which: str):
        v = voices.get(vid)
        if not v or which not in ("clip", "original"):
            raise HTTPException(404, "No such voice")
        path = voices.root / v["id"] / ("clip.wav" if which == "clip" else v["original"])
        return FileResponse(path, headers={"Cache-Control": "no-cache"})

    class Preview(BaseModel):
        text: str | None = Field(None, max_length=600)
        language: str | None = None

    @app.post("/api/voices/{vid}/preview")
    async def preview_voice(vid: str, body: Preview):
        """A short sample of the voice reading a sentence (cached until the clip changes)."""
        v = voices.get(vid)
        if not v:
            raise HTTPException(404, "No such voice")
        lang = check_language(body.language or v.get("language"))
        text = (body.text or "").strip() or PREVIEW_TEXT.get(lang) or v.get("transcript")  # else what its clip says
        if not text:
            raise HTTPException(400, f"Type a sentence in {config.LANGUAGE_NAMES.get(lang, lang)} for the voice to say.")
        model = model_for(lang)
        key = uuid.uuid5(uuid.NAMESPACE_URL, f"{lang}|{text}|{model}").hex[:10]
        PREVIEWS.mkdir(parents=True, exist_ok=True)
        path = PREVIEWS / f"{v['id']}-{key}.wav"
        if not path.exists():
            try:
                track, sr = await worker.speech(text, voice=v["id"], language=lang, model=model, seed=42)
            except (EngineError, ValueError) as e:
                raise HTTPException(500, str(e))
            audio.save_wav(path, track, sr)
        return FileResponse(path, media_type="audio/wav", headers={"Cache-Control": "no-cache"})

    class Find(BaseModel):
        language: str = "en"
        count: int = Field(4, ge=1, le=8)
        text: str | None = Field(None, max_length=400)

    @app.post("/api/voices/find")
    async def find_voices(body: Find):
        """Random new voices (no clip): the model invents one per seed. Keep the ones you like."""
        lang = check_language(body.language)
        model = model_for(lang)
        text = (body.text or "").strip() or PREVIEW_TEXT.get(lang)
        if not text:
            raise HTTPException(400, f"Type a sentence in {config.LANGUAGE_NAMES.get(lang, lang)} for the new voices to say.")
        FOUND.mkdir(parents=True, exist_ok=True)
        for f in FOUND.glob("*.wav"):  # samples from earlier searches that weren't kept
            if time.time() - f.stat().st_mtime > 3600:
                f.unlink(missing_ok=True)
        out = []
        for _ in range(body.count):
            seed = random.randint(0, 2**31 - 10**6)
            try:
                track, sr = await worker.speech(text, voice=None, language=lang, model=model, seed=seed, loudness=-18.0)
            except (EngineError, ValueError) as e:
                raise HTTPException(500, str(e))
            token = uuid.uuid4().hex[:12]
            audio.save_wav(FOUND / f"{token}.wav", track, sr)
            (FOUND / f"{token}.txt").write_text(text, encoding="utf-8")  # what it says, for S2 Pro if it's kept
            out.append({"token": token, "seed": seed, "language": lang, "seconds": round(len(track) / sr, 1)})
        return out

    @app.get("/api/found/{token}")
    def found_file(token: str):
        path = FOUND / f"{token}.wav"
        if not token.isalnum() or not path.exists():
            raise HTTPException(404, "That sample is gone. Find new voices again.")
        return FileResponse(path, media_type="audio/wav")

    class KeepFound(BaseModel):
        token: str
        name: str = Field(min_length=1, max_length=60)
        language: str | None = None
        notes: str = ""

    @app.post("/api/voices/keep")
    async def keep_found(body: KeepFound):
        path = FOUND / f"{body.token}.wav"
        if not body.token.isalnum() or not path.exists():
            raise HTTPException(404, "That sample is gone. Find new voices again.")
        try:
            said = FOUND / f"{body.token}.txt"
            v = await asyncio.to_thread(voices.add, name=body.name, data=path.read_bytes(), filename="found.wav",
                                        language=check_language(body.language), notes=body.notes, source="found",
                                        extra={"transcript": said.read_text(encoding="utf-8")} if said.exists() else None)
        except ValueError as e:
            raise HTTPException(400, str(e))
        if not cfg["default_voice"]:
            cfg["default_voice"] = v["id"]
            config.save(cfg)
        return v

    # ---- tools (ffmpeg) and transcripts -----------------------------------------------------

    @app.get("/api/tools")
    def list_tools():
        return downloads.tools()  # each says whether this PC can use it ("available")

    @app.post("/api/tools/{key}/{action}")
    async def tool_action(key: str, action: str):
        if key not in config.TOOLS:
            raise HTTPException(404, "Unknown tool")
        try:
            if action == "download":
                downloads.start_tool(key)
            elif action == "cancel":
                downloads.cancel("tool:" + key)
            elif action == "remove":
                await asyncio.to_thread(downloads.delete_tool, key)
            else:
                raise HTTPException(404, "Unknown action")
        except RuntimeError as e:
            raise HTTPException(409, str(e))
        return downloads.tools()

    @app.get("/api/transcripts")
    def list_transcripts():
        return transcripts.list()

    @app.post("/api/transcripts")
    async def add_transcript(request: Request):
        form = await request.form()
        upload = form.get("file")
        if not hasattr(upload, "read"):
            raise HTTPException(400, "Choose an audio or video file.")
        model = str(form.get("model") or "") or None
        if model and config.MODELS.get(model, {}).get("kind") != "subtitles":
            raise HTTPException(400, "Unknown Whisper model")
        if not subtitles.whisper_available(cfg):
            raise HTTPException(400, "No Whisper model is downloaded. Get one on the Models page.")
        filename = getattr(upload, "filename", "") or "audio"
        if Path(filename).suffix.lower() in media.VIDEO_EXT and not media.ffmpeg_exe():
            raise HTTPException(400, "Reading video needs ffmpeg. Download it on the Models page (Tools), then try again.")
        language = str(form.get("language") or "") or None
        if language and language not in config.LANGUAGE_NAMES:
            raise HTTPException(400, "Unsupported language")
        tmp = config.DATA / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        src = tmp / f"tr-{uuid.uuid4().hex[:10]}{Path(filename).suffix.lower()[:6]}"
        with open(src, "wb") as f:
            await asyncio.to_thread(shutil.copyfileobj, upload.file, f, 1 << 20)
        return transcripts.add(src, filename, model=model, language=language,
                               translate=form.get("translate") in ("1", "true", "on"))

    @app.get("/api/transcripts/{tid}/{fmt}")
    def transcript_file(tid: str, fmt: str, download: int = 0):
        t = transcripts.items.get(tid)
        if not t or fmt not in t.get("files", {}):
            raise HTTPException(404, "No such transcript file")
        path = transcripts.folder(t) / t["files"][fmt]
        media_type = {"txt": "text/plain; charset=utf-8", "srt": "text/plain; charset=utf-8",
                      "vtt": "text/vtt; charset=utf-8", "json": "application/json"}[fmt]
        return FileResponse(path, media_type=media_type, filename=path.name if download else None)

    @app.delete("/api/transcripts/{tid}")
    def delete_transcript(tid: str):
        try:
            transcripts.delete(tid)
        except KeyError:
            raise HTTPException(404, "No such transcript")
        except OSError as e:
            raise HTTPException(409, str(e))
        return {"deleted": tid}

    # ---- presets, pronunciation, output settings of a batch ------------------------------

    @app.get("/api/presets")
    def list_presets():
        return presets.list()

    class PresetIn(BaseModel):
        name: str = Field(min_length=1, max_length=60)
        settings: dict

    @app.post("/api/presets")
    def save_preset(body: PresetIn):
        s = dict(body.settings)
        if s.get("voice"):
            s["voice"] = check_voice(s["voice"])
        if s.get("language"):
            s["language"] = check_language(s["language"])
        try:
            return presets.save(body.name, s)
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app.delete("/api/presets/{pid}")
    def delete_preset(pid: str):
        try:
            presets.delete(pid)
        except KeyError:
            raise HTTPException(404, "No such preset")
        return {"deleted": pid}

    @app.get("/api/dictionary")
    def list_words():
        return sorted(dictionary.entries, key=lambda e: (e["language"], e["from"].lower()))

    class WordIn(BaseModel):
        written: str = Field(min_length=1, max_length=120)
        said: str = Field(min_length=1, max_length=300)
        language: str = ""
        case: bool = False

    @app.post("/api/dictionary")
    def add_word(body: WordIn):
        try:
            return dictionary.add(body.written, body.said, body.language, body.case)
        except ValueError as e:
            raise HTTPException(400, str(e))

    class WordEdit(BaseModel):
        written: str | None = None
        said: str | None = None
        language: str | None = None
        case: bool | None = None

    @app.get("/api/dictionary/export")
    def export_words(format: str = "csv", language: str | None = None):
        if format not in ("csv", "json"):
            raise HTTPException(400, "format must be csv or json")
        if language and language not in config.LANGUAGE_NAMES:
            raise HTTPException(400, "Unsupported language")
        import datetime as dt
        name = f"pronunciation{'-' + language if language else ''}-{dt.date.today().isoformat()}.{format}"
        return Response(dictionary.export(format, language or None),
                        media_type="text/csv; charset=utf-8" if format == "csv" else "application/json",
                        headers={"Content-Disposition": f'attachment; filename="{name}"'})

    @app.post("/api/dictionary/import")
    async def import_words(request: Request):
        """CSV (comma, semicolon or tab; English or Spanish headers), JSON, or TXT lines `written = said`."""
        form = await request.form()
        upload = form.get("file")
        if not hasattr(upload, "read"):
            raise HTTPException(400, "Choose a CSV, JSON or TXT file.")
        data = await upload.read()
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(400, "That file is over 10 MB; a pronunciation list is usually a few KB.")
        default = str(form.get("language") or "")
        if default and default not in config.LANGUAGE_NAMES:
            raise HTTPException(400, "Unsupported language")
        try:
            rows, problems = parse_import(data, getattr(upload, "filename", "") or "words.csv", default)
        except ValueError as e:
            raise HTTPException(400, str(e))
        if not rows and not problems:
            raise HTTPException(400, "No words found in that file.")
        result = dictionary.import_entries(rows, update=form.get("update", "1") in ("1", "true", "on"))
        return result | {"problems": problems[:50], "problem_count": len(problems)}

    @app.patch("/api/dictionary/{eid}")
    def edit_word(eid: str, body: WordEdit):
        try:
            return dictionary.update(eid, **{"from": body.written, "to": body.said, "language": body.language, "case": body.case})
        except KeyError:
            raise HTTPException(404, "No such entry")
        except ValueError as e:
            raise HTTPException(400, str(e))

    @app.delete("/api/dictionary/{eid}")
    def delete_word(eid: str):
        dictionary.delete(eid)
        return {"deleted": eid}

    class SpeakableIn(BaseModel):
        text: str = Field(max_length=MAX_TEXT)
        language: str | None = None
        spell_numbers: bool | None = None

    @app.post("/api/speakable")
    def speakable_preview(body: SpeakableIn):
        """What the voice will actually read for this text (dictionary + numbers), without speaking it."""
        lang = check_language(body.language)
        numbers = cfg["spell_numbers"] if body.spell_numbers is None else body.spell_numbers
        return {"text": speakable(body.text, lang, dictionary, numbers), "language": lang,
                "numbers_supported": lang in ("en", "es", "fr", "de", "it", "pt")}

    class OutputEdit(BaseModel):
        speed: float | None = Field(None, ge=config.SPEED_RANGE[0], le=config.SPEED_RANGE[1])
        loudness: float | None = Field(None, ge=-30, le=-9)
        formats: list[str] | None = None
        subtitles: bool | None = None
        pause_paragraph: float | None = Field(None, ge=0, le=10)

    @app.patch("/api/batches/{batch_id}/settings")
    def edit_output(batch_id: str, body: OutputEdit, script: int | None = None):
        """Change the output (speed, loudness, files, subtitles) and rebuild — no re-speaking. For the whole batch, or
        with ?script=n for one script only (each Quick take has its own)."""
        b = get_batch(batch_id)
        changes = {k: v for k, v in body.model_dump().items() if v is not None}
        if "formats" in changes:
            changes["formats"] = [f for f in changes["formats"] if f in ("wav", "mp3")]
            if not changes["formats"]:
                raise HTTPException(400, "Choose WAV, MP3 or both.")
        if script is not None:
            s = get_script(b, script)
            ensure_idle(b, s)
            s.setdefault("settings", {}).update(changes)
            worker.refinish(b, s)
            store.save(b)
            worker.notify()
            return summarize(b, full=True)
        if b.get("kind") == "singles":
            raise HTTPException(400, "Each Quick take has its own output: use the Output button on the take.")
        b["settings"].update(changes)
        for s in b["scripts"]:
            worker.refinish(b, s)
        store.save(b)
        worker.notify()
        return summarize(b, full=True)

    # ---- models, engine, setup ------------------------------------------------------

    @app.get("/api/models")
    def list_models():
        return downloads.status()

    @app.post("/api/models/{key}/download")
    async def download_model(key: str):
        if key not in config.MODELS:
            raise HTTPException(404, "Unknown model")
        try:
            downloads.start(key)
        except ValueError as e:  # e.g. S2 Pro without a CUDA or Vulkan engine
            raise HTTPException(409, str(e))
        return downloads.status()

    @app.post("/api/models/{key}/cancel")
    async def cancel_download(key: str):
        downloads.cancel(key)
        return downloads.status()

    @app.delete("/api/models/{key}/partial")
    async def discard_download(key: str):
        if key not in config.MODELS:
            raise HTTPException(404, "Unknown model")
        try:
            removed = downloads.discard(key)
        except RuntimeError as e:
            raise HTTPException(409, str(e))
        return {"removed": removed, "models": downloads.status()}

    @app.delete("/api/models/{key}")
    async def delete_model(key: str):
        if key not in config.MODELS:
            raise HTTPException(404, "Unknown model")
        if key == cfg["default_model"]:
            raise HTTPException(409, "That's the default voice model. Pick another default in Settings first.")
        if any(settings_for(b, s).get("model") == key for b in store.batches.values()
               if batch_status(b) in ("running", "queued", "paused") for s in b["scripts"]):
            raise HTTPException(409, "A batch in the queue uses this model. Finish or cancel it first.")
        return {"removed": downloads.delete(key), "models": downloads.status()}

    def setup_state() -> dict:
        hw = hardware.detect()
        eng = cfg["engine"]
        rec_engine = hardware.recommended_engine(hw)
        installed_eng = config.installed_engines(cfg)
        rec_model = hardware.recommended_model(hw, eng if eng in installed_eng else rec_engine)
        models = {m["key"]: m for m in downloads.status()}
        free = hardware.disk_free(cfg)
        return {
            "hardware": hw, "gpu": hardware.main_gpu(hw), "disk_free": free,
            "warnings": hardware.warnings(hw, cfg, eng),
            "engine": eng, "engine_release": config.ENGINE_RELEASE,
            "engines": [{"key": k, "label": e["label"], "about": e["about"],
                         "size": sum(z[1] for z in e["zips"]), "installed": k in installed_eng,
                         "active": k == eng and k in installed_eng, "recommended": k == rec_engine,
                         "partial": downloads.engine_partial(k), "job": downloads.jobs.get("engine:" + k)}
                        for k, e in config.ENGINES.items()],
            "models": [models[k] | {"fit": hardware.model_fit(k, hw, eng), "recommended": k in (rec_model, "whisper-small"),
                                    "default": k == cfg["default_model"],
                                    "enough_disk": free is None or models[k]["installed"] or free > models[k]["to_download"] + 5e8}
                       for k in config.MODELS],
            "benchmark": cfg.get("benchmark"),
            "whisper_gpu": downloads.whisper_gpu(),
            "steps": {"engine": eng in installed_eng, "model": cfg["default_model"] in config.installed_models(cfg),
                      "subtitles": subtitles.whisper_available(cfg), "voice": bool(voices.list()),
                      "benchmark": bool(cfg.get("benchmark"))},
            "ready": eng in installed_eng and cfg["default_model"] in config.installed_models(cfg),
        }

    @app.get("/api/setup")
    async def get_setup(refresh: bool = False):
        if refresh:
            await asyncio.to_thread(hardware.detect, True)
        return setup_state()

    @app.get("/api/about")
    def about():
        """The About page: version, this PC in a few words (for problem reports), folders, and the notices."""
        import platform
        notices = config.ROOT / "THIRD_PARTY_NOTICES.md"
        return {
            "version": __version__, "repo": REPO_URL, "installed": config.INSTALLED,
            "windows": f"Windows {platform.release()} ({platform.version()})", "python": platform.python_version(),
            "engine_release": config.ENGINE_RELEASE,
            "folders": {"Batches": str(store.root), "Voices": str(voices.root), "Models": cfg["models_dir"],
                        "Settings and logs": str(config.DATA)},
            "notices": notices.read_text(encoding="utf-8") if notices.exists() else "",
        }

    @app.post("/api/setup/engines/{key}/{action}")
    async def engine_action(key: str, action: str):
        if key not in config.ENGINES:
            raise HTTPException(404, "Unknown engine")
        if action == "download":
            downloads.start_engine(key)
        elif action == "cancel":
            downloads.cancel("engine:" + key)
        elif action == "discard":
            try:
                downloads.discard_engine(key)
            except RuntimeError as e:
                raise HTTPException(409, str(e))
        elif action == "use":
            if key not in config.installed_engines(cfg):
                raise HTTPException(400, "Download that engine first.")
            if key != cfg["engine"]:
                cfg["engine"] = key  # the next segment runs on it
                cfg.pop("benchmark", None)  # the speed was measured on the old engine
                config.save(cfg)
                downloads.ensure_whisper_gpu()  # Whisper follows the engine onto its graphics card
                downloads.ensure_s2_runtime()   # so does S2 Pro's s2.cpp
        elif action == "remove":
            if key == cfg["engine"]:
                raise HTTPException(409, "That engine is in use. Switch to another one first.")
            await asyncio.to_thread(downloads.delete_engine, key)
        else:
            raise HTTPException(404, "Unknown action")
        return setup_state()

    @app.get("/api/whisper-gpu")
    def whisper_gpu():
        return downloads.whisper_gpu()

    @app.post("/api/whisper-gpu/{action}")
    def whisper_gpu_action(action: str):
        """retry: download Whisper's graphics card build again after a failure; cancel: pause it."""
        if action == "retry":
            downloads.ensure_whisper_gpu(retry=True)
        elif action == "cancel":
            key = config.whisper_gpu_engine(cfg)
            if key:
                downloads.cancel("whisper-gpu:" + key)
        else:
            raise HTTPException(404, "Unknown action")
        return downloads.whisper_gpu()

    @app.post("/api/setup/benchmark")
    async def benchmark():
        """Speak a fixed paragraph and time it: how many times faster than real time this PC is."""
        model = check_model(None)
        if batches_active():
            raise HTTPException(409, "Wait for the running batches to finish, or pause them, then test.")
        sample = ("In the winter of 1913, a small fishing town woke up to find its lighthouse dark. For forty-two "
                  "years, the keeper had never missed a single night. His name was Elias Ward, and on that morning, "
                  "nobody could find him.")
        try:
            t0 = time.monotonic()
            await worker.speech("Hello.", voice=None, language="en", model=model, seed=1, loudness=None)  # warm-up
            warm = time.monotonic() - t0
            t0 = time.monotonic()
            track, sr = await worker.speech(sample, voice=None, language="en", model=model, seed=42, loudness=None)
            took = time.monotonic() - t0
        except EngineError as e:
            raise HTTPException(500, str(e))
        seconds = len(track) / sr
        cfg["benchmark"] = {"model": model, "engine": cfg["engine"], "audio_s": round(seconds, 1),
                            "took_s": round(took, 1), "x_realtime": round(seconds / took, 2),
                            "first_s": round(warm, 1), "at": int(time.time())}
        config.save(cfg)
        return setup_state()

    # ---- updates and settings ---------------------------------------------------------

    @app.get("/api/update")
    def update_state():
        return updater.state

    @app.post("/api/update/check")
    async def update_check():
        return await updater.check()

    @app.post("/api/update/{kind}")
    async def update_apply(kind: str):
        try:
            updater.start(kind)
        except ValueError as e:
            raise HTTPException(400, str(e))
        return updater.state

    @app.get("/api/settings")
    def get_settings():
        out = {k: cfg[k] for k in sorted(config.EDITABLE) if k != "hf_token"}
        return out | {"hf_token_set": bool((cfg.get("hf_token") or "").strip()),
                      "engine_dir": str(config.engine_dir(cfg)), "models_dir": cfg["models_dir"],
                      "voices_dir": str(voices.root), "data_dir": str(config.DATA),
                      "start_with_windows": autostart.enabled(), "python_exe": autostart.python_console(),
                      "mcp_script": str(config.ROOT / "studio_mcp.py"), "version": __version__, "repo_url": REPO_URL,
                      "installed": config.INSTALLED}

    @app.put("/api/settings")
    async def put_settings(request: Request):
        body = await request.json()
        if "start_with_windows" in body and bool(body["start_with_windows"]) != autostart.enabled():
            autostart.set_enabled(bool(body["start_with_windows"]))
        changes = {k: v for k, v in body.items() if k in config.EDITABLE and v != cfg.get(k)}
        if "default_model" in changes and changes["default_model"] not in config.voice_models():
            raise HTTPException(400, "Unknown voice model")
        if "default_language" in changes:
            check_language(changes["default_language"])
        if changes.get("subtitles_model") and config.MODELS.get(changes["subtitles_model"], {}).get("kind") != "subtitles":
            raise HTTPException(400, "Unknown subtitles model")
        if changes.get("default_voice"):
            changes["default_voice"] = check_voice(changes["default_voice"])
        if "api_key" in changes:
            changes["api_key"] = str(changes["api_key"]).strip()
            if len(changes["api_key"]) < 8 or any(c.isspace() for c in changes["api_key"]):
                raise HTTPException(400, "The API key needs at least 8 characters and no spaces.")
        if "batches_dir" in changes:
            if batches_active():
                raise HTTPException(409, "Finish or cancel running batches before moving the batches folder.")
            try:
                store.set_root(changes["batches_dir"])
            except OSError as e:
                raise HTTPException(400, f"Can't use that folder: {e}")
        if "exports_dir" in changes:
            try:
                Path(changes["exports_dir"]).mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise HTTPException(400, f"Can't use that exports folder: {e}")
        if "agent_read_dirs" in changes:
            dirs = changes["agent_read_dirs"]
            if not isinstance(dirs, list) or not all(isinstance(d, str) and d.strip() for d in dirs):
                raise HTTPException(400, "Agent folders must be a list of folder paths.")
            changes["agent_read_dirs"] = list(dict.fromkeys(d.strip() for d in dirs))
        if "formats" in changes:
            changes["formats"] = [f for f in changes["formats"] if f in ("wav", "mp3")]
            if not changes["formats"]:
                raise HTTPException(400, "Choose WAV, MP3 or both.")
        for key in ("notify", "agents_noncommercial", "check_updates", "subtitles", "spell_numbers"):
            if key in changes:
                changes[key] = bool(changes[key])
        for key, lo, hi in (("port", 1024, 65535), ("mp3_bitrate", 64, 320), ("max_chars", 150, 1200), ("timeout_s", 60, 7200)):
            if key in changes:
                changes[key] = max(lo, min(hi, int(changes[key])))
        for key, lo, hi in (("loudness", -30, -9), ("pause_segment", 0, 5), ("pause_paragraph", 0, 10), ("speed", *config.SPEED_RANGE)):
            if key in changes:
                changes[key] = max(lo, min(hi, float(changes[key])))
        if "hf_token" in changes:
            changes["hf_token"] = str(changes["hf_token"] or "").strip()
        cfg.update(changes)
        config.save(cfg)
        return get_settings() | {"restart_needed": "port" in changes}

    @app.post("/api/browse-folder")
    async def browse_folder(request: Request):
        """Open the Windows folder picker on this PC (a web page can't see full paths)."""
        start = str((await request.json()).get("start") or "")
        return {"path": await asyncio.to_thread(pick_folder, start)}

    @app.post("/api/open-folder")
    async def open_folder(request: Request):
        which = (await request.json()).get("which")
        paths = {"batches": store.root, "exports": Path(cfg["exports_dir"]), "voices": voices.root,
                 "models": Path(cfg["models_dir"]), "logs": config.DATA / "logs"}
        if which not in paths:
            raise HTTPException(404, "Unknown folder")
        paths[which].mkdir(parents=True, exist_ok=True)
        os.startfile(paths[which])
        return {"ok": True}

    @app.post("/api/split-preview")
    async def split_preview(request: Request):
        """How a script would be split into segments, and roughly how long it is (for the Create page)."""
        body = await request.json()
        text = str(body.get("text") or "")[:MAX_TEXT]
        split = {k: body.get(k, cfg[k]) for k in ("max_chars", "pause_segment", "pause_paragraph")}
        split["max_chars"] = config.part_chars(body.get("model") or cfg["default_model"], split["max_chars"])
        parts = textmod.split(text, **split)
        return {"segments": len(parts), "chars": len(text), "estimate_s": round(textmod.estimate_seconds(text)),
                "pauses_s": round(sum(p["pause_after"] for p in parts), 1),
                "parts": [{"text": p["text"][:80], "pause_after": p["pause_after"]} for p in parts[:200]]}

    # ---- OpenAI-compatible API ----------------------------------------------------------

    def require_key(authorization: str | None = Header(None)):
        if authorization != f"Bearer {cfg['api_key']}":
            raise HTTPException(401, "Invalid or missing API key")

    @app.get("/v1/health")
    def health():
        return {"status": "ok", "engine": engine.state, "version": __version__}

    @app.get("/v1/models", dependencies=[Depends(require_key)])
    def api_models():
        return {"object": "list", "data": [
            {"id": config.MODELS[k]["api_id"], "object": "model", "owned_by": "local", "label": config.MODELS[k]["label"],
             "kind": config.MODELS[k]["kind"], "license": config.MODELS[k]["license"]}
            for k in config.installed_models(cfg)]}

    @app.get("/v1/audio/voices", dependencies=[Depends(require_key)])
    def api_voices():
        return {"object": "list", "data": [{"id": v["id"], "name": v["name"], "language": v.get("language"),
                                            "seconds": v.get("seconds"), "notes": v.get("notes")} for v in voices.list()]}

    class SpeechIn(BaseModel):
        input: str = Field(min_length=1, max_length=MAX_TEXT)
        model: str | None = None
        voice: str | None = None
        response_format: str = Field("mp3", pattern="^(mp3|wav|pcm|flac)$")
        speed: float = Field(1.0, ge=0.25, le=4.0)
        language: str | None = None   # extension: en, es, … (defaults to the voice's language)
        seed: int | None = Field(None, ge=0, lt=2**31)  # extension
        instructions: str | None = None  # accepted for compatibility; this model doesn't take style instructions

    @app.post("/v1/audio/speech", dependencies=[Depends(require_key)])
    async def api_speech(p: SpeechIn):
        """OpenAI's /v1/audio/speech. `voice` is a name or id from the voice library; OpenAI's built-in names
        (alloy, nova…) fall back to the default voice from Settings."""
        v = voices.get(p.voice or "") or voices.get(cfg["default_voice"])
        if not v:
            raise HTTPException(400, "No voice: pass a voice name from the voice library (GET /v1/audio/voices), "
                                     "or set a default voice in Settings.")
        lang = check_language(p.language or v.get("language"))
        check_speaks(check_model(p.model), lang)
        try:
            # OpenAI allows 0.25-4; speech stays natural between 0.8 and 1.25, so the speed is kept in that range.
            track, sr = await worker.speech(p.input, voice=v["id"], language=lang, model=check_model(p.model),
                                            seed=p.seed, loudness=cfg["loudness"], speed=p.speed)
        except (EngineError, ValueError) as e:
            raise HTTPException(500, str(e))
        if p.response_format == "mp3":
            data = await asyncio.to_thread(audio.mp3_bytes, track, sr, cfg["mp3_bitrate"])
        elif p.response_format == "pcm":
            data = (track.clip(-1, 1) * 32767).astype("<i2").tobytes()
        elif p.response_format == "flac":
            import io
            import soundfile as sf
            buf = io.BytesIO()
            sf.write(buf, track, sr, format="FLAC")
            data = buf.getvalue()
        else:
            data = audio.wav_bytes(track, sr)
        return Response(data, media_type=AUDIO_TYPES[p.response_format],
                        headers={"X-Sample-Rate": str(sr), "X-Voice": v["name"], "X-Language": lang})

    @app.post("/v1/audio/transcriptions", dependencies=[Depends(require_key)])
    async def api_transcribe(request: Request):
        """OpenAI's /v1/audio/transcriptions (multipart: file, model, language, response_format)."""
        form = await request.form()
        upload = form.get("file")
        if not hasattr(upload, "read"):
            raise HTTPException(400, "file is required")
        model_name = str(form.get("model") or "")
        model = next((k for k, m in config.MODELS.items() if m["kind"] == "subtitles" and model_name in (k, m["api_id"])),
                     None) or config.subtitles_model(cfg)
        if not model or model not in config.installed_models(cfg) or not subtitles.whisper_available(cfg):
            raise HTTPException(400, "No transcription model installed. Download Whisper on the Models page.")
        fmt = str(form.get("response_format") or "json")
        language = str(form.get("language") or "") or None
        try:
            a, sr = audio.load(await upload.read())
        except ValueError as e:
            raise HTTPException(400, str(e))
        tmp = config.DATA / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        wav = tmp / f"t{uuid.uuid4().hex[:10]}.wav"
        audio.save_wav(wav, a, sr)
        try:
            result = await asyncio.to_thread(subtitles.run_whisper, cfg, wav, language, model)
        except subtitles.WhisperError as e:
            raise HTTPException(500, str(e))
        finally:
            wav.unlink(missing_ok=True)
        text = subtitles.transcript(result)
        if fmt == "text":
            return PlainTextResponse(text)
        if fmt in ("srt", "vtt"):
            heard = subtitles.whisper_words(result)
            srt = subtitles.from_whisper(text, heard, len(a) / sr) if heard else ""
            if fmt == "vtt":
                srt = "WEBVTT\n\n" + srt.replace(",", ".")
            return PlainTextResponse(srt)
        if fmt == "verbose_json":
            segs = [{"id": i, "start": s["offsets"]["from"] / 1000, "end": s["offsets"]["to"] / 1000, "text": s["text"].strip()}
                    for i, s in enumerate(result.get("transcription", []))]
            return {"text": text, "language": result.get("result", {}).get("language"), "duration": len(a) / sr,
                    "segments": segs}
        return {"text": text}

    if mcp:
        app.router.routes.extend(mcp.streamable_http_app().routes)  # POST/GET /mcp, exact path (no redirect)
    app.mount("/help-files", StaticFiles(directory=HELP), name="help")
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
    return app
