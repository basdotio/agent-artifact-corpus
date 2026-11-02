"""Tests for the shell MCP server functionality."""

import os
import pytest
import asyncio
from shell_mcp_server.server import run_shell_command, settings
from typing import List, Dict


@pytest.fixture(autouse=True)
def setup_test_settings(allowed_directories: List[str], test_shells: Dict[str, str]):
    """Configure test settings before each test."""
    settings.ALLOWED_DIRECTORIES = [os.path.abspath(d) for d in allowed_directories]
    settings.ALLOWED_SHELLS = test_shells
    return settings


@pytest.mark.asyncio
async def test_run_shell_command_success(allowed_directories: List[str], test_shells: Dict[str, str]):
    """Test successful shell command execution."""
    # Create a test file
    test_file = os.path.join(allowed_directories[0], "test.txt")
    with open(test_file, "w") as f:
        f.write("test content")
    
    # Test command execution
    shell_name = next(iter(test_shells.keys()))  # Get first shell
    if os.name == 'nt':
        command = 'type test.txt' if shell_name == 'cmd' else 'Get-Content test.txt'
    else:
        command = 'cat test.txt'
    
    result = await run_shell_command(shell_name, command, allowed_directories[0])
    
    assert result["exit_code"] == 0
    assert "test content" in result["stdout"]
    assert not result["stderr"]


@pytest.mark.asyncio
async def test_run_shell_command_invalid_directory(allowed_directories: List[str], test_shells: Dict[str, str]):
    """Test command execution in invalid directory."""
    shell_name = next(iter(test_shells.keys()))
    with pytest.raises(ValueError, match="is not in the allowed directories"):
        await run_shell_command(shell_name, "ls", "/invalid/directory")


@pytest.mark.asyncio
async def test_run_shell_command_invalid_shell(allowed_directories: List[str], test_shells: Dict[str, str]):
    """Test command execution with invalid shell."""
    with pytest.raises(ValueError, match="is not allowed"):
        await run_shell_command("invalid_shell", "ls", allowed_directories[0])


@pytest.mark.asyncio
async def test_run_shell_command_timeout(allowed_directories: List[str], test_shells: Dict[str, str]):
    """Test command timeout."""
    settings.COMMAND_TIMEOUT = 1
    
    shell_name = next(iter(test_shells.keys()))
    if os.name == 'nt':
        command = 'timeout 10' if shell_name == 'cmd' else 'Start-Sleep 10'
    else:
        command = 'sleep 10'
    
    with pytest.raises(TimeoutError):
        await run_shell_command(shell_name, command, allowed_directories[0])


@pytest.mark.asyncio
async def test_command_output_encoding(allowed_directories: List[str], test_shells: Dict[str, str]):
    """Test handling of non-ASCII command output."""
    shell_name = next(iter(test_shells.keys()))
    if os.name == 'nt':
        command = 'echo ñçé' if shell_name == 'cmd' else 'Write-Output "ñçé"'
    else:
        command = 'echo "ñçé"'
    
    result = await run_shell_command(shell_name, command, allowed_directories[0])
    
    assert result["exit_code"] == 0
    assert "ñçé" in result["stdout"].strip()


@pytest.mark.asyncio
async def test_concurrent_commands(allowed_directories: List[str], test_shells: Dict[str, str]):
    """Test running multiple commands concurrently."""
    shell_name = next(iter(test_shells.keys()))
    if os.name == 'nt':
        command = 'echo test' if shell_name == 'cmd' else 'Write-Output "test"'
    else:
        command = 'echo "test"'
    
    tasks = [
        run_shell_command(shell_name, command, allowed_directories[0])
        for _ in range(5)
    ]
    
    results = await asyncio.gather(*tasks)
    
    for result in results:
        assert result["exit_code"] == 0
        assert "test" in result["stdout"].strip()


@pytest.mark.asyncio
async def test_command_with_arguments(allowed_directories: List[str], test_shells: Dict[str, str]):
    """Test command execution with arguments."""
    shell_name = next(iter(test_shells.keys()))
    
    # Create test files
    for i in range(3):
        with open(os.path.join(allowed_directories[0], f"test{i}.txt"), "w") as f:
            f.write(f"content{i}")
    
    # Test with wildcards and arguments
    if os.name == 'nt':
        command = 'dir /b test*.txt' if shell_name == 'cmd' else 'Get-ChildItem test*.txt | Select-Object Name'
    else:
        command = 'ls test*.txt'
    
    result = await run_shell_command(shell_name, command, allowed_directories[0])
    
    assert result["exit_code"] == 0
    assert "test0.txt" in result["stdout"]
    assert "test1.txt" in result["stdout"]
    assert "test2.txt" in result["stdout"]