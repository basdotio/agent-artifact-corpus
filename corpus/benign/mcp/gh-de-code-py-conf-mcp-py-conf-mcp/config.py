from dataclasses import dataclass, field
import logging
import os
from typing import Any, Mapping, Optional, Sequence

import yaml

from py_conf_mcp.config_typing import (
    FromPythonClassConfigDict,
    FromPythonFunctionConfigDict,
    InputConfigDict,
    ServerConfigDict,
    AppConfigDict,
    ToolDefinitionsConfigDict
)


LOGGER = logging.getLogger(__name__)


class EnvironmentVariables:
    CONFIG_FILE = 'CONFIG_FILE'


@dataclass(frozen=True)
class FromPythonFunctionConfig:
    name: str
    module: str
    key: str
    description: Optional[str] = None

    @staticmethod
    def from_dict(
        from_python_function_config_dict: FromPythonFunctionConfigDict
    ) -> 'FromPythonFunctionConfig':
        return FromPythonFunctionConfig(
            name=from_python_function_config_dict['name'],
            module=from_python_function_config_dict['module'],
            key=from_python_function_config_dict['key'],
            description=from_python_function_config_dict.get('description')
        )


@dataclass(frozen=True)
class FromPythonClassConfig:
    name: str
    module: str
    class_name: str
    description: Optional[str] = None
    init_parameters: Mapping[str, Any] = field(default_factory=dict)
    inputs: Mapping[str, InputConfigDict] = field(default_factory=dict)

    @staticmethod
    def from_dict(
        from_python_class_config_dict: FromPythonClassConfigDict
    ) -> 'FromPythonClassConfig':
        return FromPythonClassConfig(
            name=from_python_class_config_dict['name'],
            module=from_python_class_config_dict['module'],
            class_name=from_python_class_config_dict['className'],
            description=from_python_class_config_dict.get('description'),
            init_parameters=from_python_class_config_dict.get('initParameters', {}),
            inputs=from_python_class_config_dict.get('inputs', {})
        )


@dataclass(frozen=True)
class ToolDefinitionsConfig:
    from_python_function: Sequence[FromPythonFunctionConfig] = field(default_factory=list)
    from_python_class: Sequence[FromPythonClassConfig] = field(default_factory=list)

    @staticmethod
    def from_dict(
        tool_definitions_config_dict: ToolDefinitionsConfigDict
    ) -> 'ToolDefinitionsConfig':
        return ToolDefinitionsConfig(
            from_python_function=list(map(
                FromPythonFunctionConfig.from_dict,
                tool_definitions_config_dict.get('fromPythonFunction', [])
            )),
            from_python_class=list(map(
                FromPythonClassConfig.from_dict,
                tool_definitions_config_dict.get('fromPythonClass', [])
            ))
        )

    def __bool__(self) -> bool:
        return bool(
            self.from_python_function
            or self.from_python_class
        )


@dataclass(frozen=True)
class ServerConfig:
    name: str
    tools: Sequence[str]

    @staticmethod
    def from_dict(server_config_dict: ServerConfigDict) -> 'ServerConfig':
        return ServerConfig(
            name=server_config_dict['name'],
            tools=server_config_dict['tools']
        )


@dataclass(frozen=True)
class AppConfig:
    tool_definitions: ToolDefinitionsConfig
    server: ServerConfig

    @staticmethod
    def from_dict(app_config_dict: AppConfigDict) -> 'AppConfig':
        return AppConfig(
            tool_definitions=ToolDefinitionsConfig.from_dict(
                app_config_dict.get('toolDefinitions', {})
            ),
            server=ServerConfig.from_dict(app_config_dict['server'])
        )


def get_app_config_file() -> str:
    return os.environ[EnvironmentVariables.CONFIG_FILE]


def load_app_config_from_file(config_file: str) -> AppConfig:
    LOGGER.info('Loading config from: %r', config_file)
    with open(config_file, 'r', encoding='utf-8') as config_fp:
        return AppConfig.from_dict(
            yaml.safe_load(config_fp)
        )


def load_app_config() -> AppConfig:
    return load_app_config_from_file(get_app_config_file())
