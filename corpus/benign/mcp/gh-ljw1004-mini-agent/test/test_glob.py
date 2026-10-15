import os
import time
from pathlib import Path
from textwrap import dedent
import pytest
import mcp.types
import core_tools
import tempfile
from typing import Generator

def sortlines(text: str) -> str:
    return ''.join(sorted(text.splitlines(keepends=True)))

@pytest.fixture
def root() -> Generator[Path, None, None]:
    original_dir = Path.cwd()
    root = Path(__file__).parent / "sample_data" / "ls_test_root"
    os.chdir(root)
    yield root.resolve()
    os.chdir(original_dir)

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for tests that need to write files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir).resolve()

class TestGlob:
    def test_path_1(self, root: Path):
        isOk, result = core_tools.glob_impl({"path": ".", "pattern": "*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            {root}/file1.txt
            """)

    def test_basic_pattern_txt(self, root: Path):
        """Test basic pattern matching with *.txt"""
        isOk, result = core_tools.glob_impl({"pattern": "*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            {root}/file1.txt
            """)

    def test_recursive_pattern_txt(self, root: Path):
        """Test recursive pattern matching with **/*.txt"""
        isOk, result = core_tools.glob_impl({"pattern": "**/*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == dedent(f"""\
            {root}/dir1/subdir1/nested.txt
            {root}/dir1/test_file.txt
            {root}/dir2/nested/deep/deeply_nested.txt
            {root}/file1.txt
            """)

    def test_path_dot_pattern_txt(self, root: Path):
        """Test with path="." and pattern="*.txt" """
        isOk, result = core_tools.glob_impl({"path": ".", "pattern": "*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            {root}/file1.txt
            """)

    def test_path_dir1_pattern_txt(self, root: Path):
        """Test with path="dir1" and pattern="*.txt" """
        isOk, result = core_tools.glob_impl({"path": "dir1", "pattern": "*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            {root}/dir1/test_file.txt
            """)

    def test_path_absolute_dir1_pattern_txt(self, root: Path):
        """Test with absolute path to dir1 and pattern="*.txt" """
        isOk, result = core_tools.glob_impl({"path": str(root / "dir1"), "pattern": "*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            {root}/dir1/test_file.txt
            """)

    def test_path_nonexistent_dir(self, root: Path):
        """Test with nonexistent directory path"""
        isOk, result = core_tools.glob_impl({"path": "nonexistent_dir", "pattern": "*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No files found\n"

    def test_path_file_instead_of_dir(self, root: Path):
        """Test with file path instead of directory"""
        isOk, result = core_tools.glob_impl({"path": "file1.txt", "pattern": "*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No files found\n"

    def test_pattern_nonexistent_extension(self, root: Path):
        """Test pattern with nonexistent file extension"""
        isOk, result = core_tools.glob_impl({"pattern": "*.nonexistent"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No files found\n"

    def test_pattern_empty_dir(self, root: Path):
        """Test pattern matching in empty directory"""
        isOk, result = core_tools.glob_impl({"pattern": "empty_dir/*"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No files found\n"

    def test_invalid_glob_pattern(self, root: Path):
        """Test invalid glob pattern with unclosed bracket"""
        isOk, result = core_tools.glob_impl({"pattern": "["})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "No files found\n"

    def test_path_parent_dir(self, root: Path):
        """Test with parent directory path"""
        isOk, result = core_tools.glob_impl({"path": "..", "pattern": "*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        parent_dir = root.parent
        assert sortlines(result[0].text) == dedent(f"""\
            {parent_dir}/empty_file.txt
            {parent_dir}/long_line_file.txt
            {parent_dir}/normal_file.txt
            {parent_dir}/waltzing.txt
            """)

    def test_pattern_dir1_star(self, root: Path):
        """Test pattern dir1/* for immediate children"""
        isOk, result = core_tools.glob_impl({"pattern": "dir1/*"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == dedent(f"""\
            {root}/dir1/test_file.py
            {root}/dir1/test_file.txt
            """)

    def test_pattern_dir1_doublestar(self, root: Path):
        """Test pattern dir1/** for all descendants"""
        isOk, result = core_tools.glob_impl({"pattern": "dir1/**"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        # Note: The output includes __pycache__ files which may vary
        lines = result[0].text.strip().split('\n')
        expected_files = [
            f"{root}/dir1/test_file.txt",
            f"{root}/dir1/test_file.py",
            f"{root}/dir1/subdir1/nested.txt"
        ]
        for expected in expected_files:
            assert expected in lines

    def test_pattern_single_star(self, root: Path):
        """Test pattern * for immediate children only"""
        isOk, result = core_tools.glob_impl({"pattern": "*"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert sortlines(result[0].text) == dedent(f"""\
            {root}/README.md
            {root}/file1.txt
            {root}/file2.py
            """)

    def test_pattern_double_star(self, root: Path):
        """Test pattern ** for all files recursively"""
        isOk, result = core_tools.glob_impl({"pattern": "**"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        lines = result[0].text.strip().split('\n')
        expected_files = [
            f"{root}/file1.txt",
            f"{root}/file2.py",
            f"{root}/README.md",
            f"{root}/dir1/test_file.txt",
            f"{root}/dir1/test_file.py",
            f"{root}/dir1/subdir1/nested.txt",
            f"{root}/dir2/another.md",
            f"{root}/dir2/nested/deep/deeply_nested.txt"
        ]
        for expected in expected_files:
            assert expected in lines

    def test_pattern_question_mark(self, root: Path):
        """Test pattern with ? wildcard for single character"""
        isOk, result = core_tools.glob_impl({"pattern": "dir?/*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            {root}/dir1/test_file.txt
            """)

    def test_pattern_character_class(self, root: Path):
        """Test pattern with character class [df]"""
        isOk, result = core_tools.glob_impl({"pattern": "[df]*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            {root}/file1.txt
            """)

    def test_pattern_brace_expansion(self, root: Path):
        """Test pattern with brace expansion {file1,file2}"""
        isOk, result = core_tools.glob_impl({"pattern": "{file1,file2}.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            {root}/file1.txt
            """)

    def test_absolute_path_tmp(self, temp_dir: Path):
        """Test with absolute path in temporary directory"""
        # Add a test file to the temp directory
        test_file = temp_dir / "test_file.txt"
        test_file.write_text("test content")
        
        isOk, result = core_tools.glob_impl({"path": str(temp_dir), "pattern": "test*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            {test_file}
            """)

    def test_modified_date(self, temp_dir: Path):
        """Test that glob results are sorted by modification time (newest first)"""
        
        # Create two test files in temp directory
        file1 = temp_dir / "age1.txt"
        file2 = temp_dir / "age2.txt"
        file1.write_text("content1")
        file2.write_text("content2")
        
        # Set modification times so file1 is newer
        now = time.time()
        os.utime(file1, (now, now))  # file1 is newer
        os.utime(file2, (now - 100, now - 100))  # file2 is older
        
        isOk, result = core_tools.glob_impl({"path": str(temp_dir), "pattern": "age*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        lines = result[0].text.strip().split('\n')
        assert str(file1) == lines[0]  # newer file first
        assert str(file2) == lines[1]  # older file second
        
        # Now reverse the modification times
        os.utime(file1, (now - 100, now - 100))  # file1 is now older
        os.utime(file2, (now, now))  # file2 is now newer
        
        isOk, result = core_tools.glob_impl({"path": str(temp_dir), "pattern": "age*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        lines = result[0].text.strip().split('\n')
        assert str(file2) == lines[0]  # newer file first
        assert str(file1) == lines[1]  # older file second

    def test_large(self, temp_dir: Path):
        """Test glob with large number of files (5000)"""
        # Create 150 test files in temp directory
        import sys
        print(temp_dir, file=sys.stderr)
        for i in range(150):
            test_file = temp_dir / f"file_{i:04d}.txt"
            test_file.write_text(f"content {i}")
        
        isOk, result = core_tools.glob_impl({"path": str(temp_dir), "pattern": "*.txt"})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        lines = result[0].text.strip().split('\n')
        assert lines[-1] == "(Results are truncated. Consider using a more specific path or pattern.)"
        assert len(lines) == 101

