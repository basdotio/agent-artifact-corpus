"""Test configuration and fixtures for shell MCP server tests."""

import os
import pytest
import tempfile
from typing import Dict, List, Generator

@pytest.fixture
def temp_directory() -> Generator[str, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def allowed_directories(temp_directory: str) -> List[str]:
    """Create a list of allowed directories for testing."""
    project_dir = os.path.join(temp_directory, "project")
    other_dir = os.path.join(temp_directory, "other")
    os.makedirs(project_dir)
    os.makedirs(other_dir)
    return [project_dir, other_dir]

@pytest.fixture
def test_shells() -> Dict[str, str]:
    """Define test shells based on the platform."""
    if os.name == 'nt':  # Windows
        return {
            'cmd': 'cmd.exe',
            'powershell': 'powershell.exe'
        }
    else:  # Unix-like
        return {
            'bash': '/bin/bash',
            'sh': '/bin/sh'
        }
