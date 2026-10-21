"""FastMCP server integration and dynamic tool generation for Integrum."""

import inspect
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from fastmcp import FastMCP, Context
from fastmcp.server.server import Transport

from integrum.docstrings import (
    SERVER_INSTRUCTIONS,
    format_function_description,
    extract_parameter_descriptions,
)
from integrum.filter import MemberFilter
from integrum.inspector import (
    ClassInfo,
    FunctionInfo,
    import_target,
    inspect_class,
    inspect_function,
    inspect_module,
)
from integrum.store import ObjectStore

logger = logging.getLogger("integrum")


def _get_session_id(ctx: Optional[Context]) -> str:
    """Extract session ID safely from FastMCP Context, or fallback to 'default'."""
    if ctx is not None:
        try:
            sid = getattr(ctx, "session_id", None)
            if sid:
                return str(sid)
        except Exception:
            pass
    return "default"


def _build_parameter_list(
    sig: inspect.Signature,
    skip_first: bool = False,
    extra_lead_params: Optional[List[Tuple[str, str]]] = None,
) -> Tuple[List[str], List[Tuple[str, str, Any, bool]], Optional[str]]:
    """Parse signature parameters into executable code definitions and metadata.
    
    Returns:
        (param_code_list, param_meta_list, var_pos_param_name)
    """
    param_code_list: List[str] = []
    param_meta_list: List[Tuple[str, str, Any, bool]] = []
    has_kwonly_marker = False
    var_pos_param_name: Optional[str] = None

    if extra_lead_params:
        for name, ann in extra_lead_params:
            param_code_list.append(f"{name}: {ann}")
            param_meta_list.append((name, ann, inspect.Parameter.empty, False))

    for i, (name, param) in enumerate(sig.parameters.items()):
        if name in ("self", "cls"):
            continue
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            continue
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            var_pos_param_name = name
            param_code_list.append(f"{name}: Any = None")
            param_meta_list.append((name, "Any", None, True))
            # If named arrays/args, also support X and y as optional aliases
            if name in ("arrays", "args") and "X" not in sig.parameters and "y" not in sig.parameters:
                param_code_list.append("X: Any = None")
                param_meta_list.append(("X", "Any", None, True))
                param_code_list.append("y: Any = None")
                param_meta_list.append(("y", "Any", None, True))
            continue

        if param.kind == inspect.Parameter.KEYWORD_ONLY and not has_kwonly_marker:
            param_code_list.append("*")
            has_kwonly_marker = True

        default = param.default
        has_default = default is not inspect.Parameter.empty

        ann = "Any"
        if name == "obj_id":
            ann = "str"
        elif param.annotation in (int, float, str, bool):
            ann = param.annotation.__name__

        if has_default:
            if isinstance(default, (int, float, str, bool, type(None))):
                def_repr = repr(default)
            else:
                def_repr = "None"
            param_code_list.append(f"{name}: {ann} = {def_repr}")
            param_meta_list.append((name, ann, default, True))
        else:
            param_code_list.append(f"{name}: {ann}")
            param_meta_list.append((name, ann, inspect.Parameter.empty, False))

    return param_code_list, param_meta_list, var_pos_param_name


def _create_dynamic_wrapper(
    tool_name: str,
    docstring: str,
    param_code_list: List[str],
    handler: Callable[[Dict[str, Any], Optional[Context]], Any],
) -> Callable[..., Any]:
    """Create a typed dynamic function compatible with FastMCP inspection."""
    full_params = list(param_code_list) + ["ctx: Context = None"]
    param_str = ", ".join(full_params)

    code = f"""
def {tool_name}({param_str}) -> Any:
    kw = locals().copy()
    kw.pop('ctx', None)
    return __handler(kw, ctx)
"""
    local_ns: Dict[str, Any] = {
        "Context": Context,
        "Any": Any,
        "__handler": handler,
    }
    exec(code, local_ns)
    wrapper = local_ns[tool_name]
    wrapper.__name__ = tool_name
    wrapper.__doc__ = docstring
    return wrapper


def _format_result(
    result: Any,
    store: ObjectStore,
    session_id: str,
    label: str,
    target_obj_id: Optional[str] = None,
) -> Any:
    """Format execution output, registering non-primitive objects in the store."""
    # If method returned self (like estimator.fit())
    if target_obj_id is not None and result is store.get(target_obj_id, session_id=session_id):
        return {
            "status": "success",
            "object_id": target_obj_id,
            "message": f"Successfully executed on object '{target_obj_id}' (returned self).",
        }

    # If result is primitive
    if result is None:
        return {"status": "success", "message": "Execution completed successfully (None)."}
    if isinstance(result, (int, float, bool)):
        return result
    if isinstance(result, str) and len(result) < 500:
        return result

    # Non-primitive object (numpy array, model, Bunch, dict, dataset, etc.)
    new_id = store.register(result, label=label, session_id=session_id)

    meta = store.list_objects(session_id=session_id).get(new_id, {})
    response: Dict[str, Any] = {
        "status": "success",
        "object_id": new_id,
        "type": meta.get("type", type(result).__name__),
    }
    if meta.get("shape"):
        response["shape"] = meta["shape"]

    # If composite (tuple/dict/bunch)
    if isinstance(result, (tuple, list)):
        response["items"] = [f"{new_id}_{i}" for i in range(len(result))]
        if len(result) == 4 and "split" in label.lower():
            sub_labels = ["X_train", "X_test", "y_train", "y_test"]
            for idx, sub in enumerate(sub_labels):
                store._sessions[session_id][f"{new_id}.{sub}"] = result[idx]
                store._sessions[session_id][f"{new_id}_{sub}"] = result[idx]
            response["sub_keys"] = [f"{new_id}.{sub}" for sub in sub_labels]
            response["message"] = (
                f"train_test_split returned 4 arrays stored under '{new_id}':\n"
                f"  - X_train: '{new_id}.X_train' (or '{new_id}_0')\n"
                f"  - X_test:  '{new_id}.X_test' (or '{new_id}_1')\n"
                f"  - y_train: '{new_id}.y_train' (or '{new_id}_2')\n"
                f"  - y_test:  '{new_id}.y_test' (or '{new_id}_3')"
            )
        else:
            response["message"] = (
                f"Stored {type(result).__name__} with object_id '{new_id}'. "
                f"Access items using: {response['items']}."
            )
    elif isinstance(result, dict) or hasattr(result, "keys"):
        try:
            keys = list(result.keys())[:10]
            response["sub_keys"] = [f"{new_id}.{k}" for k in keys]
            response["message"] = (
                f"Stored {type(result).__name__} with object_id '{new_id}'. "
                f"Access sub-keys using dot notation: {response['sub_keys']}."
            )
        except Exception:
            response["message"] = f"Stored {type(result).__name__} with object_id '{new_id}'."
    else:
        response["message"] = f"Stored {type(result).__name__} with object_id '{new_id}'."

    return response


class IntegrumServer:
    """Converts Python modules, classes, and functions into a FastMCP server with state management."""

    def __init__(
        self,
        name: str = "integrum-server",
        store: Optional[ObjectStore] = None,
        instructions: Optional[str] = None,
    ) -> None:
        self.name = name
        self.store = store or ObjectStore()
        self.instructions = instructions or SERVER_INSTRUCTIONS
        self.mcp = FastMCP(name=self.name, instructions=self.instructions)
        self._registered_tool_names: set[str] = set()

        # Register utility tools
        self._register_utility_tools()

    def _register_utility_tools(self) -> None:
        """Register built-in utility tools for inspecting stored objects."""
        store = self.store

        def list_stored_objects(ctx: Context = None) -> Dict[str, Any]:
            """List all objects currently held in memory for this session."""
            session_id = _get_session_id(ctx)
            return {"session_id": session_id, "objects": store.list_objects(session_id=session_id)}

        def inspect_stored_object(obj_id: str, ctx: Context = None) -> Dict[str, Any]:
            """Inspect detailed attributes, shape, and representation of a stored object."""
            session_id = _get_session_id(ctx)
            if not store.has(obj_id, session_id=session_id):
                return {"error": f"Object '{obj_id}' not found in session '{session_id}'."}
            obj = store.get(obj_id, session_id=session_id)
            attrs = [a for a in dir(obj) if not a.startswith("_")][:25]
            return {
                "object_id": obj_id,
                "type": type(obj).__name__,
                "repr": repr(obj)[:500],
                "shape": getattr(obj, "shape", None),
                "public_attributes": attrs,
            }

        self.mcp.tool(list_stored_objects)
        self.mcp.tool(inspect_stored_object)
        self._registered_tool_names.add("list_stored_objects")
        self._registered_tool_names.add("inspect_stored_object")

    def expose_function(self, func: Callable[..., Any], name: Optional[str] = None) -> str:
        """Expose a standalone function as an MCP tool."""
        info = inspect_function(func, name=name)
        tool_name = info.name
        if tool_name in self._registered_tool_names:
            return tool_name

        doc = format_function_description(info.docstring, is_constructor=False, is_method=False, function_name=tool_name)
        param_code, _, var_pos_name = _build_parameter_list(info.signature)

        store = self.store
        target_fn = info.target

        def handler(kwargs: Dict[str, Any], ctx: Optional[Context]) -> Any:
            session_id = _get_session_id(ctx)
            pos_args = []
            if var_pos_name and var_pos_name in kwargs and kwargs[var_pos_name] is not None:
                val = kwargs.pop(var_pos_name)
                if isinstance(val, (list, tuple)):
                    pos_args.extend([store.resolve(x, session_id=session_id) for x in val])
                else:
                    pos_args.append(store.resolve(val, session_id=session_id))
            # Fallback if caller passed X and y as named arguments
            if not pos_args and "X" in kwargs and "y" in kwargs:
                x_val = kwargs.pop("X", None)
                y_val = kwargs.pop("y", None)
                if x_val is not None or y_val is not None:
                    pos_args.extend([
                        store.resolve(x_val, session_id=session_id),
                        store.resolve(y_val, session_id=session_id),
                    ])
            kwargs.pop("X", None)
            kwargs.pop("y", None)

            resolved_kwargs = {
                k: store.resolve(v, session_id=session_id)
                for k, v in kwargs.items()
                if v is not None or k in info.signature.parameters
            }
            try:
                res = target_fn(*pos_args, **resolved_kwargs)
            except Exception as e:
                return {"error": f"Error executing {tool_name}: {e}"}
            return _format_result(res, store, session_id, label=tool_name)

        wrapper = _create_dynamic_wrapper(tool_name, doc, param_code, handler)
        self.mcp.tool(wrapper)
        self._registered_tool_names.add(tool_name)
        logger.info(f"Registered function tool: {tool_name}")
        return tool_name

    def expose_class(
        self,
        cls: Type[Any],
        name: Optional[str] = None,
        member_filter: Optional[MemberFilter] = None,
    ) -> List[str]:
        """Expose a class constructor and its public methods as MCP tools."""
        info = inspect_class(cls, name=name, member_filter=member_filter)
        cls_name = info.name
        registered = []
        store = self.store

        # 1. Constructor tool: <ClassName>_create
        ctor_tool_name = f"{cls_name}_create"
        if ctor_tool_name not in self._registered_tool_names:
            ctor_doc = format_function_description(
                info.docstring,
                is_constructor=True,
                class_name=cls_name,
            )
            param_code, _, _ = _build_parameter_list(info.init_signature, skip_first=True)

            def ctor_handler(kwargs: Dict[str, Any], ctx: Optional[Context]) -> Any:
                session_id = _get_session_id(ctx)
                resolved_kwargs = {k: store.resolve(v, session_id=session_id) for k, v in kwargs.items()}
                try:
                    instance = cls(**resolved_kwargs)
                except Exception as e:
                    return {"error": f"Error instantiating {cls_name}: {e}"}
                obj_id = store.register(instance, label=cls_name, session_id=session_id)
                return {
                    "status": "success",
                    "object_id": obj_id,
                    "class": cls_name,
                    "message": (
                        f"Created {cls_name} instance with object_id '{obj_id}'. "
                        f"Use obj_id='{obj_id}' in subsequent method calls like {cls_name}_fit."
                    ),
                }

            wrapper = _create_dynamic_wrapper(ctor_tool_name, ctor_doc, param_code, ctor_handler)
            self.mcp.tool(wrapper)
            self._registered_tool_names.add(ctor_tool_name)
            registered.append(ctor_tool_name)
            logger.info(f"Registered constructor tool: {ctor_tool_name}")

        # 2. Methods: <ClassName>_<method_name>
        for method_name, method_info in info.methods.items():
            method_tool_name = f"{cls_name}_{method_name}"
            if method_tool_name in self._registered_tool_names:
                continue

            method_doc = format_function_description(
                method_info.docstring,
                is_method=True,
                class_name=cls_name,
            )
            # Add virtual parameter 'obj_id'
            param_code, _, _ = _build_parameter_list(
                method_info.signature,
                skip_first=True,
                extra_lead_params=[("obj_id", "str")],
            )

            # Closure capture for method dispatch
            def make_method_handler(m_name: str) -> Callable[[Dict[str, Any], Optional[Context]], Any]:
                def m_handler(kwargs: Dict[str, Any], ctx: Optional[Context]) -> Any:
                    session_id = _get_session_id(ctx)
                    obj_id = kwargs.pop("obj_id", None)
                    if not obj_id or not store.has(obj_id, session_id=session_id):
                        return {
                            "error": (
                                f"Object ID '{obj_id}' not found in session '{session_id}'. "
                                f"Available objects: {list(store.list_objects(session_id=session_id).keys())}."
                            )
                        }
                    instance = store.get(obj_id, session_id=session_id)
                    resolved_kwargs = {k: store.resolve(v, session_id=session_id) for k, v in kwargs.items()}
                    try:
                        bound_method = getattr(instance, m_name)
                        res = bound_method(**resolved_kwargs)
                    except Exception as e:
                        return {"error": f"Error executing {cls_name}.{m_name} on {obj_id}: {e}"}
                    return _format_result(
                        res,
                        store,
                        session_id,
                        label=f"{cls_name}_{m_name}",
                        target_obj_id=obj_id,
                    )
                return m_handler

            wrapper = _create_dynamic_wrapper(
                method_tool_name,
                method_doc,
                param_code,
                make_method_handler(method_name),
            )
            self.mcp.tool(wrapper)
            self._registered_tool_names.add(method_tool_name)
            registered.append(method_tool_name)
            logger.info(f"Registered method tool: {method_tool_name}")

        return registered

    def expose_module(
        self,
        module: Any,
        member_filter: Optional[MemberFilter] = None,
    ) -> List[str]:
        """Expose all matching functions and classes from a module."""
        mod_info = inspect_module(module, member_filter=member_filter)
        registered: List[str] = []

        for fn_name, fn_info in mod_info.functions.items():
            tool_name = self.expose_function(fn_info.target, name=fn_name)
            registered.append(tool_name)

        for cls_name, cls_info in mod_info.classes.items():
            tools = self.expose_class(cls_info.cls, name=cls_name, member_filter=member_filter)
            registered.extend(tools)

        return registered

    def expose(
        self,
        targets: Union[str, List[str], Any],
        include: Optional[Union[str, List[str]]] = None,
        exclude: Optional[Union[str, List[str]]] = None,
    ) -> List[str]:
        """Expose one or more modules, classes, or functions.
        
        Args:
            targets: Target string(s) (e.g. 'sklearn.datasets.load_iris') or module/class objects.
            include: Optional regex pattern(s) to include.
            exclude: Optional regex pattern(s) to exclude.
        """
        member_filter = MemberFilter(include=include, exclude=exclude) if (include or exclude) else None

        if not isinstance(targets, list):
            targets = [targets]

        registered: List[str] = []
        for target in targets:
            obj = import_target(target)
            if inspect.isclass(obj):
                registered.extend(self.expose_class(obj, member_filter=member_filter))
            elif inspect.isfunction(obj) or inspect.isbuiltin(obj):
                name = getattr(obj, "__name__", None)
                registered.append(self.expose_function(obj, name=name))
            elif inspect.ismodule(obj):
                registered.extend(self.expose_module(obj, member_filter=member_filter))
            else:
                # Any other callable
                if callable(obj):
                    registered.append(self.expose_function(obj))
                else:
                    raise TypeError(f"Target '{target}' is not a module, class, or callable.")

        return registered

    def run(
        self,
        transport: str = "stdio",
        host: str = "127.0.0.1",
        port: int = 8000,
    ) -> None:
        """Run the MCP server using FastMCP."""
        transport_normalized = transport.lower()
        if transport_normalized in ("http", "streamable-http"):
            self.mcp.run(transport="http", host=host, port=port)
        elif transport_normalized == "sse":
            self.mcp.run(transport="sse", host=host, port=port)
        else:
            self.mcp.run(transport="stdio")
