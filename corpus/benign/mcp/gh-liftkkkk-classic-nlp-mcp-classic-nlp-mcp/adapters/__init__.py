"""Adapters package: one module per classical NLP engine."""

from .base import MissingDependency, REGISTRY, detect_lang, make_result, make_token

__all__ = ["MissingDependency", "REGISTRY", "detect_lang", "make_result", "make_token"]
