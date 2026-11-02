"""
Configuration Settings for Shell MCP Server
========================================

This module defines the settings and configuration options for the shell MCP server.
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List, Dict
import os


class Settings(BaseSettings):
    """
    Application settings class using pydantic_settings.

    Attributes:
        APP_NAME (str): Name of the application
        APP_VERSION (str): Current version of the application
        COMMAND_TIMEOUT (int): Timeout for command execution in seconds
        ALLOWED_DIRECTORIES (List[str]): List of directories where commands can be executed
        ALLOWED_SHELLS (Dict[str, str]): Dictionary of shell names to their paths
    """

    APP_NAME: str = "shell-mcp-server"
    APP_VERSION: str = "0.1.0"
    COMMAND_TIMEOUT: int = 30
    ALLOWED_DIRECTORIES: List[str] = []
    ALLOWED_SHELLS: Dict[str, str] = {}

    def __init__(self, directories: List[str], shells: Dict[str, str]):
        super().__init__()
        self.ALLOWED_DIRECTORIES = [os.path.abspath(d) for d in directories]
        self.ALLOWED_SHELLS = shells

    def is_path_allowed(self, path: str) -> bool:
        """Check if a path is within any of the allowed directories."""
        abs_path = os.path.abspath(path)
        return any(
            abs_path.startswith(allowed_dir) for allowed_dir in self.ALLOWED_DIRECTORIES
        )

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")
