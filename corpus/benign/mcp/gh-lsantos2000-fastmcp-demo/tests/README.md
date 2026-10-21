# Test Configuration for FastMCP Demo

This directory contains comprehensive tests for the FastMCP demo project.

## Test Structure

```
tests/
├── __init__.py           # Test package initialization
├── test_math_tools.py    # Tests for mathematical operations
├── test_text_tools.py    # Tests for text processing tools
├── test_integration.py   # Integration tests for the MCP server
├── run_tests.py         # Test runner script
└── README.md            # This file
```

## Test Coverage

### Unit Tests
- **test_math_tools.py**: Tests for add, multiply, and calculate functions
  - Basic arithmetic operations
  - Mathematical functions (trig, log, etc.)
  - Error handling and security
  - Edge cases and type handling

- **test_text_tools.py**: Tests for text processing functions
  - Basic greeting functionality
  - Special characters and Unicode
  - Edge cases and input validation

### Integration Tests
- **test_integration.py**: End-to-end testing
  - Server import and configuration
  - FastMCP inspection functionality
  - Tool registration verification
  - Package structure validation

## Running Tests

### Run All Tests
```bash
python tests/run_tests.py
```

### Run Specific Test Modules
```bash
# Run only math tools tests
python tests/run_tests.py test_math_tools

# Run only text tools tests
python tests/run_tests.py test_text_tools

# Run only integration tests
python tests/run_tests.py test_integration
```

### Run Individual Test Files
```bash
# Run math tools tests directly
python -m unittest tests.test_math_tools

# Run with verbose output
python -m unittest tests.test_math_tools -v
```

### Using pytest (if installed)
```bash
# Install pytest first
pip install pytest

# Run all tests
pytest tests/

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=tools --cov-report=html
```

## Test Categories

### 🔢 Mathematical Operations Tests
- Addition and multiplication with various inputs
- Calculator with 50+ test cases covering:
  - Basic arithmetic operations
  - Mathematical functions (sin, cos, sqrt, log, etc.)
  - Constants (pi, e)
  - Complex expressions
  - Error handling and security validation

### 📝 Text Processing Tests
- Greeting functionality with edge cases
- Unicode and special character handling
- Input validation and type checking

### 🔗 Integration Tests
- Server configuration validation
- Tool registration verification
- Package import testing
- FastMCP compatibility testing

## Test Results

When all tests pass, you should see output like:
```
test_add_positive_numbers (tests.test_math_tools.TestMathTools) ... ok
test_calculate_basic_arithmetic (tests.test_math_tools.TestCalculator) ... ok
test_greet_basic (tests.test_text_tools.TestTextTools) ... ok
test_server_import (tests.test_integration.TestServerIntegration) ... ok

Ran XX tests in X.XXXs

OK
```

## Continuous Integration

These tests are designed to be run in CI/CD pipelines. The test runner returns appropriate exit codes:
- `0`: All tests passed
- `1`: One or more tests failed
