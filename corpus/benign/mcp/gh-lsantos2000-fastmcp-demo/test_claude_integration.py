#!/usr/bin/env python3
"""
Test script to verify Claude Desktop integration for FastMCP Demo
"""

import json
import os
import sys
from pathlib import Path

def check_claude_config():
    """Check if Claude Desktop configuration exists and is valid"""
    print("🔍 Checking Claude Desktop Integration...")
    print("=" * 50)
    
    # Check for config file in common locations
    config_paths = [
        Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",  # Windows
        Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",  # macOS
        Path.home() / ".config" / "Claude" / "claude_desktop_config.json",  # Linux
    ]
    
    config_found = False
    for config_path in config_paths:
        if config_path.exists():
            print(f"✅ Found Claude config at: {config_path}")
            config_found = True
            
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                if 'mcpServers' in config:
                    servers = config['mcpServers']
                    print(f"📊 Found {len(servers)} MCP server(s):")
                    
                    for server_name, server_config in servers.items():
                        print(f"  📦 {server_name}")
                        print(f"     Command: {server_config.get('command', 'N/A')}")
                        print(f"     Args: {server_config.get('args', [])}")
                        print(f"     Working Dir: {server_config.get('cwd', 'N/A')}")
                        
                        # Check if it's our FastMCP demo
                        if 'demo.py' in server_config.get('args', []):
                            print("     🎯 This is our FastMCP Demo server!")
                
                else:
                    print("⚠️  No mcpServers section found in config")
                    
            except json.JSONDecodeError as e:
                print(f"❌ Error reading config file: {e}")
            except Exception as e:
                print(f"❌ Error accessing config file: {e}")
                
            break
    
    if not config_found:
        print("⚠️  No Claude Desktop config found in standard locations")
        print("💡 You may need to manually copy claude_desktop_config.json to the Claude config directory")
    
    return config_found

def check_server_files():
    """Check if all required server files exist"""
    print("\n🔍 Checking Server Files...")
    print("=" * 30)
    
    required_files = [
        "demo.py",
        "tools/__init__.py",
        "tools/math_tools.py",
        "tools/text_tools.py",
        "requirements.txt",
        "claude_desktop_config.json"
    ]
    
    all_files_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing!")
            all_files_exist = False
    
    return all_files_exist

def check_dependencies():
    """Check if required Python packages are installed"""
    print("\n🔍 Checking Dependencies...")
    print("=" * 25)
    
    required_packages = ["fastmcp", "mcp", "pydantic"]
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - Not installed!")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n💡 Install missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True

def test_server_functionality():
    """Test if the server tools work correctly"""
    print("\n🔍 Testing Server Functionality...")
    print("=" * 32)
    
    try:
        # Import tools directly
        sys.path.append('.')
        from tools.math_tools import add, multiply, calculate
        from tools.text_tools import greet
        
        # Test each tool
        tests = [
            ("add(3, 5)", lambda: add(3, 5), 8),
            ("multiply(2.5, 4)", lambda: multiply(2.5, 4), 10.0),
            ("calculate('sqrt(16)')", lambda: calculate('sqrt(16)'), 4.0),
            ("greet('Tester')", lambda: greet('Tester'), "Hello, Tester! Welcome to FastMCP.")
        ]
        
        all_passed = True
        for test_name, test_func, expected in tests:
            try:
                result = test_func()
                if result == expected:
                    print(f"✅ {test_name} → {result}")
                else:
                    print(f"❌ {test_name} → {result} (expected {expected})")
                    all_passed = False
            except Exception as e:
                print(f"❌ {test_name} → Error: {e}")
                all_passed = False
        
        return all_passed
        
    except ImportError as e:
        print(f"❌ Could not import tools: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 FastMCP Demo - Claude Integration Test")
    print("=" * 45)
    
    results = {
        "server_files": check_server_files(),
        "dependencies": check_dependencies(),
        "functionality": test_server_functionality(),
        "claude_config": check_claude_config()
    }
    
    print("\n📋 Test Summary:")
    print("=" * 15)
    
    all_good = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
        if not passed:
            all_good = False
    
    print("\n" + "=" * 45)
    if all_good:
        print("🎉 All tests passed! Your FastMCP server is ready for Claude!")
        print("\n💡 Next steps:")
        print("1. Restart Claude Desktop")
        print("2. Ask Claude: 'What tools do you have available?'")
        print("3. Test with: 'Add 3 and 5' or 'Calculate sqrt(64)'")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        print("\n💡 Common fixes:")
        print("1. Make sure you're in the fastmcp_demo directory")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Run: fastmcp install claude-desktop demo.py")
    
    return all_good

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
