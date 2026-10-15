"""MCP tools for semantic code search (thin wrappers; logic lives in staticsight.semantic)."""

from __future__ import annotations

from ..config import load_config
from ..semantic.search import refresh_report, semantic_search_report, similar_code_report


async def semantic_search(query: str, path_glob: str = "", language: str = "", kind: str = "", top_k: int = 10) -> str:
    """Finds code by MEANING, not exact text, across the whole repository (every language: C/C++, Python, scripts, docs, configs). Use when you know WHAT the code does but not what it is called, e.g. 'where do we retry failed connections?', 'code that parses the packet header', 'where is the registry key written'. Combines a local code-embedding model with keyword matching and returns ranked functions/classes/sections with file:line, score and a short excerpt. Before searching, the local index is refreshed automatically when files changed (large changes refresh in the background; the result says so). After a git pull or big edits you may call refresh_semantic_index first."""
    return await semantic_search_report(load_config(), query, path_glob, language, kind, top_k)


async def find_similar_code(file_path: str, start_line: int, end_line: int = 0, top_k: int = 8) -> str:
    """Finds code elsewhere in the repository that is semantically similar to a given region: copy-paste twins, parallel implementations (Windows/Linux variants, encode/decode pairs) and places that probably need the same fix. Use during review when a function or bug fix changed: 'where else do we do this?'. Give a file and line (the enclosing function is used) or an explicit line range."""
    return await similar_code_report(load_config(), file_path, start_line, end_line, top_k)


async def refresh_semantic_index(full: bool = False) -> str:
    """Builds or refreshes the local semantic search index for the workspace (incremental: only files whose content changed are re-embedded). Call it after a git pull, branch switch or large edits, or when semantic_search reports a stale index. Small refreshes finish before returning; large ones continue in the background (check get_index_status). Writes only to StaticSight's own data folder (`.staticsight/` in the repository, ignored by git), never to source files."""
    return await refresh_report(load_config(), full)
