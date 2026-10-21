"""Shared plumbing for engine adapters: lazy imports, capability registry,
language detection and the unified output schema.

Design rule of the whole project: **wrap capabilities, not libraries**.
An adapter exposes stable capability functions (``tokenize``, ``pos_tag``,
``ner``, ...) backed by whichever classical NLP library is installed.  All
optional dependencies degrade gracefully with actionable install hints.
"""

from __future__ import annotations

import importlib
import re
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def detect_lang(text: str) -> str:
    """Return ``"zh"`` or ``"en"``.  CJK-dominant text is treated as Chinese."""
    if not text:
        return "en"
    cjk = len(_CJK_RE.findall(text))
    return "zh" if cjk >= max(1, int(0.3 * len(text.strip()))) else "en"


# ---------------------------------------------------------------------------
# Optional dependency handling
# ---------------------------------------------------------------------------

# Extra hints per optional package.  Everything except jieba is optional.
INSTALL_HINTS: dict[str, str] = {
    "spacy": (
        "spaCy is not installed. Chinese-first: `pip install 'classic-nlp-mcp[zh]'` "
        "then `python -m spacy download zh_core_web_sm` for statistical Chinese NER; "
        "English: `pip install 'classic-nlp-mcp[en]'` then `python -m spacy download en_core_web_sm`."
    ),
    "nltk": (
        "NLTK is not installed. Install with: "
        "`pip install 'classic-nlp-mcp[semantic]'` then `python -c \"import nltk; nltk.download('wordnet')\"`."
    ),
    "OpenHowNet": (
        "OpenHowNet is not installed. Install with: "
        "`pip install 'classic-nlp-mcp[semantic]'` (the sememe dictionary ships with the package)."
    ),
    "stanza": (
        "Stanza (Stanford NLP) is not installed or its models for this language are missing. Install with: "
        "`pip install 'classic-nlp-mcp[stanford]'` then download models, e.g. "
        "`python -c \"import stanza; stanza.download('en', processors='tokenize,pos,lemma,ner,depparse,openie,constituency')\"`."
    ),
}


class MissingDependency(RuntimeError):
    """Raised when a capability needs an optional library that is absent."""

    def __init__(self, package: str):
        self.package = package
        super().__init__(INSTALL_HINTS.get(package, f"Optional dependency '{package}' is not installed."))


def optional_import(package: str) -> Any:
    """Import an optional package or raise :class:`MissingDependency`."""
    try:
        return importlib.import_module(package)
    except ImportError as exc:  # pragma: no cover - depends on env
        raise MissingDependency(package) from exc


def try_import(package: str) -> Any | None:
    """Import an optional package, returning ``None`` when unavailable."""
    try:
        return importlib.import_module(package)
    except Exception:
        return None


def module_version(module: Any) -> str:
    return str(getattr(module, "__version__", "unknown"))


# ---------------------------------------------------------------------------
# Unified output schema
# ---------------------------------------------------------------------------


def make_result(tool: str, lang: str, engine: str, engine_version: str, **fields: Any) -> dict[str, Any]:
    """Build the unified result envelope shared by every tool.

    Every tool returns the same skeleton so that LLM agents can parse any
    response without special-casing::

        {"tool": ..., "lang": ..., "engine": ..., "engine_version": ..., ...fields}
    """
    out: dict[str, Any] = {
        "tool": tool,
        "lang": lang,
        "engine": engine,
        "engine_version": engine_version,
    }
    out.update(fields)
    return out


def make_token(text: str, start: int, end: int, pos: str | None = None, ner: str | None = None) -> dict[str, Any]:
    tok: dict[str, Any] = {"text": text, "start": start, "end": end}
    if pos is not None:
        tok["pos"] = pos
    if ner is not None:
        tok["ner"] = ner
    return tok


# ---------------------------------------------------------------------------
# Adapter registry
# ---------------------------------------------------------------------------

AdapterFn = Callable[..., dict[str, Any]]


class AdapterRegistry:
    """Lazily loaded, per-language capability adapters.

    Each adapter module exposes a ``get(lang)`` factory returning an object
    with capability methods, or ``None`` when its dependencies are missing.
    The registry is the single place that knows which engines exist, so
    ``list_capabilities`` stays honest.
    """

    _ADAPTER_MODULES = (
        ("spacy", "classic_nlp_mcp.adapters.spacy_adapter"),
        ("jieba", "classic_nlp_mcp.adapters.jieba_adapter"),
        ("nltk", "classic_nlp_mcp.adapters.nltk_adapter"),
        ("openhownet", "classic_nlp_mcp.adapters.openhownet_adapter"),
        ("stanza", "classic_nlp_mcp.adapters.stanza_adapter"),
        ("corenlp", "classic_nlp_mcp.adapters.corenlp_adapter"),
    )

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}

    def get(self, engine: str, lang: str) -> Any | None:
        """Return the adapter instance for (engine, lang), or None."""
        key = f"{engine}:{lang}"
        if key in self._cache:
            return self._cache[key]
        instance = None
        for name, module_name in self._ADAPTER_MODULES:
            if name != engine:
                continue
            module = try_import(module_name)
            if module is not None and hasattr(module, "get"):
                instance = module.get(lang)
            break
        self._cache[key] = instance
        return instance

    def engine_available(self, engine: str) -> bool:
        """True when the engine's *package* is importable (any language)."""
        module = try_import(f"classic_nlp_mcp.adapters.{engine}_adapter")
        if module is None:
            return False
        probe = getattr(module, "package_available", None)
        return probe() if callable(probe) else True

    def reset(self) -> None:
        self._cache.clear()


REGISTRY = AdapterRegistry()
