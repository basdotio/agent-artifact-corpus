"""Settings (data/config.json), the engine builds, and the models the app can download."""
import ctypes
import json
import os
import secrets
from pathlib import Path

from . import APP_NAME, REPO_URL

ROOT = Path(__file__).resolve().parent.parent  # the code
# The installer drops an "installed" marker next to the code. An installed copy keeps models, engine, voices
# and settings in %LOCALAPPDATA% and audio in Music, so updating or uninstalling the app never touches them.
# Run from source, everything stays inside this folder.
INSTALLED = (ROOT / "installed").exists()


def _music() -> Path:
    """The user's Music folder, wherever it really is (it may be moved or synced by OneDrive)."""
    import uuid
    folder_id = (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID("4BD8D571-6D19-48D3-BE97-422220080E43").bytes_le)
    buf = ctypes.c_wchar_p()
    try:
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(folder_id), 0, None, ctypes.byref(buf)) == 0:
            path = Path(buf.value)
            ctypes.windll.ole32.CoTaskMemFree(buf)
            return path
    except (AttributeError, OSError):
        pass
    return Path.home() / "Music"


HOME = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME if INSTALLED else ROOT
MUSIC = _music() / APP_NAME if INSTALLED else ROOT
DATA = HOME / "data"
CONFIG_FILE = DATA / "config.json"
VOICES = HOME / "voices"

DEFAULTS = {
    "host": "127.0.0.1",
    "port": 9830,
    "api_key": None,  # generated on first run
    "batches_dir": str(MUSIC / ("Batches" if INSTALLED else "batches")),
    "exports_dir": str(MUSIC / ("Exports" if INSTALLED else "exports")),  # where agents (MCP) save audio and exports
    # folders agents may read voice clips and scripts from (plus batches and exports, always)
    "agent_read_dirs": [str(Path.home() / d) for d in ("Music", "Downloads", "Desktop", "Documents")],
    "agents_noncommercial": False,  # may agents use non-commercial models?
    "engine": "cuda",  # which engine build runs the models (ENGINES); picked on the Setup page
    "models_dir": str(HOME / "models"),
    "default_model": "qwen3-tts-q8",
    "default_language": "en",
    "default_voice": "",
    # Output: what every finished script is turned into
    "loudness": -16.0,       # LUFS; YouTube plays at about -14, voiceovers usually sit at -16
    "formats": ["wav", "mp3"],
    "mp3_bitrate": 192,
    "subtitles": True,       # SRT next to each finished script (needs the subtitles model)
    "subtitles_model": "",   # which Whisper times subtitles and transcribes ("" = best installed)
    "speed": 1.0,            # 0.8-1.25: faster or slower speech, same pitch (applied when a script's files are made)
    "spell_numbers": True,   # read 1913 / $5M / 35% / 5:30 as words (en, es, fr, de, it, pt)
    "pause_segment": 0.25,   # seconds of silence where a long paragraph was split
    "pause_paragraph": 0.7,  # seconds between paragraphs
    "max_chars": 600,        # longest piece of text sent to the engine at once (about 40 seconds of speech)
    "notify": True,
    "check_updates": True,
    "hf_token": "",
    "timeout_s": 900,        # one segment
}

# llama.cpp builds, from one pinned release so every engine behaves the same. (url, size, sha256)
ENGINE_RELEASE = "b11476"
_GH = f"https://github.com/ggml-org/llama.cpp/releases/download/{ENGINE_RELEASE}/"
ENGINES = {
    "cuda": {"label": "NVIDIA · CUDA", "about": "The fastest option for NVIDIA cards (GeForce RTX 20 series and newer). Needs a 2025 or newer driver.",
             "zips": [(_GH + "llama-b11476-bin-win-cuda-13.4-x64.zip", 153139193, "0f947f51ece3b807a7f556dbdf45dc1a7f31aa6ea265657639007a33ef1ce5e0"),
                      (_GH + "cudart-llama-bin-win-cuda-13.4-x64.zip", 423535356, "738f8c251ac22b70c3ae6f83a10cf222725df0395246a2cf58f32bdb85fbe668")],
             "gpu": True},
    "cuda12": {"label": "NVIDIA · CUDA (older driver)", "about": "For NVIDIA cards whose driver can't be updated to a 2025 one, and GTX 10/16 cards.",
               "zips": [(_GH + "llama-b11476-bin-win-cuda-12.4-x64.zip", 264521953, "b30289b92274bb7e89200832f4bcfd9e731b716a4056d00b61440f623d4cc8e8"),
                        (_GH + "cudart-llama-bin-win-cuda-12.4-x64.zip", 391443627, "8c79a9b226de4b3cacfd1f83d24f962d0773be79f1e7b75c6af4ded7e32ae1d6")],
               "gpu": True},
    "vulkan": {"label": "AMD / Intel · Vulkan", "about": "For AMD Radeon and Intel Arc cards. Also works on NVIDIA, a little slower than CUDA.",
               "zips": [(_GH + "llama-b11476-bin-win-vulkan-x64.zip", 33380424, "5c71e7b749697da4a8d46e9ee55486845cbba27c9dfbecb4007f31ba6610d523")],
               "gpu": True},
    "cpu": {"label": "CPU only", "about": "No graphics card needed. Speech comes out a bit slower than real time.",
            "zips": [(_GH + "llama-b11476-bin-win-cpu-x64.zip", 19441535, "a23e548c6b3525c38bcfeceaff919786ae06741857043cb670279b70100e5483")],
            "gpu": False},
}
ENGINE_EXE = "llama-tts.exe"

# whisper.cpp. The CPU build works on every PC and comes with the first Whisper model. With a graphics card voice
# engine, Whisper runs on the card too (WHISPER_GPU below): 8-10x faster, and the PC stays free.
WHISPER_RELEASE = "b5454"
WHISPER_ZIP = (f"https://github.com/ggml-org/whisper.cpp/releases/download/{WHISPER_RELEASE}/whisper-bin-x64.zip",
               8928640, "6ba69e3482d7826214f90a6a9c84ca07782aec1e1d0c6a7c30c994fd5d816ccb")
WHISPER_EXE = "whisper-cli.exe"

# Whisper on the graphics card: our builds of the same whisper.cpp, one per graphics card voice engine (made by
# .github/workflows/whisper.yml, release "whisper-b5454"). The CUDA ones load cuBLAS/cudart from that engine's
# folder, so nothing of NVIDIA's is downloaded twice; Vulkan needs only the graphics driver. Fetched by themselves
# once the engine and a Whisper model are there. (url, size, sha256)
_WGPU = f"{REPO_URL}/releases/download/whisper-{WHISPER_RELEASE}/whisper-{WHISPER_RELEASE}-win-"
WHISPER_GPU = {
    "cuda": (_WGPU + "cuda-13.4-x64.zip", 137475345, "016a4d6c99b6afa346dd89838ceec13cb72c80e2c7a6ab8d72612f3db1189326"),
    "cuda12": (_WGPU + "cuda-12.4-x64.zip", 258606838, "cd3b99a09b0472b4df2f5ada5f0ebfdfecd875aaacac805372ba667fcfc904f2"),
    "vulkan": (_WGPU + "vulkan-x64.zip", 18205922, "578fe45668a82df43c7b4e850cc8b7e625ad3d07be1ae7dc8b0e376406ae0d7e"),
}


def engine_dir(cfg: dict, key: str | None = None) -> Path:
    return HOME / "engine" / (key or cfg["engine"])


def whisper_dir() -> Path:
    return HOME / "engine" / "whisper"


# The second voice engine: s2.cpp running Fish Audio S2 Pro, one build per graphics card engine (made by
# .github/workflows/s2cpp.yml, release S2_RELEASE). The CUDA build loads cuBLAS/cudart from the voice engine's folder.
# It comes with an S2 Pro model download. (url, size, sha256)
S2_RELEASE = "s2cpp-2c33261"
S2_EXE = "s2.exe"
_S2 = f"{REPO_URL}/releases/download/{S2_RELEASE}/s2cpp-win-"
S2_RUNTIME = {
    "cuda": (_S2 + "cuda-13.4-x64.zip", 124289419, "257e8600d75947503ec0f031f26adfcd4a18dbec694c6ce08072d75875fe426b"),
    "vulkan": (_S2 + "vulkan-x64.zip", 20430998, "123941edcf6ae522fd7121c6cd46107e8ffcbfa32b56041e9da7cbc14ab8f86c"),
}


def s2_dir(engine: str) -> Path:
    return HOME / "engine" / f"s2-{engine}"


def s2_engine(cfg: dict) -> str | None:
    """The engine S2 Pro runs on: the one in use, if s2.cpp has a build for it and the engine is installed."""
    key = cfg["engine"]
    return key if key in S2_RUNTIME and (engine_dir(cfg, key) / ENGINE_EXE).exists() else None


def whisper_gpu_dir(engine: str) -> Path:
    return HOME / "engine" / f"whisper-gpu-{engine}"


def whisper_gpu_engine(cfg: dict) -> str | None:
    """The voice engine whose graphics card Whisper uses: the one in use, if it's a graphics card engine and installed."""
    key = cfg["engine"]
    return key if key in WHISPER_GPU and (engine_dir(cfg, key) / ENGINE_EXE).exists() else None


def installed_engines(cfg: dict) -> list[str]:
    return [k for k in ENGINES if (engine_dir(cfg, k) / ENGINE_EXE).exists()]


HF = "https://huggingface.co/"
_QWEN = HF + "ggml-org/Qwen3-TTS-12Hz-1.7B-Base-GGUF/resolve/main/"
_WHISPER = HF + "ggerganov/whisper.cpp/resolve/main/"
_S2PRO = HF + "rodrigomt/s2-pro-gguf/resolve/main/"  # S2 Pro as GGUF for s2.cpp (decoder kept in F16)
# Every file a model can need (url, size, sha256); shared files are downloaded once.
FILES = {
    "Qwen3-TTS-12Hz-1.7B-Base-Q8_0.gguf": (_QWEN + "Qwen3-TTS-12Hz-1.7B-Base-Q8_0.gguf", 1847874400,
                                           "ac7931aeb2e7aad1a6ed6602d353a5679c9d096b18ce8204ac730a8408d572e1"),
    "Qwen3-TTS-12Hz-1.7B-Base-Q4_K_M.gguf": (_QWEN + "Qwen3-TTS-12Hz-1.7B-Base-Q4_K_M.gguf", 1035965280,
                                             "8d18c94acb2addd042f97da63c98be144eafa76d0d9495177eab65130cf85129"),
    "mmproj-Qwen3-TTS-12Hz-1.7B-Base-Q8_0.gguf": (_QWEN + "mmproj-Qwen3-TTS-12Hz-1.7B-Base-Q8_0.gguf", 446422912,
                                                  "6fd65188839bcd6ecc91b277ad471e22a0edfada4699a0fe82f1165c18cfcce2"),
    "s2-pro-q8_0.gguf": (_S2PRO + "s2-pro-q8_0.gguf", 5630037088,
                         "e2043182234786e7b975547d3bbcb23ff02e4ff684b82f7fa851287e4cb4f267"),
    "s2-pro-q6_k.gguf": (_S2PRO + "s2-pro-q6_k.gguf", 4525266528,
                         "84ac904172a2cadb84e8f7f14ea3f1acef0584987635e85f7207fd254eafa235"),
    "ggml-base-q5_1.bin": (_WHISPER + "ggml-base-q5_1.bin", 59707625,
                           "422f1ae452ade6f30a004d7e5c6a43195e4433bc370bf23fac9cc591f01a8898"),
    "ggml-small-q5_1.bin": (_WHISPER + "ggml-small-q5_1.bin", 190085487,
                            "ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb"),
    "ggml-medium-q5_0.bin": (_WHISPER + "ggml-medium-q5_0.bin", 539212467,
                             "19fea4b380c3a618ec4723c3eef2eb785ffba0d0538cf43f8f235e7b3b34220f"),
    "ggml-large-v3-turbo-q5_0.bin": (_WHISPER + "ggml-large-v3-turbo-q5_0.bin", 574041195,
                                     "394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2"),
    "ggml-large-v3-q5_0.bin": (_WHISPER + "ggml-large-v3-q5_0.bin", 1081140203,
                               "d75795ecff3f83b5faa89d1900604ad8c780abd5739fae406de19f23ecd98ad1"),
    "UVR-MDX-NET-Voc_FT.onnx": ("https://github.com/k2-fsa/sherpa-onnx/releases/download/source-separation-models/"
                                "UVR-MDX-NET-Voc_FT.onnx", 66762795,
                                "e411182ce2c53541fefdcc99a8f46f2fe03978eb22038b9497c1d9d95a00fad4"),
}

# Programs the app can download besides the engine. ffmpeg reads video files (MP4, MKV, MOV, WEBM…); if it's
# already installed on the PC (on PATH), that copy is used and nothing is downloaded.
TOOLS = {
    "ffmpeg": {"label": "ffmpeg (video files)", "exe": "ffmpeg.exe",
               "about": "Lets the app read video files (MP4, MKV, MOV, WEBM…) for transcripts and voice clips.",
               "license": "GPL v3 — a separate program; using it doesn't affect your audio",
               "zip": ("https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-essentials_build.zip",
                       114768076, "60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba")},
}


def tool_dir(key: str) -> Path:
    return HOME / "engine" / key

# Language codes the voice models take; the label is shown in the app.
LANGUAGES = {"en": "English", "es": "Spanish", "fr": "French", "de": "German", "it": "Italian",
             "pt": "Portuguese", "ru": "Russian", "ja": "Japanese", "ko": "Korean", "zh": "Chinese"}

# What S2 Pro speaks (from its model card): it reads the language from the text itself.
S2_LANGUAGES = ["zh", "en", "ja", "ko", "es", "pt", "ar", "ru", "fr", "de", "sv", "it", "tr", "no", "nl", "cy", "eu",
                "ca", "da", "gl", "ta", "hu", "fi", "pl", "et", "hi", "la", "ur", "th", "vi", "jw", "bn", "yo", "sl",
                "cs", "sw", "nn", "he", "ms", "uk", "id", "kk", "bg", "lv", "my", "tl", "sk", "ne", "fa", "af", "el",
                "bo", "hr", "ro", "sn", "mi", "yi", "am", "be", "km", "is", "az", "sd", "br", "sq", "ps", "mn", "ht",
                "ml", "sr", "sa", "te", "ka", "bs", "pa", "lt", "kn", "si", "hy", "mr", "as", "gu", "fo"]

# Every language a voice model here speaks: Qwen3-TTS's ten first, then the rest of S2 Pro's by name. The language
# picked for a script also sets Whisper's language, numbers as words and the pronunciation list.
LANGUAGE_NAMES = {**LANGUAGES, **{k: v for k, v in sorted({"af": "Afrikaans", "sq": "Albanian", "am": "Amharic", "ar": "Arabic", "hy": "Armenian", "as": "Assamese", "az": "Azerbaijani", "eu": "Basque", "be": "Belarusian", "bn": "Bengali", "bs": "Bosnian", "br": "Breton", "bg": "Bulgarian", "my": "Burmese", "ca": "Catalan", "hr": "Croatian", "cs": "Czech", "da": "Danish", "nl": "Dutch", "et": "Estonian", "fo": "Faroese", "fi": "Finnish", "gl": "Galician", "ka": "Georgian", "el": "Greek", "gu": "Gujarati", "ht": "Haitian Creole", "he": "Hebrew", "hi": "Hindi", "hu": "Hungarian", "is": "Icelandic", "id": "Indonesian", "jw": "Javanese", "kn": "Kannada", "kk": "Kazakh", "km": "Khmer", "la": "Latin", "lv": "Latvian", "lt": "Lithuanian", "ms": "Malay", "ml": "Malayalam", "mi": "Maori", "mr": "Marathi", "mn": "Mongolian", "ne": "Nepali", "no": "Norwegian", "nn": "Norwegian Nynorsk", "ps": "Pashto", "fa": "Persian", "pl": "Polish", "pa": "Punjabi", "ro": "Romanian", "sa": "Sanskrit", "sr": "Serbian", "sn": "Shona", "sd": "Sindhi", "si": "Sinhala", "sk": "Slovak", "sl": "Slovenian", "sw": "Swahili", "sv": "Swedish", "tl": "Tagalog", "ta": "Tamil", "te": "Telugu", "th": "Thai", "bo": "Tibetan", "tr": "Turkish", "uk": "Ukrainian", "ur": "Urdu", "vi": "Vietnamese", "cy": "Welsh", "yi": "Yiddish", "yo": "Yoruba"}.items(), key=lambda kv: kv[1])}}

# kind "voice": speaks text (runs on the engine). kind "subtitles": whisper.cpp for SRT timings and transcripts.
MODELS = {
    "qwen3-tts-q8": {
        "kind": "voice", "label": "Qwen3-TTS 1.7B · Q8", "short": "Qwen3-TTS · best quality", "api_id": "qwen3-tts",
        "files": ["Qwen3-TTS-12Hz-1.7B-Base-Q8_0.gguf", "mmproj-Qwen3-TTS-12Hz-1.7B-Base-Q8_0.gguf"],
        "license": "Apache 2.0 — commercial use OK", "page": HF + "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "languages": list(LANGUAGES), "vram_gb": 4.2,
        "about": "The default. Natural voices in 10 languages, clones a voice from a few seconds of audio. "
                 "About 2× faster than real time on an RTX 5060 laptop GPU."},
    "qwen3-tts-q4": {
        "kind": "voice", "label": "Qwen3-TTS 1.7B · Q4", "short": "Qwen3-TTS · smaller", "api_id": "qwen3-tts-q4",
        "files": ["Qwen3-TTS-12Hz-1.7B-Base-Q4_K_M.gguf", "mmproj-Qwen3-TTS-12Hz-1.7B-Base-Q8_0.gguf"],
        "license": "Apache 2.0 — commercial use OK", "page": HF + "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "languages": list(LANGUAGES), "vram_gb": 3.2,
        "about": "Same model, compressed further: for graphics cards with 4 GB or less, or CPU-only PCs. "
                 "Slightly less polished."},
    # runtime "s2": spoken by s2.cpp (S2_RUNTIME), not llama.cpp; only on the engines listed. Parts are kept shorter
    # (max_chars): the voice fades on long stretches. vram_gb is the peak measured on an RTX 5060 (8 GB).
    "s2-pro-q8": {
        "kind": "voice", "runtime": "s2", "engines": ["cuda", "vulkan"], "label": "Fish Audio S2 Pro · Q8",
        "short": "S2 Pro · expressive, 80+ languages", "api_id": "s2-pro", "files": ["s2-pro-q8_0.gguf"],
        "license": "Fish Audio Research License — non-commercial; commercial use needs a licence from Fish Audio",
        "noncommercial": True, "page": HF + "fishaudio/s2-pro", "languages": S2_LANGUAGES, "vram_gb": 7.2,
        "max_chars": 300, "tags": True,
        "about": "Very expressive, with emotion tags like [whisper] or [excited] in the text, and 80+ languages. "
                 "About real time on an NVIDIA card with 8 GB or more (half the speed of Qwen3-TTS); slower on Vulkan."},
    "s2-pro-q6": {
        "kind": "voice", "runtime": "s2", "engines": ["cuda", "vulkan"], "label": "Fish Audio S2 Pro · Q6",
        "short": "S2 Pro · for 6-8 GB cards", "api_id": "s2-pro-q6", "files": ["s2-pro-q6_k.gguf"],
        "license": "Fish Audio Research License — non-commercial; commercial use needs a licence from Fish Audio",
        "noncommercial": True, "page": HF + "fishaudio/s2-pro", "languages": S2_LANGUAGES, "vram_gb": 6.2,
        "max_chars": 300, "tags": True,
        "about": "Same model, compressed a little further, for graphics cards with 6 to 8 GB. Emotion tags are a "
                 "little weaker than in Q8."},
    # Subtitle timing only needs Whisper to find the words (the text comes from the script), so small is plenty;
    # the bigger ones are for transcribing audio you didn't write (the transcription API, the MCP transcribe tool).
    "whisper-base": {
        "kind": "subtitles", "label": "Whisper base", "short": "Subtitles · fastest", "api_id": "whisper-base",
        "files": ["ggml-base-q5_1.bin"], "license": "MIT — commercial use OK", "page": HF + "openai/whisper-base",
        "about": "The smallest, and the quickest on the processor (about 24× faster than real time on an Intel Core "
                 "Ultra 9). As good as small for timing clear English narration; less sure of other languages."},
    "whisper-small": {
        "kind": "subtitles", "label": "Whisper small", "short": "Subtitles · fast", "api_id": "whisper-small",
        "files": ["ggml-small-q5_1.bin"], "license": "MIT — commercial use OK", "page": HF + "openai/whisper-small",
        "about": "Times the subtitles (SRT) of every finished script. Plenty for subtitles in all 10 languages, and "
                 "quick on the processor too (about 10× faster than real time on an Intel Core Ultra 9)."},
    "whisper-medium": {
        "kind": "subtitles", "label": "Whisper medium", "short": "Transcripts · more accurate", "api_id": "whisper-medium",
        "files": ["ggml-medium-q5_0.bin"], "license": "MIT — commercial use OK", "page": HF + "openai/whisper-medium",
        "about": "More accurate, especially in Spanish and other non-English languages. Slower than small."},
    "whisper-turbo": {
        "kind": "subtitles", "label": "Whisper large-v3 turbo", "short": "Transcripts · accurate and quick", "api_id": "whisper-large-v3-turbo",
        "files": ["ggml-large-v3-turbo-q5_0.bin"], "license": "MIT — commercial use OK", "page": HF + "openai/whisper-large-v3-turbo",
        "about": "Close to large-v3 accuracy at a fraction of the work. On a graphics card it's the best pick for "
                 "everything: a 26-minute script in about 40 seconds. Also good for transcribing audio you didn't write."},
    "whisper-large": {
        "kind": "subtitles", "label": "Whisper large-v3", "short": "Transcripts · most accurate", "api_id": "whisper-large-v3",
        "files": ["ggml-large-v3-q5_0.bin"], "license": "MIT — commercial use OK", "page": HF + "openai/whisper-large-v3",
        "about": "The most accurate Whisper, and the slowest (very slow on the processor). For hard audio: accents, "
                 "noise, music underneath."},
}
MODELS["uvr-vocals"] = {
    "kind": "separation", "label": "Voice separator (UVR MDX-Net)", "short": "Separates a voice from music",
    "api_id": "uvr-mdx-net-voc-ft", "files": ["UVR-MDX-NET-Voc_FT.onnx"],
    "license": "MIT — commercial use OK", "page": "https://github.com/Anjok07/ultimatevocalremovergui",
    "about": "Takes the voice out of a clip with music or background sound under it, so it can become a clean "
             "reference voice. Runs on the CPU, about 4× faster than real time."}
SUBTITLE_PREFERENCE = ["whisper-small", "whisper-turbo", "whisper-medium", "whisper-base", "whisper-large"]
# With Whisper on the graphics card, turbo is about as quick as small there and far more accurate outside English.
SUBTITLE_PREFERENCE_GPU = ["whisper-turbo", *(k for k in SUBTITLE_PREFERENCE if k != "whisper-turbo")]


def model_files(key: str) -> list[str]:
    return list(MODELS[key]["files"])


def model_page(key: str) -> str:
    return MODELS[key]["page"]


def part_chars(model: str | None, max_chars: int) -> int:
    """Longest part for this voice model: the setting, or less for models whose voice fades on long stretches."""
    return min(int(max_chars), int((MODELS.get(model) or {}).get("max_chars") or max_chars))


def voice_models() -> list[str]:
    return [k for k, m in MODELS.items() if m["kind"] == "voice"]


EDITABLE = {"batches_dir", "exports_dir", "default_model", "default_language", "default_voice", "port", "api_key",
            "notify", "agent_read_dirs", "agents_noncommercial", "check_updates", "loudness", "formats", "mp3_bitrate",
            "subtitles", "subtitles_model", "pause_segment", "pause_paragraph", "max_chars", "hf_token", "timeout_s",
            "speed", "spell_numbers"}
SPEED_RANGE = (0.8, 1.25)


def load() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_FILE.exists():
        cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    if not cfg["api_key"]:
        cfg["api_key"] = "sk-local-" + secrets.token_urlsafe(24)
        save(cfg)
    return cfg


def save(cfg: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    tmp.replace(CONFIG_FILE)


def installed_models(cfg: dict) -> list[str]:
    models_dir = Path(cfg["models_dir"])
    return [key for key in MODELS if all((models_dir / f).exists() for f in model_files(key))]


def subtitles_model(cfg: dict) -> str | None:
    """The Whisper model to use: the one chosen in Settings if it's installed, else the best installed one (turbo
    first when Whisper runs on the graphics card)."""
    installed = installed_models(cfg)
    if cfg.get("subtitles_model") in installed:
        return cfg["subtitles_model"]
    gpu = (key := whisper_gpu_engine(cfg)) and (whisper_gpu_dir(key) / WHISPER_EXE).exists()
    return next((k for k in (SUBTITLE_PREFERENCE_GPU if gpu else SUBTITLE_PREFERENCE) if k in installed), None)
