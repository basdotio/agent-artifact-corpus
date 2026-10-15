"""Per-language import rewriters used when materialising an extraction."""

from __future__ import annotations

from .base import BaseRewriter, ImportRewriter

__all__ = ["BaseRewriter", "ImportRewriter", "rewriter_for"]

_REWRITERS: dict[str, ImportRewriter] = {}


def _load() -> dict[str, ImportRewriter]:
    if _REWRITERS:
        return _REWRITERS
    from .python import PythonRewriter

    for r in (PythonRewriter(),):
        _REWRITERS[r.language] = r

    # Optional backends: absent ones simply mean "copy verbatim", which is a
    # safe default -- an unrewritten import fails loudly in the extracted copy.
    for module_name, attr in (
        ("javascript", "JavaScriptRewriter"),
        ("rust", "RustRewriter"),
        ("go", "GoRewriter"),
    ):
        try:
            mod = __import__(f"{__name__}.{module_name}", fromlist=[attr])
            inst = getattr(mod, attr)()
        except (ImportError, AttributeError):
            continue
        _REWRITERS[inst.language] = inst
        for alias in getattr(inst, "aliases", ()):
            _REWRITERS[alias] = inst
    return _REWRITERS


def rewriter_for(language: str | None) -> ImportRewriter | None:
    if not language:
        return None
    return _load().get(language)
