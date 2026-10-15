"""Embedding engine: resolves/downloads the pinned model, runs it with ONNX Runtime, or uses the test embedder.

No PyTorch. The same ONNX model and tokenizer.json are used by the TypeScript implementation, so an index built by
one implementation is queryable by the other. `test-hash` is a deterministic, dependency-light embedder for tests.
"""

from __future__ import annotations

import hashlib
import os
import re
import threading
import urllib.request
from pathlib import Path
from typing import Any

from ..config import Config
from ..core.errors import StaticSightError
from ..shared import shared_json

HF_ENDPOINT_DEFAULT = "https://huggingface.co"


class SemanticUnavailable(StaticSightError):
    title = "Semantic search is not available"


def model_spec(name: str) -> dict[str, Any]:
    models = shared_json("semantic/models.json")["models"]
    if name not in models:
        raise SemanticUnavailable(
            f"Unknown embedding model `{name}`.", f"Use one of: {', '.join(sorted(models))} (STATICSIGHT_EMBED_MODEL)."
        )
    return models[name]


def model_id(cfg: Config) -> str:
    """Identity stored in the index; changing it triggers a rebuild."""
    if cfg.embed_model_dir:
        return "custom:" + Path(cfg.embed_model_dir).name
    spec = model_spec(cfg.embed_model)
    return f"{cfg.embed_model}@{spec.get('revision', 'builtin')}"


# ----------------------------------------------------------------------------- test embedder
_IDENT = re.compile(r"[A-Za-z0-9_]+")
_SUBWORD = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")


def _ascii_lower(s: str) -> str:
    return "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in s)


def hash_tokens(text: str) -> list[str]:
    out: list[str] = []
    for ident in _IDENT.findall(text):
        for part in ident.split("_"):
            out.extend(_ascii_lower(p) for p in _SUBWORD.findall(part))
    return out


def fnv1a32(data: bytes) -> int:
    h = 0x811C9DC5
    for b in data:
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


class HashEmbedder:
    """Deterministic bag-of-subwords embedder (tests only): identical output in Python and TypeScript."""

    name = "test-hash"

    def __init__(self, dims: int = 256):
        self.dims = dims

    def embed(self, texts: list[str]):
        import numpy as np

        out = np.zeros((len(texts), self.dims), dtype=np.float64)
        for i, t in enumerate(texts):
            for tok in hash_tokens(t):
                h = fnv1a32(tok.encode("utf-8"))
                out[i, h % self.dims] += -1.0 if (h >> 8) & 1 else 1.0
        norms = np.sqrt((out * out).sum(axis=1, keepdims=True))
        norms[norms == 0] = 1.0
        return (out / norms).astype(np.float32)


# ----------------------------------------------------------------------------- model files
def model_dir(cfg: Config) -> Path:
    if cfg.embed_model_dir:
        return Path(cfg.embed_model_dir).expanduser()
    spec = model_spec(cfg.embed_model)
    return cfg.cache_dir / "models" / cfg.embed_model / spec["revision"]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


_verified: set[str] = set()


def missing_model_files(cfg: Config) -> list[str]:
    """Files that are absent or fail their pinned sha256 (custom model dirs are only checked for presence)."""
    d = model_dir(cfg)
    if cfg.embed_model_dir:
        need = ["tokenizer.json"]
        onnx = [p for p in ("onnx/model_quantized.onnx", "onnx/model.onnx", "model.onnx") if (d / p).is_file()]
        return [f for f in need if not (d / f).is_file()] + ([] if onnx else ["onnx/model.onnx"])
    spec = model_spec(cfg.embed_model)
    bad = []
    for rel, sha in spec["files"].items():
        p = d / rel
        key = f"{p}:{sha}"
        if key in _verified:
            continue
        if not p.is_file() or _sha256(p) != sha:
            bad.append(rel)
        else:
            _verified.add(key)
    return bad


def download_model(cfg: Config, progress=None) -> Path:
    """Download the pinned model files into the cache (sha256-verified, atomic). Honours HTTPS_PROXY and HF_ENDPOINT."""
    if cfg.embed_model_dir:
        raise SemanticUnavailable(
            f"Model files are missing in STATICSIGHT_EMBED_MODEL_DIR (`{cfg.embed_model_dir}`).",
            "Copy tokenizer.json and the ONNX model there, or unset the variable to use the pinned download.",
        )
    spec = model_spec(cfg.embed_model)
    if "repo" not in spec:
        return model_dir(cfg)
    if not cfg.semantic_allow_download:
        raise SemanticUnavailable(
            f"The embedding model `{spec['repo']}` is not downloaded and downloads are disabled.",
            f"Run `staticsight model download` on a connected machine and copy `{model_dir(cfg)}`, or set "
            "STATICSIGHT_EMBED_MODEL_DIR to a pre-downloaded copy.",
        )
    d = model_dir(cfg)
    endpoint = os.environ.get("HF_ENDPOINT", HF_ENDPOINT_DEFAULT).rstrip("/")
    for rel in missing_model_files(cfg):
        url = f"{endpoint}/{spec['repo']}/resolve/{spec['revision']}/{rel}"
        dest = d / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".part")
        if progress:
            progress(f"downloading {rel}")
        try:
            with urllib.request.urlopen(url, timeout=60) as resp, open(tmp, "wb") as out:
                while True:
                    block = resp.read(1 << 20)
                    if not block:
                        break
                    out.write(block)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise SemanticUnavailable(
                f"Could not download `{url}`: {exc}",
                "Check network/proxy (HTTPS_PROXY) or HF_ENDPOINT, or pre-download with STATICSIGHT_EMBED_MODEL_DIR.",
            ) from exc
        got = _sha256(tmp)
        if got != spec["files"][rel]:
            tmp.unlink(missing_ok=True)
            raise SemanticUnavailable(f"Checksum mismatch for `{rel}` (got {got[:12]}…); the download was discarded.")
        os.replace(tmp, dest)
    return d


# ----------------------------------------------------------------------------- ONNX embedder
class OnnxEmbedder:
    def __init__(self, cfg: Config, directory: Path, max_tokens: int, pooling: str):
        try:
            import numpy  # noqa: F401
            from tokenizers import Tokenizer

            ort = _import_onnxruntime()
        except ImportError as exc:
            raise SemanticUnavailable(
                f"Python packages for semantic search are missing ({exc.name}).",
                'Install them (onnxruntime, tokenizers, numpy) with `python3 staticsight.py --install --semantic` from the StaticSight clone, or `pip install -r requirements-semantic.txt`.',
            ) from exc
        ort.set_default_logger_severity(3)
        onnx = next(
            directory / p for p in ("onnx/model_quantized.onnx", "onnx/model.onnx", "model.onnx") if (directory / p).is_file()
        )
        so = ort.SessionOptions()
        so.log_severity_level = 3
        if cfg.embed_threads:
            so.intra_op_num_threads = cfg.embed_threads
        self.session = ort.InferenceSession(str(onnx), so, providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.session.get_inputs()}
        self.tokenizer = Tokenizer.from_file(str(directory / "tokenizer.json"))
        self.tokenizer.no_padding()
        self.tokenizer.no_truncation()
        self.max_tokens = max_tokens
        self.pooling = pooling
        self.batch = cfg.embed_batch
        self.name = model_id(cfg)
        self.dims = int(self.session.get_outputs()[0].shape[-1])
        self._lock = threading.Lock()

    def embed(self, texts: list[str]):
        import numpy as np

        encs = self.tokenizer.encode_batch(texts)
        ids_list = [e.ids[: self.max_tokens] if self.max_tokens else e.ids for e in encs]
        out = np.zeros((len(texts), self.dims), dtype=np.float32)
        order = sorted(range(len(texts)), key=lambda i: len(ids_list[i]))  # length-sorted batches: little padding
        for s in range(0, len(order), self.batch):
            idx = order[s : s + self.batch]
            width = max(1, max(len(ids_list[i]) for i in idx))
            ids = np.zeros((len(idx), width), dtype=np.int64)
            mask = np.zeros((len(idx), width), dtype=np.int64)
            for r, i in enumerate(idx):
                row = ids_list[i]
                ids[r, : len(row)] = row
                mask[r, : len(row)] = 1
            feeds = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in self.inputs:
                feeds["token_type_ids"] = np.zeros_like(ids)
            with self._lock:
                hidden = self.session.run(None, feeds)[0]
            if self.pooling == "cls":
                vec = hidden[:, 0, :]
            else:
                m = mask[..., None].astype(np.float32)
                vec = (hidden * m).sum(axis=1) / np.maximum(m.sum(axis=1), 1e-9)
            norms = np.linalg.norm(vec, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            out[idx] = (vec / norms).astype(np.float32)
        return out


def _pooling_from_dir(d: Path, default: str) -> str:
    cfgp = d / "1_Pooling" / "config.json"
    if cfgp.is_file():
        import json

        c = json.loads(cfgp.read_text(encoding="utf-8"))
        if c.get("pooling_mode_cls_token"):
            return "cls"
        if c.get("pooling_mode_mean_tokens"):
            return "mean"
    return default


_embedders: dict[str, Any] = {}
_embedders_lock = threading.Lock()


def get_embedder(cfg: Config, allow_download: bool = True, progress=None):
    """Cached embedder for the configured model (downloads the pinned model on first use when allowed)."""
    key = f"{cfg.embed_model}|{cfg.embed_model_dir}|{cfg.cache_dir}"
    with _embedders_lock:
        if key in _embedders:
            return _embedders[key]
    if not cfg.embed_model_dir and cfg.embed_model == "test-hash":
        emb: Any = HashEmbedder(model_spec("test-hash")["dims"])
    else:
        dependencies_ok()
        if missing_model_files(cfg):
            if not allow_download:
                raise SemanticUnavailable(
                    "The embedding model is not downloaded yet.",
                    "Call refresh_semantic_index (downloads it once) or run `staticsight model download`.",
                )
            download_model(cfg, progress)
            if missing_model_files(cfg):
                raise SemanticUnavailable("The embedding model files are still incomplete after download.")
        spec = {} if cfg.embed_model_dir else model_spec(cfg.embed_model)
        d = model_dir(cfg)
        emb = OnnxEmbedder(cfg, d, int(spec.get("max_tokens", 512)), _pooling_from_dir(d, spec.get("pooling", "mean")))
    with _embedders_lock:
        _embedders[key] = emb
    return emb


def _import_onnxruntime() -> Any:
    """Import onnxruntime without its import-time hardware-probe warnings (written straight to fd 2)."""
    import sys

    if "onnxruntime" in sys.modules:
        return sys.modules["onnxruntime"]
    try:
        sys.stderr.flush()
        saved = os.dup(2)
    except (OSError, ValueError):
        import onnxruntime

        return onnxruntime
    try:
        with open(os.devnull, "w") as null:
            os.dup2(null.fileno(), 2)
            import onnxruntime
    finally:
        os.dup2(saved, 2)
        os.close(saved)
    return onnxruntime


def dependencies_ok() -> None:
    import importlib.util

    missing = [m for m in ("numpy", "onnxruntime", "tokenizers") if importlib.util.find_spec(m) is None]
    if missing:
        raise SemanticUnavailable(
            f"Python packages for semantic search are missing ({missing[0]}).",
            'Install them (onnxruntime, tokenizers, numpy) with `python3 staticsight.py --install --semantic` from the StaticSight clone, or `pip install -r requirements-semantic.txt`.',
        )


def numpy_ok() -> None:
    try:
        import numpy  # noqa: F401
    except ImportError as exc:
        raise SemanticUnavailable(
            "numpy is required for semantic search.", 'Install it with `python3 staticsight.py --install --semantic` from the StaticSight clone.'
        ) from exc


def reset_embedders() -> None:
    with _embedders_lock:
        _embedders.clear()
