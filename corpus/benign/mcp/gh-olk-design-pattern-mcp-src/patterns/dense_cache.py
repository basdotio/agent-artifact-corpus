"""Precomputed dense-embedding cache (§2.2): manifest + vectors + two-layer fingerprint.

The cache lets a normal cold start pay one probe HTTP request instead of 55 sequential
TEI ``/v1/embeddings`` calls. Two independent guards decide whether to reuse a cache entry:

1. **Metadata fingerprint** — ``names`` ordering, ``corpus_sha256``, ``embedder_model``,
   ``text_instruction_sha256``, and (when the caller declares an identity) ``model_repo``
   / ``onnx_variant``. A mismatch means the catalog or the model moved.
2. **Semantic probe** — a stored probe vector must match a fresh embedding of the same
   probe text at cosine ≥ ``dense_cache.probe_min_cosine``. Catches a model swap that
   leaves the metadata identical.

Either guard failing yields ``cache-miss:<reason>``; in ``mode=require`` the failure
raises ``DesignPatternError(ERR_008)``. The cache is OFF by default for ``--health``
(``OfflineHashEmbedder``) and ON by default for the serving path; ``mode=off`` skips
the cache read entirely. A miss with ``mode=auto`` re-embeds and overwrites the cache
when ``write`` is enabled.

The cache builder (``python -m src.patterns.dense_cache build --out /out``) writes
``vectors.npy`` first and ``manifest.json`` second so a partial run never leaves a
manifest pointing at missing data.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import logging
import math
import os
import sys
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import numpy as np
from pydantic import BaseModel

from src.config import ConfigManager, DenseCacheConfig, EmbedderConfig, ServerConfig
from src.errors import ERROR_RETRIEVAL_UNAVAILABLE, DesignPatternError
from src.patterns.embedder import (
    EmbedderIdentity,
    EmbedderProtocol,
    build_embedder,
    embedder_identity,
    l2_normalize_rows,
)
from src.patterns.loader import load_catalog

logger = logging.getLogger(__name__)

CACHE_SCHEMA_VERSION = 1
MANIFEST_NAME = "manifest.json"
VECTORS_NAME = "vectors.npy"

PROBE_TEXT = "Cache probe: bound the latency of a synchronous call in a concurrent pipeline"

#: Tolerance for the on-disk row-norm check; FAISS IndexFlatIP needs unit vectors.
UNIT_NORM_TOLERANCE = 1e-3

#: Build/CLI tooling version — surfaces in the manifest for audit, never gates acceptance.
BUILDER_VERSION = "1.0"


@dataclass(frozen=True)
class _Reason:
    """A typed status label returned alongside the resolved vectors."""

    label: str


class DenseCacheManifest(BaseModel):
    """On-disk manifest of one dense-vector cache (extra keys rejected)."""

    schema_version: int
    created_at: str  # UTC ISO-8601, informational
    record_count: int
    dimension: int
    names_sha256: str
    corpus_sha256: str
    embedder_model: str
    text_instruction_sha256: str
    model_repo: str = ""
    onnx_variant: str = ""
    tei_model_id: str = ""  # from TEI /info when reachable, informational
    tei_dtype: str = ""
    probe_text: str
    probe_vector: list[float]
    builder_version: str

    model_config = {"extra": "forbid"}


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def names_digest(names: Sequence[str]) -> str:
    """Canonical-name order digest (matches the catalog iteration order, §2.2)."""
    return _sha256_hex("\n".join(names).encode("utf-8"))


def corpus_digest(names: Sequence[str], doc_texts: Sequence[str]) -> str:
    """Per-record digest over (canonical-name × 0x1F × document_text), NUL-joined."""
    return _sha256_hex(
        "\x00".join(f"{name}\x1f{text}" for name, text in zip(names, doc_texts, strict=True)).encode("utf-8")
    )


def instruction_digest(text: str) -> str:
    """SHA-256 of the configured ``text_instruction`` (exact bytes)."""
    return _sha256_hex(text.encode("utf-8"))


def probe_cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity; returns 0.0 when either vector has zero norm or lengths differ."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = 0.0
    sum_a = 0.0
    sum_b = 0.0
    for x, y in zip(a, b, strict=True):
        dot += x * y
        sum_a += x * x
        sum_b += y * y
    if sum_a <= 0.0 or sum_b <= 0.0:
        return 0.0
    return dot / math.sqrt(sum_a * sum_b)


def _read_text(path: Path) -> tuple[str | None, str | None]:
    """Read a UTF-8 text file; return (text, None) or (None, reason)."""
    try:
        return path.read_text(encoding="utf-8"), None
    except FileNotFoundError:
        return None, "absent"
    except OSError as exc:
        logger.warning("Dense cache file unreadable: %s (%s)", path, exc)
        return None, "unreadable"


def load_manifest(cache_dir: Path) -> tuple[DenseCacheManifest | None, str]:
    """Parse ``manifest.json``; return (manifest, "ok") or (None, reason)."""
    path = cache_dir / MANIFEST_NAME
    text, read_reason = _read_text(path)
    if text is None:
        reason = "manifest-absent" if read_reason == "absent" else "manifest-unreadable"
        return None, reason
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("Dense cache manifest is not valid JSON: %s (%s)", path, exc)
        return None, "manifest-unreadable"
    try:
        manifest = DenseCacheManifest.model_validate(data)
    except Exception as exc:  # pydantic.ValidationError is the expected subclass
        logger.warning("Dense cache manifest failed validation: %s (%s)", path, exc)
        return None, "manifest-unreadable"
    if manifest.schema_version != CACHE_SCHEMA_VERSION:
        logger.warning(
            "Dense cache schema_version mismatch: got %d, expected %d",
            manifest.schema_version,
            CACHE_SCHEMA_VERSION,
        )
        return None, "schema-version"
    return manifest, "ok"


def load_vectors(
    cache_dir: Path, manifest: DenseCacheManifest
) -> tuple[list[list[float]] | None, str]:
    """Load ``vectors.npy`` and validate shape + unit norm; (vectors, "ok") or (None, reason)."""
    path = cache_dir / VECTORS_NAME
    if not path.exists():
        return None, "vectors-absent"
    try:
        matrix = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        logger.warning("Dense cache vectors unreadable: %s (%s)", path, exc)
        return None, "vectors-unreadable"
    if matrix.ndim != 2 or matrix.shape != (manifest.record_count, manifest.dimension):
        logger.warning(
            "Dense cache vectors shape mismatch: got %s, expected (%d, %d)",
            matrix.shape,
            manifest.record_count,
            manifest.dimension,
        )
        return None, "vectors-shape"
    if not np.all(np.isfinite(matrix)):
        logger.warning("Dense cache vectors contain non-finite values")
        return None, "vectors-nonfinite"
    norms = np.linalg.norm(matrix, axis=1)
    if np.any(np.abs(norms - 1.0) > UNIT_NORM_TOLERANCE):
        logger.warning(
            "Dense cache vectors are not unit-normalized (min %.6f, max %.6f)",
            float(norms.min()),
            float(norms.max()),
        )
        return None, "vectors-norm"
    return cast("list[list[float]]", matrix.astype(np.float32, copy=False).tolist()), "ok"


def _atomic_write_bytes(path: Path, payload: bytes) -> str | None:
    """Write ``payload`` to ``path`` via a sibling tmp file + ``os.replace``; None=ok."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp, "wb") as fh:
            fh.write(payload)
        os.replace(tmp, path)
    except OSError as exc:
        logger.warning("Dense cache write failed: %s (%s)", path, exc)
        return f"write-error:{exc.__class__.__name__}"
    return None


def store_cache(
    cache_dir: Path,
    manifest: DenseCacheManifest,
    vectors: Sequence[Sequence[float]],
) -> str | None:
    """Write vectors first, then manifest, both atomically; None=ok or reason string."""
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("Dense cache directory create failed: %s (%s)", cache_dir, exc)
        return f"mkdir-error:{exc.__class__.__name__}"
    array = np.asarray(vectors, dtype=np.float32)
    buf = io.BytesIO()
    np.save(buf, array, allow_pickle=False)
    reason = _atomic_write_bytes(cache_dir / VECTORS_NAME, buf.getvalue())
    if reason is not None:
        return reason
    manifest_blob = manifest.model_dump_json(indent=2).encode("utf-8")
    return _atomic_write_bytes(cache_dir / MANIFEST_NAME, manifest_blob)


def build_manifest(
    *,
    names: Sequence[str],
    doc_texts: Sequence[str],
    identity: EmbedderIdentity,
    dimension: int,
    probe_vector: Sequence[float],
    tei_info: dict[str, str],
) -> DenseCacheManifest:
    """Assemble a manifest from the just-embedded corpus and probe (no I/O)."""
    return DenseCacheManifest(
        schema_version=CACHE_SCHEMA_VERSION,
        created_at=datetime.now(UTC).isoformat(),
        record_count=len(names),
        dimension=dimension,
        names_sha256=names_digest(names),
        corpus_sha256=corpus_digest(names, doc_texts),
        embedder_model=identity.model,
        text_instruction_sha256=instruction_digest(identity.text_instruction),
        model_repo=identity.model_repo,
        onnx_variant=identity.onnx_variant,
        tei_model_id=tei_info.get("model_id", ""),
        tei_dtype=tei_info.get("model_dtype", ""),
        probe_text=PROBE_TEXT,
        probe_vector=list(probe_vector),
        builder_version=BUILDER_VERSION,
    )


def _metadata_fingerprint_match(  # noqa: PLR0911 - one return per mismatch reason; readability wins
    manifest: DenseCacheManifest, identity: EmbedderIdentity, names: Sequence[str]
) -> str | None:
    """Return None if the metadata fingerprint matches; else ``cache-miss:<reason>``."""
    if manifest.record_count != len(names):
        return f"cache-miss:record-count-{manifest.record_count}-vs-{len(names)}"
    if manifest.names_sha256 != names_digest(names):
        return "cache-miss:names-sha256"
    if manifest.embedder_model != identity.model:
        return f"cache-miss:embedder-model-{manifest.embedder_model!r}"
    if manifest.text_instruction_sha256 != instruction_digest(identity.text_instruction):
        return "cache-miss:text-instruction"
    if identity.model_repo and manifest.model_repo != identity.model_repo:
        return "cache-miss:model-repo"
    if identity.onnx_variant and manifest.onnx_variant != identity.onnx_variant:
        return "cache-miss:onnx-variant"
    # corpus_sha256 is the second-tier guard: any document_text edit shifts the
    # digest even when name ordering and identity are unchanged. Listed last so
    # the cheaper checks short-circuit first.
    return None  # corpus_sha256 check uses the caller-supplied doc_texts; see resolve_dense_vectors


def _corpus_fingerprint_match(
    manifest: DenseCacheManifest, names: Sequence[str], doc_texts: Sequence[str]
) -> bool:
    """True iff ``manifest.corpus_sha256 == corpus_digest(names, doc_texts)``."""
    return manifest.corpus_sha256 == corpus_digest(names, doc_texts)


async def _probe_embed(
    embedder: EmbedderProtocol, text: str, timeout_seconds: float
) -> list[float]:
    """Embed ``text`` with a hard timeout; raises ``asyncio.TimeoutError`` on overrun."""
    return (
        await asyncio.wait_for(
            embedder.embed_documents([text]), timeout=timeout_seconds
        )
    )[0]


def _tei_info_url(embedder_config: EmbedderConfig) -> str:
    """Derive the TEI ``/info`` URL by stripping a trailing ``/v1`` from ``base_url``."""
    base = embedder_config.config.base_url.rstrip("/")
    if base.endswith("/v1"):
        base = base[: -len("/v1")]
    return base.rstrip("/") + "/info"


def _fetch_tei_info(url: str, timeout_seconds: float = 5.0) -> dict[str, str]:
    """Fetch TEI ``/info`` JSON; return ``{}`` on any error (informational, never fatal)."""
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logger.info("TEI /info probe failed (%s): %s", url, exc)
        return {}
    if not isinstance(payload, dict):
        return {}
    out: dict[str, str] = {}
    model_id = payload.get("model_id")
    if isinstance(model_id, str):
        out["model_id"] = model_id
    model_dtype = payload.get("model_dtype")
    if isinstance(model_dtype, str):
        out["model_dtype"] = model_dtype
    return out


def _resolve_tei_info(embedder: EmbedderProtocol) -> dict[str, str]:
    """Best-effort TEI /info lookup using the embedder's stashed config (if any)."""
    config = getattr(embedder, "_config", None)
    if not isinstance(config, EmbedderConfig):
        return {}
    return _fetch_tei_info(_tei_info_url(config))


async def _embed_and_maybe_store(
    *,
    config: DenseCacheConfig,
    embedder: EmbedderProtocol,
    names: Sequence[str],
    doc_texts: Sequence[str],
    identity: EmbedderIdentity,
    miss_reason: str | None = None,
) -> tuple[list[list[float]], str]:
    """Re-embed the corpus (and the probe), optionally store the cache, return vectors."""
    if miss_reason is not None:
        logger.info("Dense cache miss", extra={"reason": miss_reason})
    vectors = await embedder.embed_documents(list(doc_texts))
    if config.write:
        probe_vector = (await embedder.embed_documents([PROBE_TEXT]))[0]
        manifest = build_manifest(
            names=names,
            doc_texts=doc_texts,
            identity=identity,
            dimension=len(vectors[0]) if vectors else 0,
            probe_vector=probe_vector,
            tei_info=_resolve_tei_info(embedder),
        )
        store_reason = store_cache(Path(config.path), manifest, vectors)
        if store_reason is not None:
            logger.warning(
                "Dense cache write failed",
                extra={"path": config.path, "reason": store_reason},
            )
    return vectors, "embedded"


async def resolve_dense_vectors(  # noqa: PLR0911, PLR0912 - one branch per guard keeps the gate contract obvious
    *,
    config: DenseCacheConfig,
    embedder: EmbedderProtocol,
    names: Sequence[str],
    doc_texts: Sequence[str],
    identity: EmbedderIdentity,
) -> tuple[list[list[float]], str]:
    """Cache-aware loader for the dense-leg corpus (returns vectors and a status label)."""
    if config.mode == "off":
        return await embedder.embed_documents(list(doc_texts)), "disabled"

    cache_dir = Path(config.path)
    manifest, manifest_reason = load_manifest(cache_dir)
    if manifest is None:
        if config.mode == "require":
            raise DesignPatternError(
                ERROR_RETRIEVAL_UNAVAILABLE,
                f"dense cache required but unusable ({manifest_reason})",
                hint="run `make embed-cache` (or set DESIGN_PATTERN_DENSE_CACHE_MODE=auto)",
            )
        return await _embed_and_maybe_store(
            config=config,
            embedder=embedder,
            names=names,
            doc_texts=doc_texts,
            identity=identity,
            miss_reason=f"cache-miss:{manifest_reason}",
        )

    mismatch = _metadata_fingerprint_match(manifest, identity, names)
    if mismatch is not None:
        if config.mode == "require":
            raise DesignPatternError(
                ERROR_RETRIEVAL_UNAVAILABLE,
                f"dense cache fingerprint mismatch ({mismatch})",
                hint="rebuild with `make embed-cache`",
            )
        return await _embed_and_maybe_store(
            config=config,
            embedder=embedder,
            names=names,
            doc_texts=doc_texts,
            identity=identity,
            miss_reason=mismatch,
        )

    if not _corpus_fingerprint_match(manifest, names, doc_texts):
        corpus_reason = "cache-miss:corpus-sha256"
        if config.mode == "require":
            raise DesignPatternError(
                ERROR_RETRIEVAL_UNAVAILABLE,
                f"dense cache fingerprint mismatch ({corpus_reason})",
                hint="rebuild with `make embed-cache`",
            )
        return await _embed_and_maybe_store(
            config=config,
            embedder=embedder,
            names=names,
            doc_texts=doc_texts,
            identity=identity,
            miss_reason=corpus_reason,
        )

    try:
        probe_vector = await _probe_embed(
            embedder, manifest.probe_text, config.probe_timeout_seconds
        )
    except (TimeoutError, OSError) as exc:
        if config.mode == "require":
            raise DesignPatternError(
                ERROR_RETRIEVAL_UNAVAILABLE,
                f"dense cache probe unreachable ({exc.__class__.__name__})",
                hint="rebuild with `make embed-cache`",
            ) from exc
        return await _embed_and_maybe_store(
            config=config,
            embedder=embedder,
            names=names,
            doc_texts=doc_texts,
            identity=identity,
            miss_reason="cache-miss:probe-unreachable",
        )

    cosine = probe_cosine(probe_vector, manifest.probe_vector)
    if cosine < config.probe_min_cosine:
        if config.mode == "require":
            raise DesignPatternError(
                ERROR_RETRIEVAL_UNAVAILABLE,
                "dense cache embedding space mismatch",
                hint="rebuild with `make embed-cache`",
            )
        return await _embed_and_maybe_store(
            config=config,
            embedder=embedder,
            names=names,
            doc_texts=doc_texts,
            identity=identity,
            miss_reason=f"cache-miss:probe-cosine-{cosine:.4f}",
        )

    vectors, vector_reason = load_vectors(cache_dir, manifest)
    if vectors is None:
        if config.mode == "require":
            raise DesignPatternError(
                ERROR_RETRIEVAL_UNAVAILABLE,
                f"dense cache vectors unusable ({vector_reason})",
                hint="rebuild with `make embed-cache`",
            )
        return await _embed_and_maybe_store(
            config=config,
            embedder=embedder,
            names=names,
            doc_texts=doc_texts,
            identity=identity,
            miss_reason=f"cache-miss:{vector_reason}",
        )
    return vectors, "cache-hit"


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: ``python -m src.patterns.dense_cache build --out <dir>``."""
    parser = argparse.ArgumentParser(
        prog="python -m src.patterns.dense_cache",
        description="Precompute the dense-embedding cache for design-pattern-mcp.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    build_cmd = sub.add_parser(
        "build", help="Embed the catalog and write the cache directory."
    )
    build_cmd.add_argument("--out", required=True, help="Output directory (e.g. data/dense-cache).")
    build_cmd.add_argument(
        "--config",
        default=ConfigManager.DEFAULT_CONFIG_PATH,
        help="Path to the server config JSON (default: config/config.json).",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command != "build":
        parser.error(f"unknown command: {args.command}")

    try:
        raw = ConfigManager.load_config(args.config)
        server_config = ServerConfig.model_validate(raw)
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"dense cache build failed: {exc}", file=sys.stderr)
        return 1
    embedder_config = server_config.embedder
    pattern_dir = Path(server_config.paths.pattern_directory)
    docs_dir = Path(server_config.paths.docs_directory)
    identity = embedder_identity(embedder_config)

    cache_dir = Path(args.out)
    catalog = load_catalog(pattern_dir, docs_dir)
    names = tuple(catalog.records)
    doc_texts = tuple(catalog.records[name].document_text for name in names)

    async def _run() -> tuple[list[list[float]], list[float]]:
        embedder = build_embedder(embedder_config)
        vectors = await embedder.embed_documents(list(doc_texts))
        normalized = await asyncio.to_thread(l2_normalize_rows, vectors)
        probe_vector = (await embedder.embed_documents([PROBE_TEXT]))[0]
        return normalized, probe_vector

    try:
        normalized, probe_vector = asyncio.run(_run())
    except Exception as exc:
        print(f"dense cache build failed: {exc}", file=sys.stderr)
        return 1

    dimension = len(normalized[0]) if normalized else 0
    manifest = build_manifest(
        names=names,
        doc_texts=doc_texts,
        identity=identity,
        dimension=dimension,
        probe_vector=probe_vector,
        tei_info=_fetch_tei_info(_tei_info_url(embedder_config)),
    )
    reason = store_cache(cache_dir, manifest, normalized)
    if reason is not None:
        print(f"dense cache write failed: {reason}", file=sys.stderr)
        return 1
    cosine = probe_cosine(probe_vector, manifest.probe_vector)
    digest_preview = manifest.corpus_sha256[:12]
    print(
        f"dense cache written: {len(names)} vectors, dim {dimension}, "
        f"corpus {digest_preview}, probe self-cosine {cosine:.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
