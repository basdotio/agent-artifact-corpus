"""Local PDF table extraction API."""

__version__ = "0.1.0"

from .core.extract import extract_tables, inspect_pdf

__all__ = ["extract_tables", "inspect_pdf", "__version__"]
