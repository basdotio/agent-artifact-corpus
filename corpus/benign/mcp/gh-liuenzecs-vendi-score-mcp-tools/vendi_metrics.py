"""Minimal CPU-only bindings to the pinned official Vendi-Score public API."""
from __future__ import annotations

import hashlib
import importlib.abc
import json
import math
import os
from pathlib import Path
import sys
from typing import Annotated, Literal
import uuid
import warnings


class _NoLocalModels(importlib.abc.MetaPathFinder):
    """Block accidental neural-model imports; this is not a security sandbox."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {
            'torch', 'torchvision', 'tensorflow', 'transformers', 'jax',
            'sentence_transformers', 'ollama', 'llama_cpp', 'diffusers',
        }:
            raise ModuleNotFoundError('Local model frameworks are disabled in this MCP.')
        return None


sys.meta_path.insert(0, _NoLocalModels())
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

import numpy as np
from scipy import linalg
from fastmcp import FastMCP


ROOT = Path(__file__).resolve().parents[2]
VENDOR = ROOT / 'vendor' / 'repo'
SOURCE_SHA256 = '8ee71e09e475c82f65262174505c88a2a119da5fb62a9e0ef4f2c12864441ac6'
COMMIT = 'ff1dfdbe6356b98a6087540f215b9a9db6db7c11'
REFERENCE = f'https://github.com/vertaix/Vendi-Score/blob/{COMMIT}/README.md'
_source = VENDOR / 'vendi_score' / 'vendi.py'
if hashlib.sha256(_source.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise RuntimeError('Pinned original Vendi source SHA256 mismatch.')
sys.path.insert(0, str(VENDOR))
from vendi_score import vendi

if Path(vendi.__file__).resolve() != _source.resolve():
    raise RuntimeError('Vendi import must originate from the bundled original source.')

vendi_metrics_mcp = FastMCP(name='vendi_metrics')
_Q = float | Literal['inf']
_ATOL = 1e-10


def _order(q: _Q) -> _Q:
    if q == 'inf':
        return q
    if isinstance(q, bool) or not isinstance(q, (int, float)) or not math.isfinite(q) or q <= 0:
        raise ValueError('q must be a positive finite number or the string inf. q=0 is deferred because upstream counts positive eigenvalue roundoff as rank.')
    return q


def _matrix(value, name: str) -> np.ndarray:
    try:
        matrix = np.asarray(value, dtype=np.float64)
    except (ValueError, TypeError) as exc:
        raise ValueError(f'{name} must be a rectangular numeric matrix.') from exc
    if matrix.ndim != 2 or 0 in matrix.shape or not np.isfinite(matrix).all():
        raise ValueError(f'{name} must be a nonempty finite rectangular matrix.')
    return matrix


def _kernel(K: np.ndarray, normalize: bool) -> None:
    if K.shape[0] != K.shape[1]:
        raise ValueError('K must be square with rows and columns aligned to the same samples.')
    if not np.allclose(K, K.T, rtol=0, atol=_ATOL):
        raise ValueError('K must be symmetric (absolute tolerance 1e-10).')
    diagonal = np.diagonal(K)
    if np.any(diagonal <= 0):
        raise ValueError('K must have a strictly positive diagonal.')
    if not normalize and not np.allclose(diagonal, 1, rtol=0, atol=_ATOL):
        raise ValueError('K must have unit diagonal when normalize=false.')
    # PSD is a documented prerequisite. Cholesky on a tolerance-shifted copy
    # checks that contract without recomputing entropy or a full eigen-spectrum.
    # The unmodified K, never this validation copy, is passed to upstream.
    tolerance = _ATOL * max(1.0, K.shape[0] * float(np.max(np.abs(K))))
    shifted = K.copy()
    shifted[np.diag_indices_from(shifted)] += tolerance
    try:
        linalg.cholesky(shifted, lower=True, check_finite=False)
    except linalg.LinAlgError as exc:
        raise ValueError('K must be positive semidefinite within the documented numerical tolerance.') from exc


def _result(tool: str, function: str, value, inputs: dict, shape: tuple[int, int], notices: list[str], output_dir: str | None) -> dict:
    score = float(value)
    if not math.isfinite(score):
        raise ValueError('The original scientific function returned a nonfinite score.')
    base = Path(output_dir).expanduser().resolve() if output_dir else ROOT / 'outputs' / 'tool-results'
    call_dir = base / uuid.uuid4().hex
    call_dir.mkdir(parents=True, exist_ok=False)
    raw_path = call_dir / 'result.json'
    provenance = {'repository': 'https://github.com/vertaix/Vendi-Score', 'commit': COMMIT,
                  'source_path': 'vendi_score/vendi.py', 'source_sha256': SOURCE_SHA256,
                  'upstream_function': f'vendi_score.vendi.{function}', 'algorithm_changes': False}
    raw = {'tool_name': tool, 'inputs': inputs, 'native_result': score, 'warnings': notices,
           'provenance': provenance, 'local_models_called': False, 'gpu_called': False}
    raw_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return {'message': 'Vendi diversity computed by the pinned original CPU implementation.',
            'reference': REFERENCE,
            'artifacts': [{'description': 'Original scalar result, complete numeric inputs and source provenance', 'path': str(raw_path.resolve())}],
            'score': score, 'num_samples': shape[0], 'input_shape': list(shape),
            'provenance': provenance, 'warnings': notices}


@vendi_metrics_mcp.tool()
def vendi_score_similarity(
    K: Annotated[list[list[float]], 'Finite symmetric positive-semidefinite sample similarity matrix; unit diagonal unless normalize=true'],
    q: Annotated[_Q, 'Positive diversity order, or inf; q=0 is deferred for an upstream numerical rank issue'] = 1,
    p: Annotated[list[float] | None, 'Optional nonnegative sample probabilities in matrix order, summing to one; null gives equal weights'] = None,
    normalize: Annotated[bool, 'Forward original diagonal normalization; false requires a unit-diagonal kernel'] = False,
    output_dir: Annotated[str | None, 'Base directory for a fresh per-call result artifact; null uses this package outputs'] = None,
) -> dict:
    """Measure effective diversity from a supplied similarity matrix with the original Vendi API.
    Input is a valid numeric kernel and order; output is the scalar score and a unique raw-result JSON artifact.
    """
    order = _order(q)
    matrix = _matrix(K, 'K')
    _kernel(matrix, normalize)
    probabilities = None
    if p is not None:
        probabilities = np.asarray(p, dtype=np.float64)
        if probabilities.ndim != 1 or len(probabilities) != matrix.shape[0] or not np.isfinite(probabilities).all() or np.any(probabilities < 0):
            raise ValueError('p must contain one finite nonnegative probability per sample.')
        if not np.isclose(probabilities.sum(), 1, rtol=0, atol=_ATOL):
            raise ValueError('p probabilities must sum to one (absolute tolerance 1e-10).')
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')
        value = vendi.score_K(matrix, q=order, p=probabilities, normalize=normalize)
    return _result('vendi_score_similarity', 'score_K', value,
                   {'K': K, 'q': order, 'p': p, 'normalize': normalize}, matrix.shape,
                   [str(item.message) for item in captured], output_dir)


@vendi_metrics_mcp.tool()
def vendi_score_embeddings(
    X: Annotated[list[list[float]], 'Already supplied finite sample vectors; nonzero rows, with unit norm required when normalize=false'],
    q: Annotated[_Q, 'Positive diversity order, or inf; q=0 is deferred for an upstream numerical rank issue'] = 1,
    normalize: Annotated[bool, 'Forward original row normalization; true retains the score_dual API default'] = True,
    output_dir: Annotated[str | None, 'Base directory for a fresh per-call result artifact; null uses this package outputs'] = None,
) -> dict:
    """Measure diversity of already supplied vectors using the original covariance-based Vendi API.
    Input is a valid numeric vector matrix and order; output is the scalar score and a unique raw-result JSON artifact.
    """
    order = _order(q)
    matrix = _matrix(X, 'X')
    norms = np.linalg.norm(matrix, axis=1)
    if not np.isfinite(norms).all() or np.any(norms <= 0):
        raise ValueError('X must contain finite nonzero rows with finite norms.')
    if not normalize and not np.allclose(norms, 1, rtol=0, atol=_ATOL):
        raise ValueError('X rows must have unit norm when normalize=false.')
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')
        value = vendi.score_dual(matrix, q=order, normalize=normalize)
    return _result('vendi_score_embeddings', 'score_dual', value,
                   {'X': X, 'q': order, 'normalize': normalize}, matrix.shape,
                   [str(item.message) for item in captured], output_dir)
