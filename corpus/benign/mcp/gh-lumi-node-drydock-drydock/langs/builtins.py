"""Register the built-in language backends.

Same registration path a third-party backend uses. To add a language, write a
`LanguageParser` and either append it here or ship it as a
``drydock.languages`` entry point -- no analyzer is touched either way.
"""

from __future__ import annotations

from . import language_registry
from .csharp import CSharpParser
from .go import GoParser
from .java import JavaParser
from .javascript import JavaScriptParser, TypeScriptParser
from .python_ast import PythonParser
from .rust import RustParser

_registry = language_registry()

for _parser in (
    PythonParser(),
    TypeScriptParser(),
    JavaScriptParser(),
    RustParser(),
    GoParser(),
    CSharpParser(),
    JavaParser(),
):
    _registry.register(_parser)

__all__ = [
    "CSharpParser",
    "GoParser",
    "JavaParser",
    "JavaScriptParser",
    "PythonParser",
    "RustParser",
    "TypeScriptParser",
]
