#!/usr/bin/env python3
"""Simple test to verify test imports work"""

import sys
from pathlib import Path

def test_basic_imports():
    """Test basic imports that should always work"""
    print("Testing basic imports...")
    
    # Test standard library imports
    try:
        import asyncio
        print("✅ asyncio imported")
    except ImportError as e:
        print(f"❌ asyncio import failed: {e}")
        return False
    
    try:
        import json
        print("✅ json imported")
    except ImportError as e:
        print(f"❌ json import failed: {e}")
        return False
    
    try:
        import logging
        print("✅ logging imported")
    except ImportError as e:
        print(f"❌ logging import failed: {e}")
        return False
    
    return True

def test_third_party_imports():
    """Test third-party imports"""
    print("Testing third-party imports...")
    
    try:
        import yaml
        print("✅ yaml imported")
    except ImportError as e:
        print(f"❌ yaml import failed: {e}")
        # Try alternative import names
        try:
            import PyYAML
            print("✅ PyYAML imported (alternative name)")
        except ImportError:
            print("❌ Both yaml and PyYAML imports failed")
            return False
    
    try:
        import neo4j
        print("✅ neo4j imported")
    except ImportError as e:
        print(f"❌ neo4j import failed: {e}")
        return False
    
    try:
        import pydantic
        print("✅ pydantic imported")
    except ImportError as e:
        print(f"❌ pydantic import failed: {e}")
        return False
    
    try:
        import aiohttp
        print("✅ aiohttp imported")
    except ImportError as e:
        print(f"❌ aiohttp import failed: {e}")
        return False
    
    return True

def test_local_imports():
    """Test local imports"""
    print("Testing local imports...")
    
    # Add parent src directory to path
    sys.path.append(str(Path(__file__).parent.parent / "src"))
    
    try:
        from models import MCPServer, OperationType, RegistrySource, ServerCategory
        print("✅ models imported")
    except ImportError as e:
        print(f"❌ models import failed: {e}")
        return False
    
    try:
        from mcp_server import ASKGMCPServer, ServerSearchRequest, ServerSearchResult
        print("✅ mcp_server imported")
    except ImportError as e:
        print(f"❌ mcp_server import failed: {e}")
        return False
    
    return True

def test_pytest_imports():
    """Test pytest imports"""
    print("Testing pytest imports...")
    
    try:
        import pytest
        print("✅ pytest imported")
    except ImportError as e:
        print(f"❌ pytest import failed: {e}")
        return False
    
    try:
        import pytest_asyncio
        print("✅ pytest-asyncio imported")
    except ImportError as e:
        print(f"⚠️  pytest-asyncio import failed (optional): {e}")
    
    return True

def main():
    """Run all import tests"""
    print("=" * 50)
    print("Import Test")
    print("=" * 50)
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("Third-party Imports", test_third_party_imports),
        ("Local Imports", test_local_imports),
        ("Pytest Imports", test_pytest_imports),
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
    print("IMPORT TEST SUMMARY")
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
        print("🎉 All imports successful!")
        return 0
    else:
        print("⚠️  Some imports failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 