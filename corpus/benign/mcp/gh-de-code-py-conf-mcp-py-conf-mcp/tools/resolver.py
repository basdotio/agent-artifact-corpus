from abc import ABC, abstractmethod
from dataclasses import dataclass
import functools
import importlib
import inspect
import logging
from typing import Annotated, Any, Callable, Literal, Mapping, Optional, Sequence

import pydantic

from py_conf_mcp.config import (
    FromPythonClassConfig,
    FromPythonFunctionConfig,
    ToolDefinitionsConfig
)
from py_conf_mcp.config_typing import InputConfigDict


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Tool:
    tool_fn: Callable
    name: str
    description: Optional[str] = None


class ToolResolver(ABC):
    @abstractmethod
    def get_tool_by_name(self, tool_name: str) -> Tool:
        pass

    def get_tools_by_name(
        self,
        tool_names: Sequence[str]
    ) -> Sequence[Tool]:
        return [
            self.get_tool_by_name(tool_name)
            for tool_name in tool_names
        ]


class InvalidToolNameError(KeyError):
    pass


def get_tool_from_tool_class(
    tool_class: type[Tool],
    init_parameters: Mapping[str, Any],
    available_kwargs: Mapping[str, Any]
) -> Tool:
    parameters = inspect.signature(tool_class).parameters
    LOGGER.info('tool_class: %r, parameters: %r', tool_class, parameters)
    extra_kwargs = {
        key: value
        for key, value in available_kwargs.items()
        if key in parameters and key not in init_parameters
    }
    return tool_class(**init_parameters, **extra_kwargs)


def get_tool_from_python_tool_instance(
    config: FromPythonFunctionConfig
) -> Tool:
    tool_module = importlib.import_module(config.module)
    tool = getattr(tool_module, config.key)
    assert callable(tool)
    return Tool(
        tool_fn=tool,
        name=config.name,
        description=config.description
    )


def get_inspect_parameter_annotation_for_input_config_dict(
    input_config_dict: InputConfigDict
) -> Any:
    enum = input_config_dict.get('enum')
    if enum:
        return Literal[tuple(enum)]
    return input_config_dict.get('type')


def get_inspect_parameter_for_input_config_dict(
    input_name: str,
    input_config_dict: InputConfigDict
) -> inspect.Parameter:
    param_type = get_inspect_parameter_annotation_for_input_config_dict(
        input_config_dict
    )

    field = pydantic.Field(
        title=input_config_dict.get('title'),
        description=input_config_dict.get('description'),
        default=input_config_dict.get('default', ...)
    )

    return inspect.Parameter(
        name=input_name,
        kind=inspect.Parameter.KEYWORD_ONLY,
        annotation=Annotated[param_type, field],
        default=input_config_dict.get('default', inspect.Parameter.empty)
    )


def get_tool_function_with_dynamic_parameters(
    tool_fn: Callable,
    inputs: Mapping[str, InputConfigDict],
    tool_name: str
) -> Callable:
    LOGGER.info('inputs: %r', inputs)

    @functools.wraps(tool_fn)
    def wrapper(**kwargs):
        return tool_fn(**kwargs)

    parameters = [
        get_inspect_parameter_for_input_config_dict(
            input_name=input_name,
            input_config_dict=input_config_dict
        )
        for input_name, input_config_dict in inputs.items()
    ]
    wrapper.__signature__ = inspect.Signature(parameters)  # type: ignore[attr-defined]

    annotations = {}
    for param in parameters:
        annotations[param.name] = param.annotation
    LOGGER.debug('annotations: %r', annotations)
    wrapper.__annotations__ = annotations  # type: ignore[attr-defined]

    model = pydantic.create_model(  # type: ignore
        f"{tool_name}_Inputs",
        **{name: (annotation, ...) for name, annotation in annotations.items()}
    )
    json_schema = model.model_json_schema()

    LOGGER.debug('json_schema: %r', json_schema)

    wrapper.__get_pydantic_json_schema__ = lambda *_: json_schema  # type: ignore[attr-defined]

    return wrapper


def get_tool_from_python_class(
    config: FromPythonClassConfig
) -> Tool:
    tool_module = importlib.import_module(config.module)
    tool_class = getattr(tool_module, config.class_name)
    assert isinstance(tool_class, type)
    tool_fn = tool_class(**config.init_parameters)

    try:
        tool_fn = tool_fn.__call__
    except AttributeError:
        pass

    assert callable(tool_fn)
    if config.inputs is not None:
        tool_fn = get_tool_function_with_dynamic_parameters(
            tool_fn,
            config.inputs,
            tool_name=config.name
        )
    return Tool(
        tool_fn=tool_fn,
        name=config.name,
        description=config.description
    )


@dataclass(frozen=True)
class ConfigToolResolver(ToolResolver):
    tool_definitions_config: ToolDefinitionsConfig

    def get_tool_by_name(self, tool_name: str) -> Tool:
        for from_python_function_config in (
            self.tool_definitions_config.from_python_function
        ):
            if from_python_function_config.name == tool_name:
                return get_tool_from_python_tool_instance(from_python_function_config)
        for from_python_class_config in (
            self.tool_definitions_config.from_python_class
        ):
            if from_python_class_config.name == tool_name:
                return get_tool_from_python_class(from_python_class_config)
        raise InvalidToolNameError(f'Unrecognised tool: {repr(tool_name)}')
