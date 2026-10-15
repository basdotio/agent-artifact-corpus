#!/usr/bin/env python3
"""
Test runner script for Android MCP Server

This script installs test dependencies and runs the complete test suite.
"""

import os
import subprocess
import sys


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(command, shell=True,
                                check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False


def main():
    """Main test runner function"""
    print("Android MCP Server Test Runner")
    print("=" * 60)

    # Change to the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"Working directory: {script_dir}")

    # Install test dependencies
    if not run_command("pip install -e .[test]", "Installing test dependencies"):
        print("Failed to install test dependencies")
        return 1

    # Run tests with coverage
    if not run_command("pytest tests/ -v --cov=. --cov-report=term-missing", "Running tests with coverage"):
        print("Tests failed")
        return 1

    print("\n" + "="*60)
    print("All tests passed successfully!")
    print("="*60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
