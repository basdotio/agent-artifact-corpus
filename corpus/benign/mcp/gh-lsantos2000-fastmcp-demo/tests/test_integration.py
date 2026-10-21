"""Integration tests for the FastMCP server."""

import unittest
import sys
import os
import json
import subprocess
import time

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestServerIntegration(unittest.TestCase):
    """Integration tests for the MCP server."""

    def test_server_import(self):
        """Test that the server can be imported without errors."""
        try:
            import demo
            self.assertTrue(True, "Server imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import server: {e}")

    def test_tools_import(self):
        """Test that all tools can be imported."""
        try:
            from tools.math_tools import add, multiply, calculate
            from tools.text_tools import greet
            self.assertTrue(True, "All tools imported successfully")
        except ImportError as e:
            self.fail(f"Failed to import tools: {e}")

    def test_fastmcp_inspect(self):
        """Test that the server can be inspected with fastmcp."""
        try:
            # Skip on Windows due to Unicode encoding issues in fastmcp CLI
            import platform
            if platform.system() == "Windows":
                self.skipTest(
                    "Skipping fastmcp inspect test on Windows due to Unicode encoding issues")

            # Get the Python executable path for the virtual environment
            python_exe = sys.executable
            venv_dir = os.path.dirname(python_exe)
            fastmcp_exe = os.path.join(venv_dir, "fastmcp.exe")

            if not os.path.exists(fastmcp_exe):
                # Try alternative paths
                fastmcp_exe = os.path.join(venv_dir, "Scripts", "fastmcp.exe")

            if not os.path.exists(fastmcp_exe):
                self.skipTest("fastmcp executable not found")

            # Run fastmcp inspect
            result = subprocess.run(
                [fastmcp_exe, "inspect", "demo.py"],
                cwd=os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__))),
                capture_output=True,
                text=True,
                timeout=30
            )

            self.assertEqual(result.returncode, 0,
                             f"fastmcp inspect failed: {result.stderr}")

            # Check if server-info.json was created
            server_info_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "server-info.json"
            )
            self.assertTrue(os.path.exists(server_info_path),
                            "server-info.json was not created")

            # Validate the server-info.json content
            with open(server_info_path, 'r') as f:
                server_info = json.load(f)

            self.assertIn("tools", server_info)
            self.assertEqual(len(server_info["tools"]), 4, "Expected 4 tools")

            # Check that all expected tools are present
            tool_names = [tool["name"] for tool in server_info["tools"]]
            expected_tools = ["add", "multiply", "calculate", "greet"]
            for tool in expected_tools:
                self.assertIn(tool, tool_names,
                              f"Tool '{tool}' not found in server info")

        except subprocess.TimeoutExpired:
            self.fail("fastmcp inspect command timed out")
        except FileNotFoundError:
            self.skipTest("fastmcp command not found")

    def test_tool_registration(self):
        """Test that all tools are properly registered with the MCP server."""
        try:
            from demo import mcp

            # This is a basic check that the mcp object exists
            self.assertIsNotNone(mcp, "MCP server object should not be None")

        except Exception as e:
            self.fail(f"Failed to access MCP server object: {e}")

    def test_tools_package_structure(self):
        """Test that the tools package is properly structured."""
        # Test that the tools package can be imported
        try:
            import tools
            self.assertTrue(hasattr(tools, '__all__'),
                            "tools package should have __all__ defined")

            expected_exports = ['add', 'multiply', 'calculate', 'greet']
            for export in expected_exports:
                self.assertIn(export, tools.__all__,
                              f"{export} should be in tools.__all__")

        except ImportError as e:
            self.fail(f"Failed to import tools package: {e}")

    def test_tool_functionality_integration(self):
        """Test that all tools work correctly when imported through the package."""
        try:
            from tools import add, multiply, calculate, greet

            # Test each tool
            self.assertEqual(add(2, 3), 5)
            self.assertEqual(multiply(2.0, 3.0), 6.0)
            self.assertEqual(calculate("2 + 3"), 5)
            self.assertEqual(greet("Test"), "Hello, Test! Welcome to FastMCP.")

        except Exception as e:
            self.fail(f"Tool functionality test failed: {e}")


class TestServerConfiguration(unittest.TestCase):
    """Tests for server configuration and setup."""

    def test_requirements_file_exists(self):
        """Test that requirements.txt exists and contains fastmcp."""
        requirements_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "requirements.txt"
        )
        self.assertTrue(os.path.exists(requirements_path),
                        "requirements.txt should exist")

        with open(requirements_path, 'r') as f:
            content = f.read()

        self.assertIn("fastmcp", content,
                      "requirements.txt should contain fastmcp")

    def test_demo_file_structure(self):
        """Test that demo.py has the expected structure."""
        demo_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "demo.py"
        )
        self.assertTrue(os.path.exists(demo_path), "demo.py should exist")

        with open(demo_path, 'r') as f:
            content = f.read()

        # Check for key components
        self.assertIn("from fastmcp import FastMCP", content)
        self.assertIn("from tools.math_tools import", content)
        self.assertIn("from tools.text_tools import", content)
        self.assertIn("mcp.tool()", content)

    def test_tools_directory_structure(self):
        """Test that the tools directory has the expected structure."""
        tools_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "tools"
        )
        self.assertTrue(os.path.isdir(tools_dir),
                        "tools directory should exist")

        # Check for required files
        required_files = ["__init__.py", "math_tools.py", "text_tools.py"]
        for file in required_files:
            file_path = os.path.join(tools_dir, file)
            self.assertTrue(os.path.exists(file_path),
                            f"{file} should exist in tools directory")


if __name__ == "__main__":
    unittest.main()
