import os
import tempfile
import shutil
from pathlib import Path
from textwrap import dedent
from typing import Generator
import pytest
import mcp.types
import core_tools

def sortlines(text: str) -> str:
    """In a multiline string, this sorts all adjoining groups of lines that start with a slash (/)."""
    acc: list[str | list[str]] = []
    for line in text.splitlines(keepends=True):
        if line.startswith("/"):
            if len(acc) == 0 or isinstance(acc[-1], str):
                acc.append([])
            assert isinstance(acc[-1], list)
            acc[-1].append(line)
        else:
            acc.append(line)
    parts = [part if isinstance(part, str) else ''.join(sorted(part)) for part in acc]
    return ''.join(parts)

@pytest.fixture(scope="session")
def grep_root_dir(tmp_path_factory: pytest.TempPathFactory) -> Generator[Path, None, None]:
    original_dir = Path.cwd()
    # The tests operate on a modified version of test/sample_data/grep_root.
    # We'll start by copying the original into a temporary lication
    tmp_parent = tmp_path_factory.mktemp("tmp_sample_data")
    tmp_root = tmp_parent / "grep_root"
    src_root = (Path(__file__).parent.absolute() / "sample_data" / "grep_root").resolve()
    shutil.copytree(src_root, tmp_root)

    # Modification 1: any file named FOR_TEST_xyz gets renamed to just xyz
    for path in tmp_root.glob("FOR_TEST_*"):
        path.rename(path.parent / path.name.replace("FOR_TEST_", ""))

    # Modification 2: we create two symlinks
    (tmp_root / "valid_symlink.txt").symlink_to("file1.txt")
    (tmp_root / "broken_symlink.txt").symlink_to("nonexistent_file.txt")

    os.chdir(tmp_root)
    yield tmp_root
    os.chdir(original_dir)

@pytest.fixture(scope="session")
def permissions_test_dir() -> Generator[Path, None, None]:
    original_dir = Path.cwd()
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str).resolve()
        os.chdir(temp_dir)
        
        (temp_dir / "no_read.txt").write_text("This file contains the unreadable pattern.\nShould not be searchable due to read permissions.\n")
        (temp_dir / "readable.txt").write_text("This file contains the readable pattern.\nShould be found normally.\n")
        (temp_dir / "readable").mkdir()
        (temp_dir / "readable" / "readable_file.txt").write_text("This file contains the readable pattern.\nShould be found normally.\n")
        (temp_dir / "no_exec").mkdir()
        (temp_dir / "no_exec" / "hidden.txt").write_text("This file contains the secret pattern.\nShould not be found due to directory permissions.\n")
        
        (temp_dir / "no_read.txt").chmod(0o200) # -:-w-,---,---
        (temp_dir / "no_exec").chmod(0o644) # d:rw-,r--,r--

        yield temp_dir
    
    os.chdir(original_dir)

class TestPattern:
    def test_basic_literal_string_pattern(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the b"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            Found 6 files
            {grep_root_dir}/many_matches.txt
            {grep_root_dir}/node_modules/module.js
            {grep_root_dir}/subdir1/file.txt
            {grep_root_dir}/test.js
            {grep_root_dir}/file1.txt
            {grep_root_dir}/jabberwocky.txt
            """))

    def test_regex_pattern_with_character_class(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "[Tt]he b"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            Found 6 files
            {grep_root_dir}/many_matches.txt
            {grep_root_dir}/node_modules/module.js
            {grep_root_dir}/subdir1/file.txt
            {grep_root_dir}/test.js
            {grep_root_dir}/file1.txt
            {grep_root_dir}/jabberwocky.txt
            """))

    def test_pattern_that_matches_nothing(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "xyz123notfound"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No files found\n"

    def test_unicode_emoji_pattern(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "🌟"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            Found 1 file
            {grep_root_dir}/emoji.txt
            """)

class TestOutputMode:
    def test_content_mode_default_shows_matching_lines(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the a", "output_mode": "content"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            {grep_root_dir}/file1.txt:it is the aim of this file
            {grep_root_dir}/nested/deep/structure/deep.txt:Deep nested file with the answer.
            {grep_root_dir}/emoji.txt:Testing emoji patterns 🚀 with the answer.
            {grep_root_dir}/subdir2/other.js:const result = "the answer is here";
            """))

    def test_count_mode_shows_match_counts_per_file(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the a", "output_mode": "count"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            {grep_root_dir}/subdir2/other.js:1
            {grep_root_dir}/file1.txt:1
            {grep_root_dir}/nested/deep/structure/deep.txt:1
            {grep_root_dir}/emoji.txt:1

            Found 4 total occurrences across 4 files.
            """))

class TestPath:
    def test_path_points_to_specific_file(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the", "path": "file1.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            Found 1 file
            {grep_root_dir}/file1.txt
            """)

    def test_path_points_to_nonexistent_file(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the", "path": "nonexistent.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No files found\n"

    def test_path_points_to_directory(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the", "path": "subdir1"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            Found 1 file
            {grep_root_dir}/subdir1/file.txt
            """)

    def test_relative_path(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the a", "path": "../grep_root"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            Found 4 files
            {grep_root_dir}/nested/deep/structure/deep.txt
            {grep_root_dir}/subdir2/other.js
            {grep_root_dir}/emoji.txt
            {grep_root_dir}/file1.txt
            """))

class TestGlob:
    def test_simple_glob_pattern(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the a", "glob": "*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            Found 3 files
            {grep_root_dir}/nested/deep/structure/deep.txt
            {grep_root_dir}/emoji.txt
            {grep_root_dir}/file1.txt
            """))

    def test_brace_expansion_in_glob(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the", "glob": "*.{js,py}"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            Found 6 files
            {grep_root_dir}/node_modules/module.js
            {grep_root_dir}/__pycache__/cache.py
            {grep_root_dir}/subdir2/other.js
            {grep_root_dir}/test.py
            {grep_root_dir}/test.js
            {grep_root_dir}/venv/lib.py
            """))

    def test_directory_components_in_glob(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the", "glob": "subdir*/*.js"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            Found 1 file
            {grep_root_dir}/subdir2/other.js
            """)

class TestType:
    def test_javascript_file_type(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the", "type": "js"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            Found 3 files
            {grep_root_dir}/node_modules/module.js
            {grep_root_dir}/subdir2/other.js
            {grep_root_dir}/test.js
            """))

class TestTypeGlobConflicts:
    def test_both_type_js_and_glob_py_specified(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the", "type": "js", "glob": "*.py"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            Found 3 files
            {grep_root_dir}/test.py
            {grep_root_dir}/__pycache__/cache.py
            {grep_root_dir}/venv/lib.py
            """))

class TestCaseInsensitive:
    def test_case_sensitive_search_default(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "THE"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            Found 2 files
            {grep_root_dir}/subdir2/other.js
            {grep_root_dir}/test.py
            """))

    def test_case_insensitive_search(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "THE B", "-i": True})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            Found 6 files
            {grep_root_dir}/many_matches.txt
            {grep_root_dir}/node_modules/module.js
            {grep_root_dir}/subdir1/file.txt
            {grep_root_dir}/test.js
            {grep_root_dir}/file1.txt
            {grep_root_dir}/jabberwocky.txt
            """))

    def test_explicit_false_value(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "THE", "-i": False, "output_mode": "content"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            {grep_root_dir}/test.py:    value = "THE VALUE"
            {grep_root_dir}/subdir2/other.js:    return "THE ANSWER";
            """))

    def test_invalid_boolean_type_string(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "test", "-i": "true", "output_mode": "content"})
        assert not isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "Error: the parameter `-i` type is expected as `boolean` but provided as `str`\n"

class TestLineNumbers:
    def test_line_numbers_with_content_mode(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the", "output_mode": "content", "-n": True, "path": "file1.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent("""\
            1:it is the aim of this file
            2:to provide the best opportunity
            3:for the grep and ls tools
            4:to find the desired answers
            """)

    def test_explicit_false_value(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "test ", "-n": False, "output_mode": "content"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            {grep_root_dir}/multiline.txt:This is a test for
            {grep_root_dir}/newline_content.txt:test pattern here
            {grep_root_dir}/many_matches.txt:the best the greatest the most the wonderful the
            {grep_root_dir}/special chars/test dir/spaced.txt:test pattern here
            """))

class TestContextLines:
    def test_before_and_after_context(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "best", "output_mode": "content", "-A": 1, "-B": 1, "path": "file1.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent("""\
            it is the aim of this file
            to provide the best opportunity
            for the grep and ls tools
            """)

    def test_zero_context_lines(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "target", "-A": 0, "output_mode": "content", "-n": True})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No matches found\n"

    def test_negative_context_value(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "target", "-A": -1, "output_mode": "content", "-n": True})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No matches found\n"

class TestHeadLimit:
    def test_limit_content_mode(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the", "output_mode": "content", "head_limit": 5, "path": "jabberwocky.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent("""\
            'Twas brillig, and the slithy toves
            Did gyre and gimble in the wabe:
            All mimsy were the borogoves,
            And the mome raths outgrabe.
            "Beware the Jabberwock, my son!
            """)

    def test_zero_head_limit(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the a", "head_limit": 0})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No files found\n"

    def test_very_large_head_limit(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the a", "head_limit": 2000})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            Found 4 files
            {grep_root_dir}/nested/deep/structure/deep.txt
            {grep_root_dir}/subdir2/other.js
            {grep_root_dir}/emoji.txt
            {grep_root_dir}/file1.txt
            """))

class TestMultiline:
    def test_multiline_pattern_without_multiline_flag(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "Start.*End", "path": "multiline.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No files found\n"

    def test_multiline_pattern_with_multiline_flag(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "Start.*End", "multiline": True, "path": "multiline.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            Found 1 file
            {grep_root_dir}/multiline.txt
            """)

    def test_multiline_with_content_output(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "Start.*End", "multiline": True, "output_mode": "content", "path": "multiline.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent("""\
            Start block
            the content here
            is important
            End block
            """)

class TestErrorHandling:
    def test_missing_required_parameter(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({})
        assert not isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "Error: The required parameter `pattern` is missing.\n"

    def test_invalid_extra_parameters(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "test", "invalid_param": "should_be_ignored"})
        assert not isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "Error: an unexpected parameter `invalid_param` was provided.\n"

    def test_invalid_regex_pattern(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "[unclosed_bracket"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No files found\n"

    def test_nonexistent_path(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "test", "path": "/nonexistent/directory/path"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No files found\n"

class TestEdgeCases:
    def test_search_in_binary_file(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the", "path": "binary.dat", "output_mode": "content"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == 'binary file matches (found "\\0" byte around offset 15)\n'

    def test_c_parameter_context_around(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "best", "output_mode": "content", "-C": 2, "path": "file1.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent("""\
            it is the aim of this file
            to provide the best opportunity
            for the grep and ls tools
            to find the desired answers
            """)

    def test_line_numbers_without_content_mode(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the", "-n": True, "path": "file1.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            Found 1 file
            {grep_root_dir}/file1.txt
            """)

    def test_double_star_recursive_glob(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the a", "glob": "**/*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            Found 3 files
            {grep_root_dir}/nested/deep/structure/deep.txt
            {grep_root_dir}/emoji.txt
            {grep_root_dir}/file1.txt
            """))

    def test_parent_directory_pattern_not_supported(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": ".", "glob": "../*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No files found\n"

    def test_malformed_glob_unclosed_bracket(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "test", "glob": "["})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No files found\n"

    def test_character_range(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": ".", "glob": "single_char_[a-z].txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            Found 2 files
            {grep_root_dir}/single_char_z.txt
            {grep_root_dir}/single_char_a.txt
            """))

    def test_path_with_special_characters(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "test pattern", "path": "special chars/test dir"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            Found 1 file
            {grep_root_dir}/special chars/test dir/spaced.txt
            """)

    def test_unicode_in_path(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "unicode pattern", "path": "unicode_文件名.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            Found 1 file
            {grep_root_dir}/unicode_文件名.txt
            """)

    def test_symlink_handling(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "grep and ls tools", "path": "valid_symlink.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            Found 1 file
            {grep_root_dir}/file1.txt
            """)

    def test_broken_symlink(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "grep and ls tools", "path": "broken_symlink.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No files found\n"

    def test_empty_path(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "test pattern", "path": ""})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            Found 2 files
            {grep_root_dir}/newline_content.txt
            {grep_root_dir}/special chars/test dir/spaced.txt
            """))

class TestOutputFormatEdgeCases:
    def test_count_mode_with_single_file_bug(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the", "output_mode": "count", "path": "one_match.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "1\n\nFound 0 total occurrences across 0 files.\n"

    def test_count_mode_counts_lines_not_occurrences(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the", "output_mode": "count", "path": "many_matches.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "3\n\nFound 0 total occurrences across 0 files.\n"

class TestParameterCombinations:
    def test_all_parameters_in_content_mode(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({
            "pattern": "the a", 
            "output_mode": "content", 
            "-i": True, 
            "-n": True, 
            "-C": 1, 
            "type": "js"
        })
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            {grep_root_dir}/subdir2/other.js:1:const result = "the answer is here";
            {grep_root_dir}/subdir2/other.js-2-function findThe() {{
            {grep_root_dir}/subdir2/other.js:3:    return "THE ANSWER";
            {grep_root_dir}/subdir2/other.js-4-}}
            """)

    def test_glob_vs_type_precedence(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the", "output_mode": "content", "type": "js", "glob": "*.py"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            {grep_root_dir}/__pycache__/cache.py:# Cache file with the pattern
            {grep_root_dir}/__pycache__/cache.py:cached_value = "the cached result"
            {grep_root_dir}/venv/lib.py:# Virtual env with the library
            {grep_root_dir}/venv/lib.py:virtual_env = "the virtual environment"
            {grep_root_dir}/test.py:    print("the result")
            {grep_root_dir}/test.py:# the comment here
            """))

    def test_context_parameters_ignored_in_non_content_modes(self, grep_root_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the a", "output_mode": "files_with_matches", "-n": True, "-C": 2})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            Found 4 files
            {grep_root_dir}/nested/deep/structure/deep.txt
            {grep_root_dir}/subdir2/other.js
            {grep_root_dir}/emoji.txt
            {grep_root_dir}/file1.txt
            """))

class TestPermissions:
    def test_directory_without_execute_permission(self, permissions_test_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "secret", "path": str(permissions_test_dir / "no_exec")})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No files found\n"

    def test_file_without_read_permission(self, permissions_test_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "unreadable", "path": str(permissions_test_dir / "no_read.txt")})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No files found\n"

    def test_mixed_permissions_in_directory(self, permissions_test_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the", "path": str(permissions_test_dir)})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            Found 2 files
            {permissions_test_dir}/readable.txt
            {permissions_test_dir}/readable/readable_file.txt
            """))

    def test_glob_pattern_with_permission_issues(self, permissions_test_dir: Path):
        isOk, result = core_tools.grep_impl({"pattern": "the", "glob": "**/*.txt", "path": str(permissions_test_dir)})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == sortlines(dedent(f"""\
            Found 2 files
            {permissions_test_dir}/readable.txt
            {permissions_test_dir}/readable/readable_file.txt
            """))