"""Python backend, built on `ast`.

The reference implementation of `LanguageParser`: full fidelity, and the model
the regex backends follow in shape if not in precision.

Three things it gets right that the pre-0.2 extractor did not:

* ``from . import sibling`` reports ``sibling`` in `ImportRef.symbols`, so the
  index can resolve it to the sibling module. The old code dropped the symbol
  list and resolved such imports to the package's own ``__init__.py``.
* ``__all__`` is treated as an explicit declaration of the public surface, and
  when it is absent the underscore convention is applied to *every* category
  including module constants. The old code ran its privacy check through
  ``getattr(node, "name")``, which `ast.Assign` does not have, so private
  constants like ``_SECRET_KEY`` were published as public API.
* ``sys.path`` mutations are reported via `runtime_roots`, letting the index
  resolve the flat sibling imports this very repository uses.
"""

from __future__ import annotations

import ast
from typing import Iterable

from ..core.models import (
    Class,
    Constant,
    Export,
    Func,
    ImportRef,
    Interface,
    Param,
    Symbols,
    TypeDef,
)
from .base import BaseParser

__all__ = ["PythonParser"]

_MAX_DEFAULT_LEN = 60
_MAX_VALUE_LEN = 120


class PythonParser(BaseParser):
    name = "python"
    extensions = (".py", ".pyi")
    fidelity = "ast"

    # -- protocol ----------------------------------------------------------

    def symbols(self, source: str, path: str) -> Symbols:
        tree = _parse(source)
        if tree is None:
            return Symbols()

        classes: list[Class] = []
        functions: list[Func] = []
        constants: list[Constant] = []
        types: list[TypeDef] = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(_class(node))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(_func(node))
            elif isinstance(node, ast.Assign):
                constants.extend(_constants_from_assign(node))
                types.extend(_typevars_from_assign(node))
            elif isinstance(node, ast.AnnAssign):
                c = _constant_from_ann_assign(node)
                if c:
                    constants.append(c)
                t = _typealias_from_ann_assign(node)
                if t:
                    types.append(t)
            elif hasattr(ast, "TypeAlias") and isinstance(node, ast.TypeAlias):
                # PEP 695 ``type X = int`` (Python 3.12+), which the previous
                # extractor did not recognise at all.
                types.append(
                    TypeDef(
                        name=_name_of(node.name),
                        kind="alias",
                        definition=_unparse(node.value, _MAX_VALUE_LEN),
                        line=node.lineno,
                    )
                )

        return Symbols(
            classes=tuple(classes),
            functions=tuple(functions),
            constants=tuple(constants),
            types=tuple(types),
            exports=tuple(_all_exports(tree)),
            imports=self._imports_from_tree(tree),
        )

    def imports(self, source: str, path: str) -> tuple[ImportRef, ...]:
        tree = _parse(source)
        return self._imports_from_tree(tree) if tree is not None else ()

    def interface(self, source: str, path: str) -> Interface:
        """Public surface, honouring ``__all__`` when the module declares one."""
        sym = self.symbols(source, path)
        tree = _parse(source)
        declared = _all_names(tree) if tree is not None else None
        return Interface.from_symbols(sym, explicit=declared)

    # -- extra hook consumed by ModuleIndex --------------------------------

    def runtime_roots(self, source: str, path: str) -> tuple[str, ...]:
        """Directories the module pushes onto ``sys.path`` at import time.

        Recognises the common shapes::

            sys.path.insert(0, "vendor")
            sys.path.append(os.path.join(os.path.dirname(__file__), "libs"))
            sys.path.insert(0, str(Path(__file__).parent / "analyzers"))

        Only the literal path fragments are extracted; ``__file__``-relative
        expressions resolve against the importing file's own directory, which
        is what the index assumes.
        """
        tree = _parse(source)
        if tree is None:
            return ()

        here = path.rsplit("/", 1)[0] if "/" in path else ""
        roots: list[str] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if not isinstance(fn, ast.Attribute) or fn.attr not in ("insert", "append"):
                continue
            if not _is_sys_path(fn.value):
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                    continue
                fragments = _literal_fragments(arg)
                if not fragments:
                    continue
                joined = "/".join(fragments)
                roots.append(f"{here}/{joined}" if here else joined)

        return tuple(dict.fromkeys(roots))

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _import_scopes(tree: ast.AST) -> dict[int, str]:
        """Map each import statement's line to the scope it sits in.

        Module-level imports create load-time dependencies; imports inside a
        function body or an `if TYPE_CHECKING:` block do not. Distinguishing
        them is what separates a real circular dependency from a deliberate
        deferral.
        """
        scopes: dict[int, str] = {}

        def walk(node: ast.AST, scope: str) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.Import, ast.ImportFrom)):
                    scopes[child.lineno] = scope
                    continue
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    walk(child, "function")
                elif isinstance(child, ast.ClassDef):
                    walk(child, scope)
                elif isinstance(child, (ast.If, ast.Try)):
                    # `if TYPE_CHECKING:` and try/except ImportError fallbacks
                    # are both conditional, not unconditional load-time edges.
                    walk(child, "conditional" if scope == "module" else scope)
                else:
                    walk(child, scope)

        walk(tree, "module")
        return scopes

    @classmethod
    def _imports_from_tree(cls, tree: ast.AST) -> tuple[ImportRef, ...]:
        scopes = cls._import_scopes(tree)
        refs: list[ImportRef] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    refs.append(
                        ImportRef(
                            raw=alias.name,
                            kind="absolute",
                            line=getattr(node, "lineno", 0),
                            scope=scopes.get(getattr(node, "lineno", 0), "module"),
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                refs.append(
                    ImportRef(
                        raw=node.module or "",
                        kind="relative" if node.level else "absolute",
                        level=node.level or 0,
                        # Carrying the symbols is what makes
                        # ``from . import sibling`` resolvable.
                        symbols=tuple(a.name for a in node.names),
                        line=getattr(node, "lineno", 0),
                        scope=scopes.get(getattr(node, "lineno", 0), "module"),
                    )
                )
        return tuple(refs)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _parse(source: str) -> ast.AST | None:
    try:
        return ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return None


def _unparse(node: ast.AST | None, limit: int | None = None) -> str | None:
    if node is None:
        return None
    try:
        text = ast.unparse(node)
    except Exception:
        return None
    text = " ".join(text.split())
    if limit and len(text) > limit:
        return text[:limit] + "…"
    return text


def _name_of(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    return _unparse(node) or "<expr>"


def _docstring(node: ast.AST) -> str | None:
    try:
        doc = ast.get_docstring(node, clean=True)  # type: ignore[arg-type]
    except TypeError:
        return None
    if not doc:
        return None
    return doc.strip().split("\n", 1)[0]


def _params(node: ast.FunctionDef | ast.AsyncFunctionDef, *, drop_self: bool) -> tuple[Param, ...]:
    a = node.args
    positional = list(a.posonlyargs) + list(a.args)

    # Defaults bind to the *end* of the positional list, before self is dropped.
    defaults: dict[int, str] = {}
    offset = len(positional) - len(a.defaults)
    for i, d in enumerate(a.defaults):
        rendered = _unparse(d, _MAX_DEFAULT_LEN)
        if rendered is not None:
            defaults[offset + i] = rendered

    out: list[Param] = []
    for i, arg in enumerate(positional):
        if drop_self and i == 0 and arg.arg in ("self", "cls"):
            continue
        out.append(
            Param(
                name=arg.arg,
                type=_unparse(arg.annotation),
                default=defaults.get(i),
            )
        )

    if a.vararg:
        out.append(Param(name=f"*{a.vararg.arg}", type=_unparse(a.vararg.annotation)))

    for arg, default in zip(a.kwonlyargs, a.kw_defaults):
        out.append(
            Param(
                name=arg.arg,
                type=_unparse(arg.annotation),
                default=_unparse(default, _MAX_DEFAULT_LEN) if default else None,
            )
        )

    if a.kwarg:
        out.append(Param(name=f"**{a.kwarg.arg}", type=_unparse(a.kwarg.annotation)))

    return tuple(out)


def _func(node: ast.FunctionDef | ast.AsyncFunctionDef, *, method: bool = False) -> Func:
    return Func(
        name=node.name,
        params=_params(node, drop_self=method),
        returns=_unparse(node.returns),
        line=node.lineno,
        is_async=isinstance(node, ast.AsyncFunctionDef),
        decorators=tuple(d for d in (_unparse(x) for x in node.decorator_list) if d),
        doc=_docstring(node),
    )


def _class(node: ast.ClassDef) -> Class:
    methods: list[Func] = []
    class_methods: list[Func] = []
    properties: list[Func] = []

    for item in node.body:
        if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        fn = _func(item, method=True)
        decorators = {d.split("(")[0].split(".")[-1] for d in fn.decorators}
        if "property" in decorators or "cached_property" in decorators:
            properties.append(fn)
        elif {"classmethod", "staticmethod"} & decorators:
            class_methods.append(fn)
        elif decorators & {"setter", "deleter"}:
            properties.append(fn)
        else:
            methods.append(fn)

    return Class(
        name=node.name,
        bases=tuple(b for b in (_unparse(x) for x in node.bases) if b),
        methods=tuple(methods),
        class_methods=tuple(class_methods),
        properties=tuple(properties),
        line=node.lineno,
        decorators=tuple(d for d in (_unparse(x) for x in node.decorator_list) if d),
        doc=_docstring(node),
        kind="class",
    )


def _constants_from_assign(node: ast.Assign) -> Iterable[Constant]:
    for target in node.targets:
        if isinstance(target, ast.Name) and _looks_constant(target.id):
            yield Constant(
                name=target.id,
                value=_unparse(node.value, _MAX_VALUE_LEN),
                line=node.lineno,
            )


def _constant_from_ann_assign(node: ast.AnnAssign) -> Constant | None:
    if not isinstance(node.target, ast.Name) or not _looks_constant(node.target.id):
        return None
    return Constant(
        name=node.target.id,
        value=_unparse(node.value, _MAX_VALUE_LEN),
        type=_unparse(node.annotation),
        line=node.lineno,
    )


def _typevars_from_assign(node: ast.Assign) -> Iterable[TypeDef]:
    """``T = TypeVar("T")`` / ``Alias: TypeAlias = ...`` written as a plain assign."""
    call = node.value
    if not isinstance(call, ast.Call):
        return
    fname = _name_of(call.func).split(".")[-1]
    if fname not in ("TypeVar", "NewType", "ParamSpec", "TypeVarTuple"):
        return
    for target in node.targets:
        if isinstance(target, ast.Name):
            yield TypeDef(
                name=target.id,
                kind="alias",
                definition=_unparse(call, _MAX_VALUE_LEN),
                line=node.lineno,
            )


def _typealias_from_ann_assign(node: ast.AnnAssign) -> TypeDef | None:
    if not isinstance(node.target, ast.Name):
        return None
    ann = _unparse(node.annotation) or ""
    if "TypeAlias" not in ann:
        return None
    return TypeDef(
        name=node.target.id,
        kind="alias",
        definition=_unparse(node.value, _MAX_VALUE_LEN),
        line=node.lineno,
    )


def _looks_constant(name: str) -> bool:
    """UPPER_SNAKE identifiers, the Python convention for a module constant."""
    return name.isupper() and any(ch.isalpha() for ch in name)


def _all_names(tree: ast.AST) -> frozenset[str] | None:
    """The names in ``__all__``, or None when the module does not declare one.

    Handles ``__all__ = [...]``, ``__all__ += [...]`` and ``__all__.extend([...])``.
    A module whose ``__all__`` is computed dynamically yields None -- unknown,
    not empty, so the caller falls back to the naming convention instead of
    concluding the module exposes nothing.
    """
    names: set[str] = set()
    found = False

    for node in ast.walk(tree):
        value = None
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
                value = node.value
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "__all__":
                value = node.value
        elif isinstance(node, ast.Call):
            fn = node.func
            if (
                isinstance(fn, ast.Attribute)
                and fn.attr in ("extend", "append")
                and isinstance(fn.value, ast.Name)
                and fn.value.id == "__all__"
            ):
                value = node.args[0] if node.args else None
                if fn.attr == "append" and value is not None:
                    value = ast.List(elts=[value], ctx=ast.Load())

        if value is None:
            continue
        found = True
        if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
            for elt in value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    names.add(elt.value)

    if not found:
        return None
    return frozenset(names) if names else None


def _all_exports(tree: ast.AST) -> Iterable[Export]:
    declared = _all_names(tree)
    if not declared:
        return ()
    return tuple(Export(name=n) for n in sorted(declared))


def _is_sys_path(node: ast.AST) -> bool:
    """True for the ``sys.path`` attribute access, however ``sys`` is bound."""
    if isinstance(node, ast.Attribute) and node.attr == "path":
        return isinstance(node.value, ast.Name) and node.value.id == "sys"
    return isinstance(node, ast.Name) and node.id == "path"


def _literal_fragments(node: ast.AST) -> list[str]:
    """Pull literal path pieces out of a path-building expression.

    ``str(Path(__file__).parent / "analyzers")`` -> ``["analyzers"]``
    ``os.path.join(here, "a", "b")``             -> ``["a", "b"]``
    """
    out: list[str] = []

    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            text = sub.value.strip().strip("/")
            if text and text not in (".", "..") and not text.startswith("__"):
                out.append(text)

    return out
