import os
import sys
import tempfile
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import (
    PROMPTS_FOLDER_ENV,
    get_prompt,
    get_prompt_file,
    list_prompts,
    load_prompts,
)


class TestLoadPrompts:
    """Test cases for the load_prompts function."""

    def test_load_prompts_with_valid_directory(self):
        """Test loading prompts from a valid directory with .txt files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test prompt files
            test_files = {
                "hello_world.txt": "Hello, World!",
                "goodbye.txt": "Goodbye!",
                "test_prompt.txt": "This is a test prompt.",
            }

            for filename, content in test_files.items():
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            # Mock the PROMPTS_FOLDER to point to our temp directory
            with patch("main.PROMPTS_FOLDER", temp_dir):
                prompts = load_prompts()

                assert len(prompts) == 3
                assert "hello world" in prompts
                assert "goodbye" in prompts
                assert "test prompt" in prompts
                assert prompts["hello world"] == "Hello, World!"
                assert prompts["goodbye"] == "Goodbye!"
                assert prompts["test prompt"] == "This is a test prompt."

    def test_load_prompts_with_nonexistent_directory(self):
        """Test loading prompts when directory doesn't exist."""
        with patch("main.PROMPTS_FOLDER", "/nonexistent/directory"):
            prompts = load_prompts()
            assert prompts == {}

    def test_load_prompts_with_empty_directory(self):
        """Test loading prompts from an empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("main.PROMPTS_FOLDER", temp_dir):
                prompts = load_prompts()
                assert prompts == {}

    def test_load_prompts_ignores_non_txt_files(self):
        """Test that non-.txt files are ignored."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files with different extensions
            files = {
                "prompt.txt": "Valid prompt",
                "readme.md": "This should be ignored",
                "config.json": "This should also be ignored",
                "script.py": "This should be ignored too",
            }

            for filename, content in files.items():
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            with patch("main.PROMPTS_FOLDER", temp_dir):
                prompts = load_prompts()

                assert len(prompts) == 1
                assert "prompt" in prompts
                assert prompts["prompt"] == "Valid prompt"

    def test_load_prompts_handles_file_read_errors(self):
        """Test that file read errors are handled gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a valid file
            valid_file = os.path.join(temp_dir, "valid.txt")
            with open(valid_file, "w", encoding="utf-8") as f:
                f.write("Valid content")

            # Create an invalid file (we'll mock it to raise an exception)
            invalid_file = os.path.join(temp_dir, "invalid.txt")
            with open(invalid_file, "w", encoding="utf-8") as f:
                f.write("This will cause an error")

            with patch("main.PROMPTS_FOLDER", temp_dir):
                # Mock open to raise an exception for the invalid file
                original_open = open

                def mock_open_func(file_path, *args, **kwargs):
                    if "invalid.txt" in file_path:
                        raise IOError("Mocked file read error")
                    return original_open(file_path, *args, **kwargs)

                with patch("builtins.open", side_effect=mock_open_func):
                    prompts = load_prompts()

                    # Should only load the valid file
                    assert len(prompts) == 1
                    assert "valid" in prompts
                    assert prompts["valid"] == "Valid content"

    def test_load_prompts_with_file_not_directory(self):
        """Test loading prompts when PROMPTS_FOLDER points to a file instead of directory."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_file.write("This is a file, not a directory")
            temp_file_path = temp_file.name

        try:
            with patch("main.PROMPTS_FOLDER", temp_file_path):
                prompts = load_prompts()
                assert prompts == {}
        finally:
            os.unlink(temp_file_path)


class TestListPrompts:
    """Test cases for the list_prompts function."""

    def test_list_prompts_returns_prompt_names(self):
        """Test that list_prompts returns a list of prompt names."""
        mock_prompts = {
            "hello world": "Hello, World!",
            "goodbye": "Goodbye!",
            "test prompt": "This is a test.",
        }

        with patch("main.load_prompts", return_value=mock_prompts):
            result = list_prompts()

            assert isinstance(result, list)
            assert len(result) == 3
            assert "hello world" in result
            assert "goodbye" in result
            assert "test prompt" in result

    def test_list_prompts_empty_directory(self):
        """Test list_prompts with no prompts available."""
        with patch("main.load_prompts", return_value={}):
            result = list_prompts()

            assert isinstance(result, list)
            assert len(result) == 0


class TestGetPrompt:
    """Test cases for the get_prompt function."""

    def test_get_prompt_existing_prompt(self):
        """Test getting an existing prompt."""
        mock_prompts = {"hello world": "Hello, World!", "goodbye": "Goodbye!"}

        with patch("main.load_prompts", return_value=mock_prompts):
            result = get_prompt("hello world")
            assert result == "Hello, World!"

            result = get_prompt("goodbye")
            assert result == "Goodbye!"

    def test_get_prompt_nonexistent_prompt(self):
        """Test getting a non-existent prompt."""
        mock_prompts = {"hello world": "Hello, World!"}

        with patch("main.load_prompts", return_value=mock_prompts):
            result = get_prompt("nonexistent")
            assert result == "Prompt 'nonexistent' not found."

    def test_get_prompt_empty_prompts(self):
        """Test getting a prompt when no prompts are available."""
        with patch("main.load_prompts", return_value={}):
            result = get_prompt("any_prompt")
            assert result == "Prompt 'any_prompt' not found."


class TestGetPromptFile:
    """Test cases for the get_prompt_file function."""

    def test_get_prompt_file_returns_all_prompts(self):
        """Test that get_prompt_file returns all prompts as a dictionary."""
        mock_prompts = {
            "hello world": "Hello, World!",
            "goodbye": "Goodbye!",
            "test prompt": "This is a test.",
        }

        with patch("main.load_prompts", return_value=mock_prompts):
            result = get_prompt_file()

            assert isinstance(result, dict)
            assert result == mock_prompts

    def test_get_prompt_file_empty_prompts(self):
        """Test get_prompt_file with no prompts available."""
        with patch("main.load_prompts", return_value={}):
            result = get_prompt_file()

            assert isinstance(result, dict)
            assert result == {}


class TestEnvironmentVariables:
    """Test cases for environment variable handling."""

    def test_prompts_folder_env_variable(self):
        """Test that PROMPTS_FOLDER environment variable is respected."""
        custom_path = "/custom/prompts/path"

        with patch.dict(os.environ, {PROMPTS_FOLDER_ENV: custom_path}):
            # Re-import to get the updated PROMPTS_FOLDER value
            import importlib

            import main

            importlib.reload(main)

            assert main.PROMPTS_FOLDER == custom_path

    def test_prompts_folder_default_value(self):
        """Test that PROMPTS_FOLDER defaults to prompts directory when env var is not set."""
        # Ensure the environment variable is not set
        with patch.dict(os.environ, {}, clear=True):
            # Re-import to get the updated PROMPTS_FOLDER value
            import importlib

            import main

            importlib.reload(main)

            expected_path = os.path.join(os.path.dirname(main.__file__), "prompts")
            assert main.PROMPTS_FOLDER == expected_path


class TestIntegration:
    """Integration tests that test multiple components together."""

    def test_full_workflow(self):
        """Test the complete workflow from loading to retrieving prompts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test prompt files
            test_files = {
                "greeting.txt": "Hello there!",
                "farewell.txt": "See you later!",
                "help_request.txt": "Can you help me with this?",
            }

            for filename, content in test_files.items():
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            with patch("main.PROMPTS_FOLDER", temp_dir):
                # Test list_prompts
                prompt_names = list_prompts()
                assert len(prompt_names) == 3
                assert "greeting" in prompt_names
                assert "farewell" in prompt_names
                assert "help request" in prompt_names

                # Test get_prompt for each prompt
                assert get_prompt("greeting") == "Hello there!"
                assert get_prompt("farewell") == "See you later!"
                assert get_prompt("help request") == "Can you help me with this?"

                # Test get_prompt_file
                all_prompts = get_prompt_file()
                assert len(all_prompts) == 3
                assert all_prompts["greeting"] == "Hello there!"
                assert all_prompts["farewell"] == "See you later!"
                assert all_prompts["help request"] == "Can you help me with this?"

                # Test non-existent prompt
                assert get_prompt("nonexistent") == "Prompt 'nonexistent' not found."
