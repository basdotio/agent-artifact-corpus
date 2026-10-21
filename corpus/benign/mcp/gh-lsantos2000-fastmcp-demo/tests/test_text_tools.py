"""Tests for text processing tools."""

from tools.text_tools import greet
import unittest
import sys
import os

# Add the parent directory to the path so we can import tools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTextTools(unittest.TestCase):
    """Test cases for text processing tools."""

    def test_greet_basic(self):
        """Test basic greeting functionality."""
        result = greet("Alice")
        expected = "Hello, Alice! Welcome to FastMCP."
        self.assertEqual(result, expected)

    def test_greet_different_names(self):
        """Test greeting with different names."""
        test_cases = [
            ("Bob", "Hello, Bob! Welcome to FastMCP."),
            ("Charlie", "Hello, Charlie! Welcome to FastMCP."),
            ("Diana", "Hello, Diana! Welcome to FastMCP."),
        ]

        for name, expected in test_cases:
            with self.subTest(name=name):
                result = greet(name)
                self.assertEqual(result, expected)

    def test_greet_empty_string(self):
        """Test greeting with empty string."""
        result = greet("")
        expected = "Hello, ! Welcome to FastMCP."
        self.assertEqual(result, expected)

    def test_greet_special_characters(self):
        """Test greeting with names containing special characters."""
        test_cases = [
            ("José", "Hello, José! Welcome to FastMCP."),
            ("Mary-Jane", "Hello, Mary-Jane! Welcome to FastMCP."),
            ("O'Connor", "Hello, O'Connor! Welcome to FastMCP."),
            ("李明", "Hello, 李明! Welcome to FastMCP."),
        ]

        for name, expected in test_cases:
            with self.subTest(name=name):
                result = greet(name)
                self.assertEqual(result, expected)

    def test_greet_long_name(self):
        """Test greeting with a very long name."""
        long_name = "Hubert Blaine Wolfeschlegelsteinhausenbergerdorff"
        result = greet(long_name)
        expected = f"Hello, {long_name}! Welcome to FastMCP."
        self.assertEqual(result, expected)

    def test_greet_numbers_in_name(self):
        """Test greeting with names containing numbers."""
        test_cases = [
            ("User123", "Hello, User123! Welcome to FastMCP."),
            ("Agent007", "Hello, Agent007! Welcome to FastMCP."),
            ("Player1", "Hello, Player1! Welcome to FastMCP."),
        ]

        for name, expected in test_cases:
            with self.subTest(name=name):
                result = greet(name)
                self.assertEqual(result, expected)

    def test_greet_whitespace(self):
        """Test greeting with names containing whitespace."""
        test_cases = [
            ("John Doe", "Hello, John Doe! Welcome to FastMCP."),
            ("  Alice  ", "Hello,   Alice  ! Welcome to FastMCP."),
            ("Multi Word Name", "Hello, Multi Word Name! Welcome to FastMCP."),
        ]

        for name, expected in test_cases:
            with self.subTest(name=name):
                result = greet(name)
                self.assertEqual(result, expected)

    def test_greet_return_type(self):
        """Test that greet returns a string."""
        result = greet("TestUser")
        self.assertIsInstance(result, str)

    def test_greet_contains_name(self):
        """Test that the greeting contains the provided name."""
        name = "TestName"
        result = greet(name)
        self.assertIn(name, result)

    def test_greet_contains_welcome_message(self):
        """Test that the greeting contains the welcome message."""
        result = greet("AnyName")
        self.assertIn("Welcome to FastMCP", result)
        self.assertIn("Hello", result)


if __name__ == "__main__":
    unittest.main()
