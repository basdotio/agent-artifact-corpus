import os
import tempfile
import shutil
from pathlib import Path
from textwrap import dedent
import mcp.types
import core_tools

class TestFormat:
    def test_basic(self):
        alphabet = list("abcdefghijklmnopqrstuvwxyz")
        assert core_tools.format_lines(alphabet).startswith("    1→a\n    2→b\n    3→c\n")
        assert core_tools.format_lines(alphabet).endswith("   24→x\n   25→y\n   26→z\n")
        assert core_tools.format_lines(alphabet, offset=3, limit=2) == "    3→c\n    4→d\n"

        assert core_tools.format_lines(alphabet, offset=0, limit=1) == ""
        assert core_tools.format_lines(alphabet, offset=0, limit=2) == "    1→a\n"

        assert core_tools.format_lines(alphabet, offset=1, limit=0) == ""
        assert core_tools.format_lines(alphabet, offset=1, limit=1) == "    1→a\n"
        assert core_tools.format_lines(alphabet, offset=1, limit=2) == "    1→a\n    2→b\n"

        assert core_tools.format_lines(alphabet, offset=-1, limit=0) == ""
        assert core_tools.format_lines(alphabet, offset=-1, limit=1) == ""
        assert core_tools.format_lines(alphabet, offset=-1, limit=2) == ""
        assert core_tools.format_lines(alphabet, offset=-1, limit=3) == "    1→a\n"

        assert core_tools.format_lines(alphabet, offset=25, limit=1) == "   25→y\n"
        assert core_tools.format_lines(alphabet, offset=25, limit=2) == "   25→y\n   26→z\n"
        assert core_tools.format_lines(alphabet, offset=25, limit=3) == "   25→y\n   26→z\n"


class TestReadSimple:
    def setup_method(self):
        self.sample_data_dir = Path(__file__).parent / "sample_data"
        self.normal_file = self.sample_data_dir / "normal_file.txt"
        self.empty_file = self.sample_data_dir / "empty_file.txt"
        self.long_line_file = self.sample_data_dir / "long_line_file.txt"
        
        self.temp_dir = tempfile.mkdtemp()        
        self.large_file = Path(self.temp_dir) / "large_file.txt"
        with open(self.large_file, 'w') as f:
            for i in range(10000):
                f.write(f"This is line {i} with some content to make it longer\n")

    def teardown_method(self):
        if hasattr(self, 'temp_dir') and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_1_offset_and_limit_defaults(self):
        # Test with no offset or limit - should read entire file starting from line 1
        success, r = core_tools.read_impl({"file_path": str(self.normal_file)})
        assert success
        assert isinstance(r[0], mcp.types.TextContent)
        text = r[0].text
        
        # Should contain all 5 lines, starting from line 1
        assert "    1→line 1" in text
        assert "    2→line 2" in text
        assert "    3→line 3" in text
        assert "    4→line 4" in text
        assert "    5→line 5" in text
        
        # Test with explicit offset=1, no limit - should be same result
        success2, r2 = core_tools.read_impl({"file_path": str(self.normal_file), "offset": 1})
        assert success2
        assert isinstance(r2[0], mcp.types.TextContent)
        assert r[0].text == r2[0].text

    def test_2_normal_result_format(self):
        success, r = core_tools.read_impl({"file_path": str(self.normal_file), "offset": 2, "limit": 2})
        assert success
        assert isinstance(r[0], mcp.types.TextContent)
        text = r[0].text

        lines = text.split('\n')
        assert "    2→line 2" in text
        assert "    3→line 3" in text
        
        assert "    1→line 1" not in text
        assert "    4→line 4" not in text
        assert "    5→line 5" not in text
        
        assert "<system-reminder>" in text
        
        success, result_content = core_tools.read_impl({"file_path": str(self.long_line_file), "offset": 2, "limit": 1})
        assert success
        assert isinstance(result_content[0], mcp.types.TextContent)
        text = result_content[0].text
        
        # Line 2 should contain the full long line (no truncation)
        lines = [line for line in text.split('\n') if line.startswith("    2→")]
        assert len(lines) == 1  # Should have exactly one line 2
        # Should contain the full line content without truncation
        assert lines[0].startswith("    2→" + "a" * 100)  # Check first 100 'a's are there
    
    def test_3_file_not_found(self):
        nonexistent_file = "/path/that/definitely/does/not/exist.txt"
        success, result_content = core_tools.read_impl({"file_path": nonexistent_file})
        assert not success
        assert isinstance(result_content[0], mcp.types.TextContent)
        assert result_content[0].text == "<tool_use_error>File does not exist.</tool_use_error>"
    
    def test_4_file_too_large(self):
        isOk, result = core_tools.read_impl({"file_path": str(self.large_file)})
        assert not isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert "File content (0.5MB) exceeds maximum allowed size (256KB)." in result[0].text
    
    def test_5_offset_beyond_file_length(self):
        isOk, result = core_tools.read_impl({"file_path": str(self.normal_file), "offset": 10})
        assert isOk 
        assert isinstance(result[0], mcp.types.TextContent)
        assert "<system-reminder>Warning" in result[0].text
        
        isOk, result = core_tools.read_impl({"file_path": str(self.empty_file)})
        assert isOk 
        assert isinstance(result[0], mcp.types.TextContent)
        assert "<system-reminder>Warning" in result[0].text
        
        isOk, result = core_tools.read_impl({"file_path": str(self.empty_file), "offset": 5})
        assert isOk         
        assert isinstance(result[0], mcp.types.TextContent)
        assert "<system-reminder>Warning" in result[0].text
    
    def test_6_edge_cases_and_additional_scenarios(self):
        success, result_content = core_tools.read_impl({"file_path": str(self.normal_file), "offset": 5, "limit": 1})
        assert success
        assert isinstance(result_content[0], mcp.types.TextContent)
        text = result_content[0].text
        assert "    5→line 5" in text
        assert "    4→line 4" not in text
        
        success, result_content = core_tools.read_impl({"file_path": str(self.normal_file), "offset": 4, "limit": 10})
        assert success
        assert isinstance(result_content[0], mcp.types.TextContent)
        text = result_content[0].text
        assert "    4→line 4" in text
        assert "    5→line 5" in text
        assert "    6→" not in text  # Should not have line 6
        
        success, result_content = core_tools.read_impl({"file_path": str(self.normal_file), "offset": 1, "limit": 0})
        assert success
        assert isinstance(result_content[0], mcp.types.TextContent)
        text = result_content[0].text
        assert "    1→" not in text
        assert "<system-reminder>" in text
    
class TestReadEdge:
    def setup_method(self):
        self.root = Path(__file__).parent.absolute() / "sample_data" / "read_root"
        os.chdir(self.root)
    
    def test_ok(self):
        isOk, result = core_tools.read_impl({"file_path": str(self.root / "file1.txt")})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text.startswith("    1→Hello")
        assert "<system-reminder>" in result[0].text

    def test_too_many_tokens(self):
        isOk, result = core_tools.read_impl({"file_path": str(self.root / "too_many_tokens.txt")})
        assert not isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert "File content (24876 tokens) exceeds maximum allowed tokens (24000 tokens)." in result[0].text
    
    def test_absent(self):
        isOk, result = core_tools.read_impl({"file_path": str(self.root / "file2.txt")})
        assert not isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "<tool_use_error>File does not exist.</tool_use_error>"


    def test_near_miss(self):
        isOk, result = core_tools.read_impl({"file_path": str(self.root / "file1.py")})
        assert not isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == "<tool_use_error>File does not exist. Did you mean file1.txt?</tool_use_error>"


class TestWrite:
    def setup_method(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.existing = self.root / "file1.txt"
        self.existing.write_text("This is file 1.")

    def teardown_method(self):
        if hasattr(self, 'root') and self.root.exists():
            shutil.rmtree(self.root)

    def test_write_after_read(self):
        success, result_content = core_tools.write_impl({"file_path": str(self.existing), "content": "foo"})
        assert not success
        assert isinstance(result_content[0], mcp.types.TextContent)
        assert result_content[0].text == "Error: File has not been read yet.\nRead it first before writing to it."

        _, success = core_tools.read_impl({"file_path": str(self.existing)})
        assert success

        success, result_content = core_tools.write_impl({"file_path": str(self.existing), "content": "foo"})
        assert success
        assert isinstance(result_content[0], mcp.types.TextContent)
        assert result_content[0].text == dedent(f"""\
            The file {self.existing} has been updated.
            Here's the result of running `cat -n` on a snippet of the edited file:
                1→foo
            """)

    def test_write_after_write(self):
        newfile = self.root / "file2.txt"
        success, result_content = core_tools.write_impl({"file_path": str(newfile), "content": "foo"})
        assert success
        assert isinstance(result_content[0], mcp.types.TextContent)
        assert result_content[0].text == f"File created successfully at: {newfile}"

        success, result_content = core_tools.write_impl({"file_path": str(newfile), "content": "bar"})
        assert success
        assert isinstance(result_content[0], mcp.types.TextContent)
        assert result_content[0].text == dedent(f"""\
            The file {newfile} has been updated.
            Here's the result of running `cat -n` on a snippet of the edited file:
                1→bar
            """)

class TestDiff:
    old = list("abcdefghijklmnopqrstuvwxyz")

    def test_one(self) -> None:
        new = list("abcdefghijklMnopqrstuvwxyz")
        assert core_tools.HaveReadFilesWatcher.diff(self.old, new, 1) == "   12→l\n   13→M\n   14→n\n"

    def test_insertion(self) -> None:
        new = list("abcdefghijkl123mnopqrstuvwxyz")
        assert core_tools.HaveReadFilesWatcher.diff(self.old, new, 1) == "   12→l\n   13→1\n   14→2\n   15→3\n   16→m\n"

    def test_removal(self) -> None:
        new = list("abcdefghijklpqrstuvwxyz")
        assert core_tools.HaveReadFilesWatcher.diff(self.old, new, 1) == "   12→l\n   13→p\n"

    def test_two_changes(self) -> None:
        new = list("abcdeFghijklmnopqrStuvwxyz")
        assert core_tools.HaveReadFilesWatcher.diff(self.old, new, 1) == "    5→e\n    6→F\n    7→g\n\n   18→r\n   19→S\n   20→t\n"

    def test_context_before(self) -> None:
        new = list("aBcdefghijklmnopqrstuvwxyz")
        assert core_tools.HaveReadFilesWatcher.diff(self.old, new, 3) == "    1→a\n    2→B\n    3→c\n    4→d\n    5→e\n"

    def test_context_after(self) -> None:
        new = list("abcdefghijklmnopqrstuvwxYz")
        assert core_tools.HaveReadFilesWatcher.diff(self.old, new, 3) == "   22→v\n   23→w\n   24→x\n   25→Y\n   26→z\n"

    def test_empty_before(self) -> None:
        new = list("abc")
        assert core_tools.HaveReadFilesWatcher.diff([], new, 1) == "    1→a\n    2→b\n    3→c\n"

    def test_empty_after(self) -> None:
        old = list("abc")
        assert core_tools.HaveReadFilesWatcher.diff(old, [], 1) == ""

    def test_same(self) -> None:
        old = list("abc")
        assert core_tools.HaveReadFilesWatcher.diff(old, old, 1) == ""
