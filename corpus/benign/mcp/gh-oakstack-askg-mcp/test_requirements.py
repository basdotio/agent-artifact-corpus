#!/usr/bin/env python3
"""Test requirements.txt file and package installation"""

import subprocess
import sys
from pathlib import Path

def test_requirements_file():
    """Test that requirements.txt file is valid"""
    print("Testing requirements.txt file...")
    
    requirements_path = Path("requirements.txt")
    if not requirements_path.exists():
        print("❌ requirements.txt not found")
        return False
    
    print(f"✅ requirements.txt exists at {requirements_path.absolute()}")
    
    # Read and display the contents
    with open(requirements_path, 'r') as f:
        content = f.read()
        print("Requirements.txt contents:")
        print(content)
    
    return True

def test_individual_packages():
    """Test installing packages individually"""
    print("Testing individual package installation...")
    
    packages = [
        "PyYAML>=6.0",
        "neo4j>=5.0.0",
        "pydantic>=2.0.0",
        "aiohttp>=3.8.0",
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0"
    ]
    
    for package in packages:
        try:
            print(f"Installing {package}...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", package
            ], capture_output=True, text=True, check=True)
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")
            if e.stdout:
                print(f"STDOUT: {e.stdout}")
            if e.stderr:
                print(f"STDERR: {e.stderr}")
            return False
    
    return True

def test_imports_after_installation():
    """Test that packages can be imported after installation"""
    print("Testing imports after installation...")
    
    imports = [
        ("yaml", "pyyaml"),
        ("neo4j", "neo4j"),
        ("pydantic", "pydantic"),
        ("aiohttp", "aiohttp"),
        ("pytest", "pytest"),
        ("pytest_asyncio", "pytest-asyncio")
    ]
    
    for import_name, package_name in imports:
        try:
            __import__(import_name)
            print(f"✅ {package_name} imported successfully")
        except ImportError as e:
            print(f"❌ {package_name} import failed: {e}")
            return False
    
    return True

def main():
    """Run requirements tests"""
    print("=" * 50)
    print("Requirements Test")
    print("=" * 50)
    
    tests = [
        ("Requirements File", test_requirements_file),
        ("Individual Packages", test_individual_packages),
        ("Import Test", test_imports_after_installation),
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
    print("REQUIREMENTS TEST SUMMARY")
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
        print("🎉 Requirements tests successful!")
        return 0
    else:
        print("⚠️  Some requirements tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 