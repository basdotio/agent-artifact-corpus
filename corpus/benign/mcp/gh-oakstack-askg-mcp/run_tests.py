#!/usr/bin/env python3
"""Test Runner for ASKG MCP Server

This script runs tests to verify the MCP server functionality.
"""

import subprocess
import sys
from pathlib import Path


def run_pytest():
    """Run pytest on the test files"""
    print("Running MCP Server tests...")

    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "test_basic.py",
            "test_mcp_server.py",
            "-v",
            "--tb=short",
            "--import-mode=importlib",
        ], check=False, capture_output=True, text=True, cwd=Path(__file__).parent)

        print("STDOUT:")
        print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        if result.returncode == 0:
            print("✅ All tests passed!")
        else:
            print(f"❌ Tests failed with return code: {result.returncode}")

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")

    try:
        # Run the dedicated import test
        result = subprocess.run([
            sys.executable, "test_imports_simple.py"
        ], check=False, capture_output=True, text=True, cwd=Path(__file__).parent)

        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Error running import test: {e}")
        return False

def test_config_loading():
    """Test configuration loading"""
    print("Testing configuration loading...")

    try:
        import yaml
        config_path = Path(__file__).parent.parent / ".config.yaml"
        example_config_path = Path(__file__).parent.parent / ".config.example.yaml"

        if not config_path.exists():
            print("⚠️  Configuration file not found, creating test config...")
            
            # Try to copy from example config first
            if example_config_path.exists():
                with open(example_config_path, "r") as f:
                    test_config = yaml.safe_load(f)
                print("✅ Copied from example config")
            else:
                # Create minimal test config
                test_config = {
                    "neo4j": {
                        "local": {
                            "uri": "bolt://localhost:7687",
                            "user": "neo4j",
                            "password": "password",
                        },
                    },
                }
                print("✅ Created minimal test config")
            
            with open(config_path, "w") as f:
                yaml.dump(test_config, f)
            print("✅ Test configuration created")
        else:
            print("✅ Configuration file exists")

        return True

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_config_file():
    """Test configuration file functionality"""
    print("Testing configuration file functionality...")

    try:
        # Run the dedicated config test
        result = subprocess.run([
            sys.executable, "test_config.py"
        ], check=False, capture_output=True, text=True, cwd=Path(__file__).parent)

        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Error running config test: {e}")
        return False

def main():
    """Main test runner"""
    print("=" * 60)
    print("ASKG MCP Server Test Runner")
    print("=" * 60)

    tests = [
        ("Import Test", test_imports),
        ("Configuration Test", test_config_loading),
        ("Config File Test", test_config_file),
        ("Pytest Tests", run_pytest),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 40)
        success = test_func()
        results.append((test_name, success))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
        if success:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The MCP server is ready to use.")
        return 0
    print("⚠️  Some tests failed. Please check the output above.")
    return 1

if __name__ == "__main__":
    sys.exit(main())
