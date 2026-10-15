#!/usr/bin/env python3
"""Test file structure and test file discovery"""

import os
from pathlib import Path
import subprocess
import sys

def test_file_structure():
    """Test that all required files exist"""
    print("Testing file structure...")
    
    cwd = Path.cwd()
    print(f"Current working directory: {cwd}")
    
    # Check if we're in the mcp directory
    if cwd.name != "mcp":
        print(f"⚠️  Not in mcp directory, current: {cwd.name}")
        # Try to find the mcp directory
        mcp_dir = cwd / "mcp"
        if mcp_dir.exists():
            print(f"Found mcp directory at: {mcp_dir}")
            os.chdir(mcp_dir)
            cwd = Path.cwd()
            print(f"Changed to: {cwd}")
        else:
            print("❌ Could not find mcp directory")
            return False
    
    # List all files in current directory
    print("Files in current directory:")
    for file in sorted(cwd.iterdir()):
        if file.is_file():
            print(f"  📄 {file.name}")
        elif file.is_dir():
            print(f"  📁 {file.name}/")
    
    # Check for required files
    required_files = [
        "requirements.txt",
        "mcp_server.py",
        "test_mcp_server.py",
        "test_basic.py",
        "test_imports_simple.py",
        "test_config.py",
        "test_environment.py",
        "run_tests.py"
    ]
    
    missing_files = []
    for file in required_files:
        if Path(file).exists():
            print(f"✅ {file} exists")
        else:
            print(f"❌ {file} missing")
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files found")
    return True

def test_python_execution():
    """Test that Python can execute the test files"""
    print("Testing Python execution...")
    
    test_files = [
        "test_basic.py",
        "test_imports_simple.py",
        "test_config.py",
        "test_environment.py"
    ]
    
    for test_file in test_files:
        try:
            result = subprocess.run([
                sys.executable, test_file
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"✅ {test_file} executed successfully")
            else:
                print(f"❌ {test_file} failed with return code {result.returncode}")
                if result.stdout:
                    print(f"STDOUT: {result.stdout}")
                if result.stderr:
                    print(f"STDERR: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"❌ {test_file} timed out")
            return False
        except Exception as e:
            print(f"❌ {test_file} failed with exception: {e}")
            return False
    
    return True

def test_pytest_discovery():
    """Test that pytest can discover test files"""
    print("Testing pytest discovery...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest", "--collect-only", "-q"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ pytest discovery successful")
            print("Discovered tests:")
            for line in result.stdout.split('\n'):
                if line.strip() and not line.startswith('='):
                    print(f"  {line.strip()}")
            return True
        else:
            print(f"❌ pytest discovery failed with return code {result.returncode}")
            if result.stdout:
                print(f"STDOUT: {result.stdout}")
            if result.stderr:
                print(f"STDERR: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ pytest discovery timed out")
        return False
    except Exception as e:
        print(f"❌ pytest discovery failed with exception: {e}")
        return False

def main():
    """Run file structure tests"""
    print("=" * 50)
    print("File Structure Test")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Python Execution", test_python_execution),
        ("Pytest Discovery", test_pytest_discovery),
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
    print("FILE STRUCTURE TEST SUMMARY")
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
        print("🎉 File structure tests successful!")
        return 0
    else:
        print("⚠️  Some file structure tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 