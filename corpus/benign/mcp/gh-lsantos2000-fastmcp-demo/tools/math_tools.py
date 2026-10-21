"""Mathematical operation tools."""

import math
import re
from typing import Union


def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


def multiply(a: float, b: float) -> float:
    """Multiply two floats."""
    return a * b


def calculate(expression: str) -> Union[float, int, str]:
    """
    General purpose calculator that evaluates mathematical expressions.

    Supports:
    - Basic operations: +, -, *, /, **, %
    - Parentheses for grouping
    - Mathematical functions: sin, cos, tan, log, sqrt, abs, etc.
    - Constants: pi, e

    Examples:
    - "2 + 3 * 4" → 14
    - "sqrt(16)" → 4.0
    - "sin(pi/2)" → 1.0
    - "(5 + 3) ** 2" → 64
    """
    try:
        # Clean the expression
        expression = expression.strip()

        # Replace common constants (using word boundaries to avoid partial replacements)
        expression = re.sub(r'\bpi\b', str(math.pi), expression)
        expression = re.sub(r'\be\b', str(math.e), expression)

        # Create a safe namespace with math functions
        safe_dict = {
            # Basic math functions
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "asin": math.asin,
            "acos": math.acos,
            "atan": math.atan,
            "sinh": math.sinh,
            "cosh": math.cosh,
            "tanh": math.tanh,
            "log": math.log,
            "log10": math.log10,
            "log2": math.log2,
            "exp": math.exp,
            "sqrt": math.sqrt,
            "pow": math.pow,
            "abs": abs,
            "round": round,
            "floor": math.floor,
            "ceil": math.ceil,
            "min": min,
            "max": max,
            # Constants
            "pi": math.pi,
            "e": math.e,
            # Prevent access to dangerous functions
            "__builtins__": {},
        }

        # Validate expression contains only safe characters
        if not re.match(r"^[0-9+\-*/().,%\s\w]+$", expression):
            return "Error: Invalid characters in expression"

        # Evaluate the expression
        result = eval(expression, safe_dict)

        # Return integer if result is a whole number
        if isinstance(result, float) and result.is_integer():
            return int(result)

        return result

    except ZeroDivisionError:
        return "Error: Division by zero"
    except ValueError as e:
        return f"Error: Invalid value - {str(e)}"
    except SyntaxError:
        return "Error: Invalid mathematical expression"
    except Exception as e:
        return f"Error: {str(e)}"
