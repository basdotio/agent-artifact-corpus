from typing import Generator
from pathlib import Path
from textwrap import dedent
import tempfile
import pytest
import mcp.types
import core_tools

@pytest.fixture
def file1() -> Generator[Path, None, None]:
    with tempfile.NamedTemporaryFile(mode='w') as f:
        content = (Path(__file__).parent / "sample_data" / "waltzing.txt").read_text()
        Path(f.name).write_text(content)
        core_tools.read_impl({"file_path": f.name})
        yield Path(f.name)

class TestMultiEdit:
    def test_basic_successful_single_edit(self, file1: Path):
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "jolly", "new_string": "happy"}
        ]})
        assert success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent(f"""\
            Applied 1 edit to {file1}:
            1. Replaced "jolly" with "happy"
            """)
        assert "once\na happy\nswagman" in Path(file1).read_text()

    def test_multiple_successful_edits_with_replace_all(self, file1: Path):
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "jolly", "new_string": "happy"},
            {"old_string": "swagman", "new_string": "traveler", "replace_all": True},
            {"old_string": "billabong", "new_string": "waterhole", "replace_all": True}
        ]})
        assert success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent(f"""\
            Applied 3 edits to {file1}:
            1. Replaced "jolly" with "happy"
            2. Replaced "swagman" with "traveler"
            3. Replaced "billabong" with "waterhole"
            """)

    def test_identical_old_string_and_new_string(self, file1: Path):
        # The tool explicitly checks for and rejects no-op edits where old_string equals new_string.
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "jolly", "new_string": "jolly"}
        ]})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == "No changes to make: old_string and new_string are exactly the same."

    def test_empty_old_string(self, file1: Path):
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "", "new_string": "hello"}
        ]})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == "Error: old_string cannot be empty."

    def test_empty_new_string_deletion(self, file1: Path):
        # Empty new_string successfully deletes the matched text. This is a useful feature for removing content.
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "jolly", "new_string": ""}
        ]})
        assert success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent(f"""\
            Applied 1 edit to {file1}:
            1. Replaced "jolly" with ""
            """)

    def test_both_old_string_and_new_string_empty(self, file1: Path):
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "", "new_string": ""}
        ]})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == "Error: old_string cannot be empty."

    def test_newline_as_old_string_without_replace_all(self, file1: Path):
        # The tool correctly identifies newline characters and counts all instances (32 newlines in the file). The error message shows the literal newline character.
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "\n", "new_string": " "}
        ]})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent("""\
            Found 32 matches of the string to replace, but replace_all is false.
            To replace all occurrences, set replace_all to true.
            To replace only one occurrence, please provide more context to uniquely identify the instance.
            String: 

            """)

    def test_newline_as_old_string_with_replace_all(self, file1: Path):
        # With replace_all=true, all newlines were successfully replaced with spaces, effectively converting the multi-line file to a single line.
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "\n", "new_string": " ", "replace_all": True}
        ]})
        assert success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent(f"""\
            Applied 1 edit to {file1}:
            1. Replaced "
            " with " "
            """)

    def test_multiline_old_string(self, file1: Path):
        # MultiEdit successfully handles multiline strings. The output shows literal newlines in the replacement confirmation.
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "once\na jolly\nswagman", "new_string": "once upon a time\na happy\ntraveler"}
        ]})
        assert success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent(f"""\
            Applied 1 edit to {file1}:
            1. Replaced "once
            a jolly
            swagman" with "once upon a time
            a happy
            traveler"
            """)

    def test_empty_edits_array(self, file1: Path):
        # The tool uses schema validation to require at least one edit in the array. This prevents empty operations.
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": []})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == "Error: at least one edit is required."

    def test_atomicity_mix_of_valid_and_invalid_edits(self, file1: Path):
        # Verified that the file remained unchanged - edits are atomic (all-or-nothing).
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "jolly", "new_string": "happy"},
            {"old_string": "DOESNOTEXIST", "new_string": "xyz"},
            {"old_string": "swagman", "new_string": "traveler", "replace_all": True}
        ]})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent("""\
            String to replace not found in file.
            String: DOESNOTEXIST
            """)

    def test_sequential_failure_first_edit_fails(self, file1: Path):
        # When the first edit fails, subsequent edits are not attempted.
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "DOESNOTEXIST", "new_string": "xyz"},
            {"old_string": "jolly", "new_string": "happy"},
            {"old_string": "swagman", "new_string": "traveler", "replace_all": True}
        ]})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent("""\
            String to replace not found in file.
            String: DOESNOTEXIST
            """)

    def test_overlapping_edits_edit_1_output_would_be_edit_2_input(self, file1: Path):
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "jolly", "new_string": "jolly jolly"},
            {"old_string": "jolly jolly", "new_string": "very happy"}
        ]})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent("""\
            String to replace not found in file.
            String: jolly jolly
            """)

    def test_overlapping_edits_edit_1_creates_text_for_edit_2(self, file1: Path):
        # All edits are validated against the original file content before any are applied. Edits do NOT see the results of previous edits.
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "jolly", "new_string": "happy"},
            {"old_string": "happy", "new_string": "very happy"}
        ]})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent("""\
            String to replace not found in file.
            String: happy
            """)

    def test_successful_sequential_edits_on_different_parts(self, file1: Path):
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "once", "new_string": "Once"},
            {"old_string": "a jolly", "new_string": "a happy"},
            {"old_string": "swagman", "new_string": "traveler", "replace_all": True}
        ]})
        assert success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent(f"""\
            Applied 3 edits to {file1}:
            1. Replaced "once" with "Once"
            2. Replaced "a jolly" with "a happy"
            3. Replaced "swagman" with "traveler"
            """)

    def test_conflicting_overlapping_text_regions(self, file1: Path):
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "a jolly\nswagman", "new_string": "a happy\ntraveler"},
            {"old_string": "jolly\nswagman\ncamped", "new_string": "merry\nvagabond\nrested"}
        ]})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent("""\
            String to replace overlaps with an earlier edit.
            String: jolly
            swagman
            camped
            """)

    def test_replace_all_parameter_explicit_false(self, file1: Path):
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "billabong", "new_string": "waterhole", "replace_all": False}
        ]})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent("""\
            Found 2 matches of the string to replace, but replace_all is false.
            To replace all occurrences, set replace_all to true.
            To replace only one occurrence, please provide more context to uniquely identify the instance.
            String: billabong
            """)

    def test_replace_all_parameter_omitted_default(self, file1: Path):
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "billabong", "new_string": "waterhole"}
        ]})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent("""\
            Found 2 matches of the string to replace, but replace_all is false.
            To replace all occurrences, set replace_all to true.
            To replace only one occurrence, please provide more context to uniquely identify the instance.
            String: billabong
            """)

    def test_replace_all_parameter_true(self, file1: Path):
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "billabong", "new_string": "waterhole", "replace_all": True}
        ]})
        assert success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent(f"""\
            Applied 1 edit to {file1}:
            1. Replaced "billabong" with "waterhole"
            """)

    def test_non_existent_old_string_single_edit(self, file1: Path):
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "DEFINITELY_NOT_IN_FILE", "new_string": "something else"}
        ]})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent("""\
            String to replace not found in file.
            String: DEFINITELY_NOT_IN_FILE
            """)

    def test_duplicate_edits_same_edit_twice(self, file1: Path):
        # This fails because edits are applied sequentially. After the first edit replaces "jolly" with "happy", the second edit can't find "jolly" anymore.
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "jolly", "new_string": "happy"},
            {"old_string": "jolly", "new_string": "happy"}
        ]})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent("""\
            String to replace overlaps with an earlier edit.
            String: jolly
            """)

    def test_second_edit_old_string_identical_to_first_edit_new_string(self, file1: Path):
        # MultiEdit has protection against edits that would interfere with each other. When the old_string of a later edit exactly matches (or is a substring of) the new_string of an earlier edit, it blocks the operation to prevent unexpected behavior.
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "till", "new_string": "the", "replace_all": True},
            {"old_string": "the", "new_string": "some", "replace_all": True}
        ]})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == "Cannot edit file: old_string is a substring of a new_string from a previous edit."

    def test_second_edit_old_string_is_substring_of_first_edit_new_string(self, file1: Path):
        # This confirms the protection mechanism also applies to substring relationships, not just exact matches. The tool detects that "he" is a substring of "the" and prevents the operation.
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "till", "new_string": "the"},
            {"old_string": "he", "new_string": "we", "replace_all": True}
        ]})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == "Cannot edit file: old_string is a substring of a new_string from a previous edit."

    def test_first_edit_creates_concatenation_second_edit_operates_on_result(self, file1: Path):
        # This experiment demonstrates that edits are validated against the original file content, not the result of previous edits. Even though removing " waited " from "and waited till" would create "andtill", the second edit fails because "andtill" doesn't exist in the original file.
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": " waited ", "new_string": ""},
            {"old_string": "andtill", "new_string": "foobar"}
        ]})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent("""\
            String to replace not found in file.
            String: andtill
            """)

    def test_invalid_edits_parameter_type(self, file1: Path):
        # The tool has proper type validation and provides clear error messages when the wrong parameter types are provided.
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": 42})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == "Error: edits must be a list of objects with old_string, new_string, and optional replace_all."

    def test_multiple_edits_where_one_has_duplicate_matches(self, file1: Path):
        # When any edit in the array fails validation, the entire operation fails.
        # The error message helpfully suggests using replace_all for multiple matches.
        success, r = core_tools.multiedit_impl({"file_path": str(file1), "edits": [
            {"old_string": "jolly", "new_string": "happy"},
            {"old_string": "swagman", "new_string": "traveler"},
            {"old_string": "billabong", "new_string": "waterhole"}
        ]})
        assert not success
        assert isinstance(r[0], mcp.types.TextContent)
        assert r[0].text == dedent("""\
            Found 2 matches of the string to replace, but replace_all is false.
            To replace all occurrences, set replace_all to true.
            To replace only one occurrence, please provide more context to uniquely identify the instance.
            String: swagman
            """)
