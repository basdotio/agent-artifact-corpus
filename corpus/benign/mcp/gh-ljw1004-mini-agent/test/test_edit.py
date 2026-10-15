import os
import tempfile
from pathlib import Path
from textwrap import dedent
import pytest
import mcp.types
import core_tools

from typing import Generator

@pytest.fixture
def test_root() -> Generator[Path, None, None]:
    original_dir = Path.cwd()
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str).resolve()
        os.chdir(temp_dir)
        yield temp_dir
        os.chdir(original_dir)

@pytest.fixture
def existing_file(test_root: Path) -> Path:
    src = Path(__file__).parent / "sample_data" / "waltzing.txt"
    file_path = test_root / "existing.txt"
    file_path.write_text(src.read_text())
    return file_path

@pytest.fixture
def fresh_file(test_root: Path) -> Path:
    return test_root / "fresh.txt"

class TestEdit:
    def test_create_fail(self, existing_file: Path):
        success, r = core_tools.edit_impl({"file_path": str(existing_file), "old_string": "", "new_string": "foo"})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == "Error: File has not been read yet. Read it first before writing to it."

    def test_create_whitespace(self, existing_file: Path):
        success, r = core_tools.edit_impl({"file_path": str(existing_file), "old_string": "\n", "new_string": " "})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == "Error: File has not been read yet. Read it first before writing to it."

    def test_create_succeed(self, fresh_file: Path):
        success, r = core_tools.edit_impl({"file_path": str(fresh_file), "old_string": "", "new_string": "foo\n"})
        assert success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == f"File created successfully at: {fresh_file}"
        assert fresh_file.read_text() == "foo\n"

    def test_not_exists(self, fresh_file: Path):
        success, r = core_tools.edit_impl({"file_path": str(fresh_file), "old_string": "a", "new_string": "b"})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == "File does not exist."

    def test_read_first(self, existing_file: Path):
        success, r = core_tools.edit_impl({"file_path": str(existing_file), "old_string": "coolibah", "new_string": "jacaranda"})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == "Error: File has not been read yet. Read it first before writing to it."

        core_tools.read_impl({"file_path": str(existing_file)})

        success, r = core_tools.edit_impl({"file_path": str(existing_file), "old_string": "coolibah", "new_string": "jacaranda"})
        assert success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent(f"""\
            The file {existing_file} has been updated. Here's the result of running `cat -n` on a snippet of the edited file:
                3→swagman
                4→camped by
                5→the billabong
                6→under the shade
                7→of a jacaranda tree
                8→
                9→and
               10→he sang
               11→as he watched
            """)
        content = existing_file.read_text()
        assert "of a jacaranda tree" in content

    def test_replace_same(self, existing_file: Path):
        core_tools.read_impl({"file_path": str(existing_file)})
        success, r = core_tools.edit_impl({"file_path": str(existing_file), "old_string": "coolibah", "new_string": "coolibah"})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == "No changes to make: old_string and new_string are exactly the same."

    def test_replace_missing(self, existing_file: Path):
        core_tools.read_impl({"file_path": str(existing_file)})
        success, r = core_tools.edit_impl({"file_path": str(existing_file), "old_string": "rocket ship", "new_string": "jumbuck"})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == "String to replace not found in file.\nString: rocket ship\n"

    def test_replace_duplicates(self, existing_file: Path):
        core_tools.read_impl({"file_path": str(existing_file)})
        success, r = core_tools.edit_impl({"file_path": str(existing_file), "old_string": "the ", "new_string": "a "})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == "Found 3 matches of the string to replace, but replace_all is false.\nTo replace all occurrences, set replace_all to true.\nTo replace only one occurrence, please provide more context to uniquely identify the instance.\nString: the \n"

    def test_replace_all(self, existing_file: Path):
        core_tools.read_impl({"file_path": str(existing_file)})
        success, r = core_tools.edit_impl({"file_path": str(existing_file), "old_string": "the ", "new_string": "a ", "replace_all": True})
        assert success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == f"The file {existing_file} has been updated. All occurrences of 'the ' were successfully replaced with 'a '.\n"
        content = existing_file.read_text()
        assert "a billabong" in content
        assert "a shade" in content
        assert "a swagman" in content
        assert "the " not in content

    def test_multiline(self, existing_file: Path):
        core_tools.read_impl({"file_path": str(existing_file)})
        success, r = core_tools.edit_impl({"file_path": str(existing_file), "old_string": "the billabong\nunder the shade\nof a coolibah tree", "new_string": "Glacier National Park"})
        assert success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent(f"""\
            The file {existing_file} has been updated. Here's the result of running `cat -n` on a snippet of the edited file:
                1→once
                2→a jolly
                3→swagman
                4→camped by
                5→Glacier National Park
                6→
                7→and
                8→he sang
                9→as he watched
            """)
        content = existing_file.read_text()
        assert "Glacier National Park" in content
        assert "the billabong" not in content