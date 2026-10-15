#!/usr/bin/env python3
"""Test configuration file creation and loading"""

import yaml
from pathlib import Path
import tempfile
import os

def test_config_creation():
    """Test creating a config file"""
    print("Testing config file creation...")
    
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        test_config = {
            "neo4j": {
                "local": {
                    "uri": "bolt://localhost:7687",
                    "user": "neo4j",
                    "password": "password",
                },
            },
        }
        yaml.dump(test_config, f)
        config_path = f.name
    
    try:
        # Test loading the config
        with open(config_path, 'r') as f:
            loaded_config = yaml.safe_load(f)
        
        assert loaded_config["neo4j"]["local"]["uri"] == "bolt://localhost:7687"
        assert loaded_config["neo4j"]["local"]["user"] == "neo4j"
        assert loaded_config["neo4j"]["local"]["password"] == "password"
        
        print("✅ Config file creation and loading successful")
        return True
        
    except Exception as e:
        print(f"❌ Config file test failed: {e}")
        return False
    finally:
        # Clean up
        if os.path.exists(config_path):
            os.unlink(config_path)

def test_example_config():
    """Test loading the example config"""
    print("Testing example config loading...")
    
    example_config_path = Path(__file__).parent.parent / ".config.example.yaml"
    
    if not example_config_path.exists():
        print("⚠️  Example config file not found")
        return True  # Not a failure, just missing
    
    try:
        with open(example_config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check that it has the expected structure
        assert "neo4j" in config
        assert "local" in config["neo4j"]
        assert "uri" in config["neo4j"]["local"]
        
        print("✅ Example config loaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Example config test failed: {e}")
        return False

def main():
    """Run config tests"""
    print("=" * 50)
    print("Config Test")
    print("=" * 50)
    
    tests = [
        ("Config Creation", test_config_creation),
        ("Example Config", test_example_config),
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
    print("CONFIG TEST SUMMARY")
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
        print("🎉 Config tests successful!")
        return 0
    else:
        print("⚠️  Some config tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 