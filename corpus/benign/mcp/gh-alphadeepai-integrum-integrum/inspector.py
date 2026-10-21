"""Dynamic module, function, and class introspection using inspect."""

import importlib
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from integrum.filter import MemberFilter


@dataclass
class FunctionInfo:
    """Introspected information about a function or static method."""
    name: str
    target: Callable[..., Any]
    signature: inspect.Signature
    docstring: Optional[str]
    is_coroutine: bool = False
    source_module: Optional[str] = None


@dataclass
class MethodInfo:
    """Introspected information about a class method."""
    name: str
    method: Callable[..., Any]
    signature: inspect.Signature
    docstring: Optional[str]
    is_static: bool = False
    is_class_method: bool = False


@dataclass
class ClassInfo:
    """Introspected information about a class."""
    name: str
    cls: Type[Any]
    init_signature: inspect.Signature
    docstring: Optional[str]
    methods: Dict[str, MethodInfo] = field(default_factory=dict)
    source_module: Optional[str] = None


@dataclass
class ModuleInfo:
    """Introspected information about a module."""
    name: str
    functions: Dict[str, FunctionInfo] = field(default_factory=dict)
    classes: Dict[str, ClassInfo] = field(default_factory=dict)


def import_target(target: Union[str, Any]) -> Any:
    """Import a target string or return the object if already imported.
    
    Supports:
        - 'module' (e.g. 'math')
        - 'module.submodule' (e.g. 'sklearn.datasets')
        - 'module.submodule.symbol' (e.g. 'sklearn.datasets.load_iris')
        - 'module:symbol' (e.g. 'sklearn.datasets:load_iris')
    """
    if not isinstance(target, str):
        return target

    # Handle colon notation
    if ":" in target:
        mod_name, attr_name = target.split(":", 1)
        mod = importlib.import_module(mod_name)
        curr = mod
        for part in attr_name.split("."):
            curr = getattr(curr, part)
        return curr

    # Try importing directly as module
    try:
        return importlib.import_module(target)
    except ModuleNotFoundError:
        # If last part is an attribute of a module
        if "." in target:
            parts = target.rsplit(".", 1)
            try:
                mod = importlib.import_module(parts[0])
                if hasattr(mod, parts[1]):
                    return getattr(mod, parts[1])
            except ModuleNotFoundError:
                pass
        raise


def inspect_function(func: Callable[..., Any], name: Optional[str] = None) -> FunctionInfo:
    """Inspect a function using the inspect module."""
    fn_name = name or getattr(func, "__name__", "anonymous_func")
    try:
        sig = inspect.signature(func)
    except (ValueError, TypeError):
        sig = inspect.Signature()

    doc = inspect.getdoc(func)
    is_coro = inspect.iscoroutinefunction(func)
    mod = getattr(func, "__module__", None)

    return FunctionInfo(
        name=fn_name,
        target=func,
        signature=sig,
        docstring=doc,
        is_coroutine=is_coro,
        source_module=mod,
    )


def inspect_class(
    cls: Type[Any],
    name: Optional[str] = None,
    member_filter: Optional[MemberFilter] = None,
) -> ClassInfo:
    """Inspect a class, its constructor, and public methods."""
    cls_name = name or cls.__name__
    doc = inspect.getdoc(cls)
    mod = getattr(cls, "__module__", None)

    # Constructor signature
    try:
        init_sig = inspect.signature(cls)
    except (ValueError, TypeError):
        try:
            init_sig = inspect.signature(cls.__init__)
        except (ValueError, TypeError):
            init_sig = inspect.Signature()

    methods: Dict[str, MethodInfo] = {}

    for attr_name, member in inspect.getmembers(cls):
        # Skip private/dunder methods
        if attr_name.startswith("_"):
            continue

        # Check filter if provided
        if member_filter and not member_filter.matches(attr_name, f"{cls_name}.{attr_name}"):
            continue

        # Distinguish functions/methods
        if inspect.isfunction(member) or inspect.ismethod(member) or inspect.isbuiltin(member):
            try:
                sig = inspect.signature(member)
            except (ValueError, TypeError):
                sig = inspect.Signature()

            method_doc = inspect.getdoc(member)
            # Check static/classmethod attributes
            raw_attr = getattr(cls, attr_name, member)
            is_static = isinstance(raw_attr, staticmethod)
            is_class = isinstance(raw_attr, classmethod)

            methods[attr_name] = MethodInfo(
                name=attr_name,
                method=member,
                signature=sig,
                docstring=method_doc,
                is_static=is_static,
                is_class_method=is_class,
            )

    return ClassInfo(
        name=cls_name,
        cls=cls,
        init_signature=init_sig,
        docstring=doc,
        methods=methods,
        source_module=mod,
    )


def inspect_module(
    module: Any,
    member_filter: Optional[MemberFilter] = None,
) -> ModuleInfo:
    """Inspect an entire module for public functions and classes."""
    mod_name = getattr(module, "__name__", str(module))
    functions: Dict[str, FunctionInfo] = {}
    classes: Dict[str, ClassInfo] = {}

    for attr_name, member in inspect.getmembers(module):
        # Skip private members
        if attr_name.startswith("_"):
            continue

        # Respect filter
        if member_filter and not member_filter.matches(attr_name, f"{mod_name}.{attr_name}"):
            continue

        if inspect.isclass(member):
            # Check if class was defined in this module or related package
            classes[attr_name] = inspect_class(member, name=attr_name, member_filter=member_filter)
        elif inspect.isfunction(member) or inspect.isbuiltin(member):
            functions[attr_name] = inspect_function(member, name=attr_name)

    return ModuleInfo(
        name=mod_name,
        functions=functions,
        classes=classes,
    )
