#!/usr/bin/env python3
"""
Test script for Claude Thread Continuity MCP Server

This script tests the basic functionality of the server to ensure it's working correctly.
Run this before setting up the server with Claude Desktop.
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add the current directory to Python path so we can import the server
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from server import ProjectState, ContinuityServer
    print("✅ Successfully imported server modules")
except ImportError as e:
    print(f"❌ Failed to import server modules: {e}")
    print("Make sure you're running this from the directory containing server.py")
    sys.exit(1)

async def test_project_state():
    """Test the ProjectState class functionality."""
    print("\n🧪 Testing ProjectState class...")
    
    # Use a temporary directory for testing
    test_dir = Path("/tmp/claude_continuity_test")
    storage = ProjectState(str(test_dir))
    
    # Test data
    test_project = "test-project"
    test_data = {
        "current_focus": "Testing the continuity system",
        "technical_decisions": ["Using Python for MCP server", "JSON for data storage"],
        "files_modified": ["server.py", "test_server.py"],
        "next_actions": ["Run integration tests", "Deploy to production"],
        "conversation_summary": "Building and testing Claude Thread Continuity MCP server"
    }
    
    try:
        # Test saving
        print("  📝 Testing save_state...")
        result = await storage.save_state(test_project, test_data)
        if result.get('success'):
            print("  ✅ save_state successful")
        else:
            print(f"  ❌ save_state failed: {result.get('message')}")
            return False
        
        # Test loading
        print("  📖 Testing load_state...")
        loaded_data = await storage.load_state(test_project)
        if loaded_data:
            print("  ✅ load_state successful")
            # Verify data integrity
            if loaded_data.get("current_focus") == test_data["current_focus"]:
                print("  ✅ Data integrity verified")
            else:
                print("  ❌ Data integrity check failed")
                return False
        else:
            print("  ❌ load_state returned None")
            return False
        
        # Test listing projects
        print("  📋 Testing list_projects...")
        projects = storage.list_projects()
        if projects and any(p["name"] == test_project for p in projects):
            print("  ✅ list_projects successful")
        else:
            print("  ❌ list_projects failed or project not found")
            return False
        
        # Test project summary
        print("  📊 Testing get_project_summary...")
        summary = await storage.get_project_summary(test_project)
        if summary and "Testing the continuity system" in summary:
            print("  ✅ get_project_summary successful")
        else:
            print("  ❌ get_project_summary failed")
            return False
        
        # Test auto-save checkpoint
        print("  💾 Testing auto_save_checkpoint...")
        checkpoint_success = await storage.auto_save_checkpoint(test_project, "test_trigger", "Testing checkpoint functionality")
        if checkpoint_success:
            print("  ✅ auto_save_checkpoint successful")
        else:
            print("  ❌ auto_save_checkpoint failed")
            return False
        
        # Cleanup
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print("  🧹 Cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_project_validation():
    """Test the new project validation functionality."""
    print("\n🧪 Testing Project Validation features...")
    
    # Use a temporary directory for testing
    test_dir = Path("/tmp/claude_continuity_validation_test")
    storage = ProjectState(str(test_dir))
    
    try:
        # Create some test projects with similar names
        projects_to_create = [
            "Hebrew Evaluation MVP",
            "Test Project Alpha", 
            "Website Development"
        ]
        
        print("  📝 Creating test projects...")
        for project_name in projects_to_create:
            test_data = {
                "current_focus": f"Working on {project_name}",
                "conversation_summary": f"Test project for {project_name}"
            }
            result = await storage.save_state(project_name, test_data, force=True)
            if not result.get('success'):
                print(f"  ❌ Failed to create test project: {project_name}")
                return False
        print("  ✅ Test projects created")
        
        # Test validation with unique name
        print("  🔍 Testing validation with unique name...")
        validation = storage.validate_project_name("Completely Different Project")
        if validation['is_unique']:
            print("  ✅ Unique name validation successful")
        else:
            print("  ❌ Unique name validation failed")
            return False
        
        # Test validation with similar name (should detect Hebrew Evaluation MVP)
        print("  🔍 Testing validation with similar name...")
        validation = storage.validate_project_name("Hebrew Speaking Evaluation MVP")
        if not validation['is_unique'] and len(validation['similar_projects']) > 0:
            similar_project = validation['similar_projects'][0]
            if 'Hebrew Evaluation MVP' in similar_project['name']:
                print(f"  ✅ Similar name detection successful (found: {similar_project['name']}, similarity: {similar_project['similarity']})")
            else:
                print(f"  ❌ Wrong similar project detected: {similar_project['name']}")
                return False
        else:
            print("  ❌ Similar name validation failed - should have detected similarity")
            return False
        
        # Test save with validation (should fail)
        print("  🚫 Testing save with validation failure...")
        result = await storage.save_state("Hebrew Evaluation Website", {"test": "data"}, force=False)
        if not result.get('success') and result.get('status') == 'validation_required':
            print("  ✅ Save validation correctly prevented similar project creation")
        else:
            print("  ❌ Save validation failed to prevent similar project creation")
            return False
        
        # Test save with force override
        print("  💪 Testing save with force override...")
        result = await storage.save_state("Hebrew Evaluation Website", {"test": "data"}, force=True)
        if result.get('success'):
            print("  ✅ Force override successful")
        else:
            print("  ❌ Force override failed")
            return False
        
        # Test different similarity thresholds
        print("  🎯 Testing different similarity thresholds...")
        validation_strict = storage.validate_project_name("Hebrew Eval MVP", similarity_threshold=0.9)
        validation_loose = storage.validate_project_name("Hebrew Eval MVP", similarity_threshold=0.5)
        
        if len(validation_loose['similar_projects']) >= len(validation_strict['similar_projects']):
            print("  ✅ Similarity threshold working correctly")
        else:
            print("  ❌ Similarity threshold not working as expected")
            return False
        
        # Cleanup
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)
            print("  🧹 Validation test cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error during validation testing: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_server_initialization():
    """Test basic server initialization."""
    print("\n🧪 Testing ContinuityServer initialization...")
    
    try:
        server = ContinuityServer()
        print("  ✅ Server instance created successfully")
        
        # Test async initialization
        init_result = await server.initialize()
        if init_result:
            print("  ✅ Async initialization successful")
        else:
            print("  ⚠️  Async initialization returned False (may still work)")
        
        # Test storage initialization
        storage = await server._ensure_storage_initialized()
        if storage:
            print("  ✅ Storage initialization successful")
        else:
            print("  ❌ Storage initialization failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error during server testing: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_new_tools():
    """Test the new MCP tools for validation."""
    print("\n🧪 Testing new MCP tools...")
    
    try:
        server = ContinuityServer()
        await server.initialize()
        
        # First, create a project to test against
        await server.handle_save_project_state({
            "project_name": "My Test Project",
            "current_focus": "Setup for tool testing",
            "force": True
        })

        # Test validate_project_name tool with a similar name
        print("  🔍 Testing validate_project_name tool...")
        result = await server.handle_validate_project_name({
            "project_name": "My Test Proj",
            "similarity_threshold": 0.7
        })
        
        if result and len(result) > 0 and "SIMILAR PROJECTS FOUND" in result[0].text:
            print("  ✅ validate_project_name tool working")
        else:
            print("  ❌ validate_project_name tool failed")
            # print(f"DEBUG: {result[0].text if result else 'No result'}")
            return False
        
        # Test enhanced save_project_state with validation
        print("  💾 Testing enhanced save_project_state...")
        save_result = await server.handle_save_project_state({
            "project_name": "Unique Save Test Project",
            "current_focus": "Testing enhanced save functionality",
            "force": False
        })
        
        if save_result and len(save_result) > 0 and "✅" in save_result[0].text:
            print("  ✅ Enhanced save_project_state working")
        else:
            print("  ❌ Enhanced save_project_state failed")
            return False
        
        # Cleanup the test project
        import shutil
        test_dir = Path(os.path.expanduser("~/.claude_states/"))
        project_dirs = ["My Test Project", "Unique Save Test Project"]
        for p_dir in project_dirs:
            dir_to_remove = test_dir / p_dir
            if dir_to_remove.exists():
                shutil.rmtree(dir_to_remove)

        return True
        
    except Exception as e:
        print(f"  ❌ Error during new tools testing: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dependencies():
    """Test that all required dependencies are available."""
    print("\n🧪 Testing dependencies...")
    
    dependencies = [
        ("mcp", "MCP SDK"),
        ("mcp.server", "MCP Server"),
        ("mcp.types", "MCP Types"),
        ("json", "JSON (built-in)"),
        ("pathlib", "Pathlib (built-in)"),
        ("asyncio", "Asyncio (built-in)"),
        ("difflib", "Difflib (built-in) - NEW for validation")
    ]
    
    for module_name, description in dependencies:
        try:
            __import__(module_name)
            print(f"  ✅ {description}")
        except ImportError:
            print(f"  ❌ {description} - MISSING!")
            print(f"     Try: pip install {module_name}")
            return False
    
    return True

def main():
    """Run all tests."""
    print("🚀 Claude Thread Continuity MCP Server Test Suite v1.1")
    print("==" * 30)
    
    all_tests_passed = True
    
    # Test dependencies
    if not test_dependencies():
        all_tests_passed = False
        print("\n❌ Dependency tests failed. Please install missing dependencies.")
    
    # Test ProjectState functionality
    try:
        if not asyncio.run(test_project_state()):
            all_tests_passed = False
            print("\n❌ ProjectState tests failed.")
    except Exception as e:
        print(f"\n❌ ProjectState test crashed: {e}")
        all_tests_passed = False

    # Test NEW project validation functionality
    try:
        if not asyncio.run(test_project_validation()):
            all_tests_passed = False
            print("\n❌ Project validation tests failed.")
    except Exception as e:
        print(f"\n❌ Project validation test crashed: {e}")
        all_tests_passed = False
    
    # Test server initialization
    try:
        if not asyncio.run(test_server_initialization()):
            all_tests_passed = False
            print("\n❌ Server initialization tests failed.")
    except Exception as e:
        print(f"\n❌ Server initialization test crashed: {e}")
        all_tests_passed = False
    
    # Test new MCP tools
    try:
        if not asyncio.run(test_new_tools()):
            all_tests_passed = False
            print("\n❌ New tools tests failed.")
    except Exception as e:
        print(f"\n❌ New tools test crashed: {e}")
        all_tests_passed = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("🎉 All tests passed! The enhanced server is ready to use.")
        print("\n✨ NEW FEATURES VALIDATED:")
        print("  • Project name validation with fuzzy matching")
        print("  • Automatic fragmentation prevention")
        print("  • Force override for edge cases")
        print("  • Configurable similarity thresholds")
        print("\nNext steps:")
        print("1. Add the server to your Claude Desktop config")
        print("2. Restart Claude Desktop")
        print("3. Enjoy fragmentation-free project continuity!")
    else:
        print("❌ Some tests failed. Please fix the issues above before using the server.")
    
    return 0 if all_tests_passed else 1

if __name__ == "__main__":
    sys.exit(main())
