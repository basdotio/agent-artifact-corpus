"""Core contracts: models, paths, walking, output, registry, CLI."""

from __future__ import annotations

from .models import (
    Class,
    Constant,
    Export,
    FileId,
    Func,
    ImportRef,
    Interface,
    Param,
    Role,
    SourceFile,
    Symbols,
    TypeDef,
)
from .output import Reporter, dumps, to_jsonable, write_output
from .paths import ModuleIndex, Resolution, common_prefix, file_id, is_within
from .registry import (
    AnalysisContext,
    Analyzer,
    AnalyzerRegistry,
    Option,
    available,
    get_analyzer,
    registry,
)
from .walker import (
    DEFAULT_SKIP_DIRS,
    WalkPolicy,
    WalkResult,
    classify_role,
    read_text,
    walk,
)

__all__ = [
    "AnalysisContext",
    "Analyzer",
    "AnalyzerRegistry",
    "Class",
    "Constant",
    "DEFAULT_SKIP_DIRS",
    "Export",
    "FileId",
    "Func",
    "ImportRef",
    "Interface",
    "ModuleIndex",
    "Option",
    "Param",
    "Reporter",
    "Resolution",
    "Role",
    "SourceFile",
    "Symbols",
    "TypeDef",
    "WalkPolicy",
    "WalkResult",
    "available",
    "classify_role",
    "common_prefix",
    "dumps",
    "file_id",
    "get_analyzer",
    "is_within",
    "read_text",
    "registry",
    "to_jsonable",
    "walk",
    "write_output",
]
