"""Stanford CoreNLP adapter: the *canonical* OpenIE, served over HTTP.

Stanza (any released version) does not ship OpenIE - OpenIE lives in the
Java CoreNLP distribution.  This adapter talks to a local
`StanfordCoreNLPServer`, so there is no JVM embedding here: the user runs

    # one-time: https://stanfordnlp.github.io/CoreNLP/download.html
    java -mx4g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer \
         -port 9000 -timeout 15000

and points this server at it (env ``CORENLP_URL``, default
``http://localhost:9000``).  When the server is down the adapter degrades
gracefully and ``list_capabilities`` reports the true status.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from ..adapters.base import make_result

SERVER_URL = os.environ.get("CORENLP_URL", "http://localhost:9000")
_TIMEOUT = float(os.environ.get("CORENLP_TIMEOUT", "30"))
_PROBE_CACHE: dict[str, bool] = {}


def package_available() -> bool:
    """True when a CoreNLP server answers on CORENLP_URL right now."""
    lang = "probe"
    if lang in _PROBE_CACHE:
        return _PROBE_CACHE[lang]
    ok = False
    try:
        with urllib.request.urlopen(f"{SERVER_URL}/ping", timeout=2) as resp:
            ok = resp.status == 200
    except Exception:
        ok = False
    _PROBE_CACHE[lang] = ok
    return ok


def reset_probe() -> None:
    _PROBE_CACHE.clear()


def setup_hint() -> str:
    return (
        "Stanford CoreNLP server not reachable at "
        f"{SERVER_URL}. Download CoreNLP from "
        "https://stanfordnlp.github.io/CoreNLP/download.html and start it: "
        'java -mx4g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer '
        "-port 9000 -timeout 15000  (or set CORENLP_URL to a running server)."
    )


def get(lang: str):
    """CoreNLP OpenIE is English-focused; require a live server."""
    if lang not in ("en",) or not package_available():
        return None
    return CoreNLPAdapter()


class CoreNLPAdapter:
    lang = "en"

    def _require(self) -> None:
        if not package_available():
            raise RuntimeError(setup_hint())

    def _annotate(self, text: str, annotators: str) -> dict[str, Any]:
        self._require()
        from urllib.parse import quote

        props = quote(json.dumps({"annotators": annotators, "outputFormat": "json"}))
        # properties go in the query string; the POST body is the raw text.
        # (POSTing properties as a JSON body makes the server treat the JSON
        # itself as input text under its default inputFormat=text.)
        req = urllib.request.Request(
            f"{SERVER_URL}/?properties={props}",
            data=text.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def openie_triples(self, text: str) -> dict[str, Any]:
        """The canonical Stanford OpenIE (CoreNLP rules over neural-free
        deterministic pipeline: tokenize,ssplit,pos,lemma,ner,depparse,openie)."""
        payload = self._annotate(
            text, "tokenize,ssplit,pos,lemma,ner,depparse,openie"
        )
        triples: list[dict[str, Any]] = []
        for sent in payload.get("sentences", []):
            toks = sent.get("tokens", [])
            for rel in sent.get("openie", []):
                span = self._span(toks, rel.get("subjectSpan"), rel.get("objectSpan"))
                triples.append(
                    {
                        "subject": rel.get("subject", ""),
                        "predicate": rel.get("relation", ""),
                        "object": rel.get("object", ""),
                        "confidence": round(float(rel.get("probability", 0.5)), 3),
                        "span": span,
                        "sentence": sent.get("text", ""),
                        "engine": "stanford-corenlp-openie",
                    }
                )
        return make_result(
            "openie_triples", self.lang, "stanford-corenlp-openie", "CoreNLP-server",
            triples=triples, supported=True,
            note="Canonical Stanford CoreNLP OpenIE via local server - the "
                 "reference implementation of OpenIE.",
        )

    @staticmethod
    def _span(toks: list[dict], subj_span, obj_span) -> dict[str, int]:
        """Convert CoreNLP token-index spans [begin, end) to char offsets."""
        try:
            if toks and subj_span and obj_span:
                b = min(int(subj_span[0]), int(obj_span[0]))
                e = max(int(subj_span[1]), int(obj_span[1]))
                first, last = toks[b], toks[e - 1]
                return {
                    "start": int(first["characterOffsetBegin"]),
                    "end": int(last["characterOffsetEnd"]),
                }
        except Exception:
            pass
        return {"start": 0, "end": 0}
