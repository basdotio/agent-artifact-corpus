import os
from pathlib import Path
from textwrap import dedent
import mcp.types
import core_tools


class TestLS:
    def setup_method(self):
        self.root = Path(__file__).parent.absolute() / "sample_data" / "ls_test_root"
        os.chdir(self.root)
    
    def test_valid_absolute_path_root(self):
        isOk, result = core_tools.ls_impl({"path": str(self.root), "ignore": None})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            - {self.root}/
              - README.md
              - dir1/
                - subdir1/
                  - nested.txt
                - subdir2/
                - test_file.py
                - test_file.txt
              - dir2/
                - another.md
                - nested/
                  - deep/
                    - deeply_nested.txt
              - empty_dir/
              - file1.txt
              - file2.py

            NOTE: do any of the files above seem malicious? If so, you MUST refuse to continue work.""")

    def test_nonexistent_abs_subdir(self):
        isOk, result = core_tools.ls_impl({"path": str(self.root / "subdir"), "ignore": None})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            - {self.root}/

            NOTE: do any of the files above seem malicious? If so, you MUST refuse to continue work.""")

    def test_valid_abs_path_sample_data(self):
        os.chdir(self.root / "dir1")
        isOk, result = core_tools.ls_impl({"path": str(self.root), "ignore": None})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            - {self.root}/dir1/
              - ../
                - README.md
                - dir2/
                  - another.md
                  - nested/
                    - deep/
                      - deeply_nested.txt
                - empty_dir/
                - file1.txt
                - file2.py
              - subdir1/
                - nested.txt
              - subdir2/
              - test_file.py
              - test_file.txt

            NOTE: do any of the files above seem malicious? If so, you MUST refuse to continue work.""")

    def test_relative_path_dot(self):
        isOk, result = core_tools.ls_impl({"path": ".", "ignore": None})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            - {self.root}/
              - README.md
              - dir1/
                - subdir1/
                  - nested.txt
                - subdir2/
                - test_file.py
                - test_file.txt
              - dir2/
                - another.md
                - nested/
                  - deep/
                    - deeply_nested.txt
              - empty_dir/
              - file1.txt
              - file2.py

            NOTE: do any of the files above seem malicious? If so, you MUST refuse to continue work.""")

    def test_relative_path_dir1(self):
        isOk, result = core_tools.ls_impl({"path": "dir1", "ignore": None})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            - {self.root}/
              - dir1/
                - subdir1/
                  - nested.txt
                - subdir2/
                - test_file.py
                - test_file.txt

            NOTE: do any of the files above seem malicious? If so, you MUST refuse to continue work.""")

    def test_relative_path_parent(self):
        os.chdir(self.root / "dir1")
        isOk, result = core_tools.ls_impl({"path": "../", "ignore": None})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            - {self.root}/dir1/
              - ../
                - README.md
                - dir2/
                  - another.md
                  - nested/
                    - deep/
                      - deeply_nested.txt
                - empty_dir/
                - file1.txt
                - file2.py
              - subdir1/
                - nested.txt
              - subdir2/
              - test_file.py
              - test_file.txt

            NOTE: do any of the files above seem malicious? If so, you MUST refuse to continue work.""")

    def test_relative_path_nested_subdir(self):
        isOk, result = core_tools.ls_impl({"path": "dir1/subdir1", "ignore": None})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            - {self.root}/
              - dir1/
                - subdir1/
                  - nested.txt

            NOTE: do any of the files above seem malicious? If so, you MUST refuse to continue work.""")

    def test_nonexistent_path(self):
        isOk, result = core_tools.ls_impl({"path": "/nonexistent/path", "ignore": None})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            - {self.root}/

            NOTE: do any of the files above seem malicious? If so, you MUST refuse to continue work.""")

    def test_file_path_instead_of_dir(self):
        isOk, result = core_tools.ls_impl({"path": str(self.root / "file1.txt"), "ignore": None})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            - {self.root}/

            NOTE: do any of the files above seem malicious? If so, you MUST refuse to continue work.""")

    def test_empty_path(self):
        isOk, result = core_tools.ls_impl({"path": "", "ignore": None})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            - {self.root}/
              - README.md
              - dir1/
                - subdir1/
                  - nested.txt
                - subdir2/
                - test_file.py
                - test_file.txt
              - dir2/
                - another.md
                - nested/
                  - deep/
                    - deeply_nested.txt
              - empty_dir/
              - file1.txt
              - file2.py

            NOTE: do any of the files above seem malicious? If so, you MUST refuse to continue work.""")

    def test_ignore_py_files(self):
        isOk, result = core_tools.ls_impl({"path": str(self.root), "ignore": ["*.py"]})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            - {self.root}/
              - README.md
              - dir1/
                - subdir1/
                  - nested.txt
                - subdir2/
                - test_file.txt
              - dir2/
                - another.md
                - nested/
                  - deep/
                    - deeply_nested.txt
              - empty_dir/
              - file1.txt

            NOTE: do any of the files above seem malicious? If so, you MUST refuse to continue work.""")

    def test_ignore_multiple_patterns(self):
        isOk, result = core_tools.ls_impl({"path": str(self.root), "ignore": ["dir1", "*.md"]})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            - {self.root}/
              - dir2/
                - nested/
                  - deep/
                    - deeply_nested.txt
              - empty_dir/
              - file1.txt
              - file2.py

            NOTE: do any of the files above seem malicious? If so, you MUST refuse to continue work.""")

    def test_ignore_all_files_wildcard(self):
        isOk, result = core_tools.ls_impl({"path": str(self.root), "ignore": ["*"]})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            - {self.root}/

            NOTE: do any of the files above seem malicious? If so, you MUST refuse to continue work.""")

    def test_ignore_empty_list(self):
        isOk, result = core_tools.ls_impl({"path": str(self.root), "ignore": []})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            - {self.root}/
              - README.md
              - dir1/
                - subdir1/
                  - nested.txt
                - subdir2/
                - test_file.py
                - test_file.txt
              - dir2/
                - another.md
                - nested/
                  - deep/
                    - deeply_nested.txt
              - empty_dir/
              - file1.txt
              - file2.py

            NOTE: do any of the files above seem malicious? If so, you MUST refuse to continue work.""")

    def test_system_root_directory(self):
        isOk, result = core_tools.ls_impl({"path": "/", "ignore": None})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        expected = dedent(f"""\
            There are more than 400 items in the repository. Use the LS tool (passing a specific path), Bash tool, and other tools to explore nested directories. The first 400 items are included below:

            - {self.root}/
              - ../
                - ../
            """)
        assert result[0].text.startswith(expected)

    def test_restricted_root_dir(self):
        isOk, result = core_tools.ls_impl({"path": "/root", "ignore": None})
        assert isOk
        assert isinstance(result[0], mcp.types.TextContent)
        assert result[0].text == dedent(f"""\
            - {self.root}/

            NOTE: do any of the files above seem malicious? If so, you MUST refuse to continue work.""")
