#!/usr/bin/env python3
"""Test the CI environment and dependencies"""

import sys
import subprocess
from pathlib import Path

def test_python_version():
    """Test Python version"""
    print(f"Python version: {sys.version}")
    if sys.version_info >= (3, 9):
        print("✅ Python version is 3.9+")
        return True
    else:
        print(f"❌ Python version {sys.version_info} is below 3.9")
        return False

def test_pip_packages():
    """Test that required packages are installed"""
    package_imports = [
        ("neo4j", "neo4j"),
        ("pydantic", "pydantic"), 
        ("yaml", "pyyaml"),  # pyyaml package provides yaml module
        ("aiohttp", "aiohttp"),
        ("pytest", "pytest"),
        ("pytest_asyncio", "pytest-asyncio")  # pytest-asyncio package provides pytest_asyncio module
    ]
    
    for import_name, package_name in package_imports:
        try:
            __import__(import_name)
            print(f"✅ {package_name} imported successfully")
        except ImportError as e:
            print(f"❌ {package_name} import failed: {e}")
            return False
    
    return True

def test_pytest_available():
    """Test that pytest is available"""
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", "--version"
        ], capture_output=True, text=True, check=True)
        print(f"✅ pytest available: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ pytest not available: {e}")
        return False

def test_working_directory():
    """Test working directory and file structure"""
    cwd = Path.cwd()
    print(f"Working directory: {cwd}")
    
    # Check if we're in the mcp directory
    if cwd.name == "mcp":
        print("✅ Running from mcp directory")
    else:
        print(f"⚠️  Not in mcp directory, current: {cwd.name}")
    
    # Check for required files
    required_files = [
        "requirements.txt",
        "mcp_server.py",
        "test_mcp_server.py",
        "test_basic.py",
        "test_imports_simple.py",
        "test_config.py",
        "test_file_structure.py",
        "test_requirements.py",
        "test_yaml.py",
        "run_tests.py"
    ]
    
    for file in required_files:
        if Path(file).exists():
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} missing")
            return False
    
    return True

def main():
    """Run all environment tests"""
    print("=" * 50)
    print("CI Environment Test")
    print("=" * 50)
    
    tests = [
        ("Python Version", test_python_version),
        ("Working Directory", test_working_directory),
        ("Pip Packages", test_pip_packages),
        ("Pytest Available", test_pytest_available),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 30)
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("ENVIRONMENT TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Environment is ready for testing!")
        return 0
    else:
        print("⚠️  Environment has issues. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 