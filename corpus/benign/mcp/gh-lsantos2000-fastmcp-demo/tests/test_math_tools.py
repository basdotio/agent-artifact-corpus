"""Tests for mathematical operation tools."""

from tools.math_tools import add, multiply, calculate
import unittest
import math
import sys
import os

# Add the parent directory to the path so we can import tools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMathTools(unittest.TestCase):
    """Test cases for mathematical operation tools."""

    def test_add_positive_numbers(self):
        """Test adding positive integers."""
        self.assertEqual(add(3, 5), 8)
        self.assertEqual(add(10, 20), 30)
        self.assertEqual(add(0, 5), 5)

    def test_add_negative_numbers(self):
        """Test adding negative integers."""
        self.assertEqual(add(-3, -5), -8)
        self.assertEqual(add(-10, 5), -5)
        self.assertEqual(add(10, -5), 5)

    def test_add_zero(self):
        """Test adding with zero."""
        self.assertEqual(add(0, 0), 0)
        self.assertEqual(add(5, 0), 5)
        self.assertEqual(add(0, -5), -5)

    def test_multiply_positive_numbers(self):
        """Test multiplying positive numbers."""
        self.assertEqual(multiply(2.5, 4.0), 10.0)
        self.assertEqual(multiply(3.0, 3.0), 9.0)
        self.assertEqual(multiply(1.0, 5.0), 5.0)

    def test_multiply_negative_numbers(self):
        """Test multiplying negative numbers."""
        self.assertEqual(multiply(-2.5, 4.0), -10.0)
        self.assertEqual(multiply(-3.0, -3.0), 9.0)
        self.assertEqual(multiply(0.0, 5.0), 0.0)

    def test_multiply_by_zero(self):
        """Test multiplying by zero."""
        self.assertEqual(multiply(0.0, 0.0), 0.0)
        self.assertEqual(multiply(5.0, 0.0), 0.0)
        self.assertEqual(multiply(0.0, -5.0), 0.0)


class TestCalculator(unittest.TestCase):
    """Test cases for the calculator tool."""

    def test_basic_arithmetic(self):
        """Test basic arithmetic operations."""
        self.assertEqual(calculate("2 + 3"), 5)
        self.assertEqual(calculate("10 - 4"), 6)
        self.assertEqual(calculate("3 * 4"), 12)
        self.assertEqual(calculate("15 / 3"), 5)
        self.assertEqual(calculate("2 ** 3"), 8)
        self.assertEqual(calculate("10 % 3"), 1)

    def test_order_of_operations(self):
        """Test order of operations (PEMDAS)."""
        self.assertEqual(calculate("2 + 3 * 4"), 14)
        self.assertEqual(calculate("(2 + 3) * 4"), 20)
        self.assertEqual(calculate("2 ** 3 * 4"), 32)
        self.assertEqual(calculate("(5 + 3) ** 2"), 64)

    def test_mathematical_functions(self):
        """Test mathematical functions."""
        self.assertEqual(calculate("sqrt(16)"), 4)
        self.assertEqual(calculate("abs(-42)"), 42)
        self.assertEqual(calculate("max(5, 3, 8)"), 8)
        self.assertEqual(calculate("min(5, 3, 8)"), 3)
        self.assertEqual(calculate("round(3.7)"), 4)
        self.assertEqual(calculate("floor(3.7)"), 3)
        self.assertEqual(calculate("ceil(3.2)"), 4)

    def test_trigonometric_functions(self):
        """Test trigonometric functions."""
        # Using assertAlmostEqual for floating point comparisons
        self.assertAlmostEqual(calculate("sin(pi/2)"), 1.0, places=10)
        self.assertAlmostEqual(calculate("cos(0)"), 1.0, places=10)
        self.assertAlmostEqual(calculate("tan(pi/4)"), 1.0, places=10)

    def test_logarithmic_functions(self):
        """Test logarithmic functions."""
        self.assertAlmostEqual(calculate("log(e)"), 1.0, places=10)
        self.assertEqual(calculate("log10(100)"), 2.0)
        self.assertEqual(calculate("log2(8)"), 3.0)
        self.assertAlmostEqual(calculate("exp(1)"), math.e, places=10)

    def test_constants(self):
        """Test mathematical constants."""
        self.assertAlmostEqual(calculate("pi"), math.pi, places=10)
        self.assertAlmostEqual(calculate("e"), math.e, places=10)

    def test_complex_expressions(self):
        """Test complex mathematical expressions."""
        self.assertEqual(calculate("sqrt(25) + 3"), 8)
        self.assertAlmostEqual(calculate("sin(pi/6) * 2"), 1.0, places=10)
        self.assertEqual(calculate("(sqrt(16) + 2) * 3"), 18)

    def test_error_handling(self):
        """Test error handling for invalid expressions."""
        # Division by zero
        result = calculate("1 / 0")
        self.assertTrue(result.startswith("Error: Division by zero"))

        # Invalid syntax
        result = calculate("2 +")
        self.assertTrue(result.startswith(
            "Error: Invalid mathematical expression"))

        # Invalid characters
        result = calculate("2 + abc")
        self.assertTrue(result.startswith("Error:"))

    def test_security(self):
        """Test that dangerous expressions are blocked."""
        # Should block imports
        result = calculate("__import__('os')")
        self.assertTrue(result.startswith("Error:"))

        # Should block file operations
        result = calculate("open('/etc/passwd')")
        self.assertTrue(result.startswith("Error:"))

    def test_whitespace_handling(self):
        """Test that expressions with various whitespace are handled correctly."""
        self.assertEqual(calculate("  2 + 3  "), 5)
        self.assertEqual(calculate("2+3"), 5)
        self.assertEqual(calculate(" 2 * 3 "), 6)

    def test_integer_vs_float_results(self):
        """Test that results are returned as integers when appropriate."""
        # Should return integer
        result = calculate("4.0 / 2.0")
        self.assertEqual(result, 2)
        self.assertIsInstance(result, int)

        # Should return float
        result = calculate("5.0 / 2.0")
        self.assertEqual(result, 2.5)
        self.assertIsInstance(result, float)


if __name__ == "__main__":
    unittest.main()
