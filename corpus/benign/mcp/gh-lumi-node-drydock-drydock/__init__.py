"""Drydock -- an agentic toolchest for deconstructing software architectures.

Public surface::

    from drydock import AnalysisContext, get_analyzer, available

    ctx = AnalysisContext("/path/to/project")
    result = get_analyzer("boundaries").run(ctx)

Extend it by registering an analyzer or a language backend; see
`drydock.core.registry.Analyzer` and `drydock.langs.base.LanguageParser`.
"""

from __future__ import annotations

__version__ = "0.2.0"

from .core.models import (
    Class,
    Constant,
    Export,
    FileId,
    Func,
    ImportRef,
    Interface,
    Param,
    SourceFile,
    Symbols,
    TypeDef,
)
from .core.output import Reporter
from .core.paths import ModuleIndex, Resolution
from .core.registry import (
    AnalysisContext,
    Analyzer,
    AnalyzerRegistry,
    Option,
    available,
    get_analyzer,
    registry,
)
from .core.walker import WalkPolicy, WalkResult, walk
from .langs import LanguageParser, LanguageRegistry, language_registry

__all__ = [
    "__version__",
    "AnalysisContext",
    "Analyzer",
    "AnalyzerRegistry",
    "Class",
    "Constant",
    "Export",
    "FileId",
    "Func",
    "ImportRef",
    "Interface",
    "LanguageParser",
    "LanguageRegistry",
    "ModuleIndex",
    "Option",
    "Param",
    "Reporter",
    "Resolution",
    "SourceFile",
    "Symbols",
    "TypeDef",
    "WalkPolicy",
    "WalkResult",
    "available",
    "get_analyzer",
    "language_registry",
    "registry",
    "walk",
]
