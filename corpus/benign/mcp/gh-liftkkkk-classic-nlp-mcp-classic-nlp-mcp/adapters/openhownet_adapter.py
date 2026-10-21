"""OpenHowNet adapter: sememe (义原) lookup for Chinese words.

OpenHowNet (THUNLP) is optional::

    pip install 'classic-nlp-mcp[semantic]'
"""

from __future__ import annotations

import contextlib
import sys
from typing import Any

from ..adapters.base import make_result, try_import

_OpenHowNet = try_import("OpenHowNet")

_hownet = None
if _OpenHowNet is not None:
    try:
        # OpenHowNet prints banners/warnings to stdout, which would corrupt
        # the MCP stdio JSON-RPC stream - force every print onto stderr.
        with contextlib.redirect_stdout(sys.stderr):
            _hownet = _OpenHowNet.HowNetDict()
    except Exception:
        _hownet = None


def package_available() -> bool:
    return _OpenHowNet is not None


def dict_ready() -> bool:
    return _hownet is not None


def get(lang: str) -> "OpenHowNetAdapter | None":
    if _hownet is None:
        return None
    lang = "zh" if lang == "auto" else lang
    return OpenHowNetAdapter() if lang == "zh" else None


class OpenHowNetAdapter:
    lang = "zh"

    def _require(self) -> Any:
        if _hownet is None:
            from ..adapters.base import MissingDependency

            raise MissingDependency("OpenHowNet")
        return _hownet

    def seme_lookup(self, word: str, max_senses: int = 5) -> dict[str, Any]:
        """Look up HowNet sememes (义原) for a Chinese word."""
        hnd = self._require()
        senses: list[dict[str, Any]] = []
        try:
            with contextlib.redirect_stdout(sys.stderr):
                anns = hnd.get_sememes_by_word(word)[:max_senses]
        except Exception:
            anns = []
        for ann in anns:
            entry = {
                "sense": str(ann.get("sense", "")),
                "sememes": [str(s) for s in ann.get("sememes", [])],
            }
            senses.append(entry)
        sememe_set = sorted({s for entry in senses for s in entry["sememes"]})
        return make_result(
            "seme_lookup", "zh", "OpenHowNet", getattr(_OpenHowNet, "__version__", "unknown"),
            word=word, senses=senses, sememes=sememe_set, found=bool(senses),
            note="HowNet sememes are fine-grained lexical-semantic primitives - useful for entity typing and interpretable similarity.",
        )
