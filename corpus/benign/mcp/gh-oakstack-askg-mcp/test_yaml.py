#!/usr/bin/env python3
"""Test yaml import and functionality"""

import sys

def test_yaml_import():
    """Test yaml import"""
    print("Testing yaml import...")
    
    try:
        import yaml
        print(f"✅ yaml imported successfully, version: {yaml.__version__}")
        return True
    except ImportError as e:
        print(f"❌ yaml import failed: {e}")
        return False

def test_yaml_functionality():
    """Test yaml functionality"""
    print("Testing yaml functionality...")
    
    try:
        import yaml
        
        # Test basic yaml operations
        test_data = {
            "test": "value",
            "number": 42,
            "list": [1, 2, 3],
            "nested": {"key": "value"}
        }
        
        # Test dump
        yaml_string = yaml.dump(test_data)
        print(f"✅ yaml.dump() works: {yaml_string}")
        
        # Test load
        loaded_data = yaml.safe_load(yaml_string)
        print(f"✅ yaml.safe_load() works: {loaded_data}")
        
        # Test that data matches
        assert loaded_data == test_data, "Loaded data doesn't match original"
        print("✅ Data integrity verified")
        
        return True
        
    except Exception as e:
        print(f"❌ yaml functionality test failed: {e}")
        return False

def main():
    """Run yaml tests"""
    print("=" * 50)
    print("YAML Test")
    print("=" * 50)
    
    tests = [
        ("YAML Import", test_yaml_import),
        ("YAML Functionality", test_yaml_functionality),
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
    print("YAML TEST SUMMARY")
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
        print("🎉 YAML tests successful!")
        return 0
    else:
        print("⚠️  Some YAML tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 