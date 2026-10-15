from typing import Any, Mapping, NotRequired, Sequence, TypedDict


class InputConfigDict(TypedDict):
    type: Any
    default: NotRequired[Any]
    enum: NotRequired[Sequence[Any]]
    title: NotRequired[str]
    description: NotRequired[str]


class FromPythonFunctionConfigDict(TypedDict):
    name: str
    module: str
    key: str
    description: NotRequired[str]


class FromPythonClassConfigDict(TypedDict):
    name: str
    module: str
    className: str
    description: NotRequired[str]
    initParameters: NotRequired[Mapping[str, Any]]
    inputs: NotRequired[Mapping[str, InputConfigDict]]


class ToolDefinitionsConfigDict(TypedDict):
    fromPythonFunction: NotRequired[Sequence[FromPythonFunctionConfigDict]]
    fromPythonClass: NotRequired[Sequence[FromPythonClassConfigDict]]


class ServerConfigDict(TypedDict):
    name: str
    tools: Sequence[str]


class AppConfigDict(TypedDict):
    toolDefinitions: NotRequired[ToolDefinitionsConfigDict]
    server: ServerConfigDict
