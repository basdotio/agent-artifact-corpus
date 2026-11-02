"""Tests for the configuration module."""

import os
import tempfile
import pytest
from shell_mcp_server.config import Settings


def test_settings_initialization(allowed_directories: list[str], test_shells: dict[str, str]):
    """Test that Settings can be initialized with directories and shells."""
    settings = Settings(directories=allowed_directories, shells=test_shells)
    
    assert settings.ALLOWED_DIRECTORIES == [os.path.abspath(d) for d in allowed_directories]
    assert settings.ALLOWED_SHELLS == test_shells


def test_is_path_allowed(allowed_directories: list[str], test_shells: dict[str, str]):
    """Test path validation."""
    settings = Settings(directories=allowed_directories, shells=test_shells)
    
    # Test allowed paths
    assert settings.is_path_allowed(allowed_directories[0])
    assert settings.is_path_allowed(os.path.join(allowed_directories[0], "subdir"))
    
    # Test disallowed paths
    with tempfile.TemporaryDirectory() as tmpdir:
        assert not settings.is_path_allowed(tmpdir)
        assert not settings.is_path_allowed("/some/random/path")


def test_command_timeout_setting(allowed_directories: list[str], test_shells: dict[str, str]):
    """Test command timeout configuration."""
    settings = Settings(directories=allowed_directories, shells=test_shells)
    assert settings.COMMAND_TIMEOUT == 30  # default value

    # Test with environment variable
    os.environ["COMMAND_TIMEOUT"] = "60"
    settings = Settings(directories=allowed_directories, shells=test_shells)
    assert settings.COMMAND_TIMEOUT == 60
    del os.environ["COMMAND_TIMEOUT"]