"""Local sentence embeddings for semantic search (optional).

Uses `intfloat/multilingual-e5-small` at a pinned revision, loaded only from
the local Hugging Face cache: nothing is downloaded at build or query time
(`okf-ingest fetch-model` downloads it once). Needs `torch` and
`transformers` (the `semantic` or `ingest` extra); without them, or without
the cached model, callers fall back to keyword search.
"""

import hashlib
from functools import lru_cache
from typing import Any, List, Optional

import numpy as np

MODEL_ID = "intfloat/multilingual-e5-small"
MODEL_REVISION = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
MODEL_FILES = [
    "config.json",
    "model.safetensors",
    "sentencepiece.bpe.model",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
]
DIM = 384
MAX_TOKENS = 512
BATCH = 32


class EmbeddingUnavailable(RuntimeError):
    """Raised when the model or its libraries are not installed locally."""


def passage_text(title: str, section_title: str, text: str) -> str:
    """The text embedded for a passage: its context plus its content."""
    return f"{title} | {section_title}\n{text}"


def text_hash(text: str) -> str:
    """Cache key for an embedded text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Embedder:
    """E5 encoder: mean-pooled, L2-normalized, with `query:`/`passage:` prefixes."""

    model_id = f"{MODEL_ID}@{MODEL_REVISION}"

    def __init__(self, device: Optional[str] = None):
        """Load the tokenizer and model from the local cache only.

        Raises:
            EmbeddingUnavailable: If torch/transformers or the cached model are missing.
        """
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as e:
            raise EmbeddingUnavailable(
                "semantic search needs the `semantic` extra (torch, transformers)"
            ) from e
        # Revision is pinned via MODEL_REVISION; bandit B615 only accepts literals.
        try:
            self._tokenizer: Any = AutoTokenizer.from_pretrained(  # nosec B615
                MODEL_ID, revision=MODEL_REVISION, local_files_only=True
            )
            model: Any = AutoModel.from_pretrained(  # nosec B615
                MODEL_ID, revision=MODEL_REVISION, local_files_only=True
            )
        except OSError as e:
            raise EmbeddingUnavailable(
                f"{MODEL_ID} is not downloaded; run `okf-ingest fetch-model`"
            ) from e
        if device is None:
            # Apple GPU was 4x faster than CPU in the pilot, with identical vectors.
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            if torch.cuda.is_available():
                device = "cuda"
        self._torch = torch
        self._device = device
        self._model = model.eval().to(device)

    def encode(self, texts: List[str], kind: str) -> np.ndarray:
        """Embed texts as `query` or `passage`; returns float32 rows of length DIM."""
        if kind not in ("query", "passage"):
            raise ValueError("kind must be 'query' or 'passage'")
        torch = self._torch
        rows = []
        for start in range(0, len(texts), BATCH):
            batch = self._tokenizer(
                [f"{kind}: {t}" for t in texts[start : start + BATCH]],
                padding=True,
                truncation=True,
                max_length=MAX_TOKENS,
                return_tensors="pt",
            ).to(self._device)
            with torch.no_grad():
                hidden = self._model(**batch).last_hidden_state
            mask = batch["attention_mask"].unsqueeze(-1).float()
            pooled = (hidden * mask).sum(1) / mask.sum(1)
            rows.append(torch.nn.functional.normalize(pooled, dim=-1).cpu().numpy())
        if not rows:
            return np.zeros((0, DIM), dtype=np.float32)
        return np.vstack(rows).astype(np.float32)


def unavailable_reason() -> Optional[str]:
    """Why semantic indexing cannot run, or None. Cheap: loads no model weights."""
    import importlib.util

    if not all(importlib.util.find_spec(m) for m in ("torch", "transformers")):
        return "semantic search needs the `semantic` extra (torch, transformers)"
    from huggingface_hub import try_to_load_from_cache

    for name in MODEL_FILES:
        if not isinstance(
            try_to_load_from_cache(MODEL_ID, name, revision=MODEL_REVISION), str
        ):
            return f"{MODEL_ID} is not downloaded; run `okf-ingest fetch-model`"
    return None


class LazyEmbedder:
    """Same model ID as `Embedder`, but loads the model only when asked to encode.

    Rebuilds that reuse every vector then skip the multi-second model load.
    """

    model_id = Embedder.model_id

    def encode(self, texts: List[str], kind: str) -> np.ndarray:
        """Load the model on first use and embed."""
        return get_embedder().encode(texts, kind)


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    """Process-wide embedder, loaded on first use.

    Raises:
        EmbeddingUnavailable: If the model cannot be loaded.
    """
    return Embedder()


def fetch_model() -> str:
    """Download the pinned model files into the Hugging Face cache; returns the path."""
    from huggingface_hub import snapshot_download

    return snapshot_download(  # nosec B615 - pinned to MODEL_REVISION
        MODEL_ID, revision=MODEL_REVISION, allow_patterns=MODEL_FILES
    )
