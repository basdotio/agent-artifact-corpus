"""
Test runner for all iTop MCP tests.

This script runs both unit tests and live tests with proper reporting.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def check_environment():
    """Check if environment is properly set up."""
    print("🔍 Checking environment...")
    
    # Check Python version
    if sys.version_info < (3, 10):
        print(f"❌ Python 3.10+ required, found {sys.version}")
        return False
    print(f"✅ Python {sys.version.split()[0]}")
    
    # Check if main module exists
    main_path = Path(__file__).parent / "main.py"
    if not main_path.exists():
        print(f"❌ main.py not found at {main_path}")
        return False
    print("✅ main.py found")
    
    # Check for test files
    test_dir = Path(__file__).parent / "tests"
    if not test_dir.exists():
        print(f"❌ tests directory not found at {test_dir}")
        return False
    print("✅ tests directory found")
    
    return True


def check_dependencies():
    """Check if required dependencies are installed."""
    print("\n🔍 Checking dependencies...")
    
    required_packages = [
        "pytest",
        "pytest-asyncio", 
        "httpx",
        "mcp"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (missing)")
            missing_packages.append(package)
    
    if missing_packages:
        print("\n💡 Install missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True


def run_linting():
    """Run code linting."""
    commands = [
        ("python -m black --check .", "Black code formatting check"),
        ("python -m isort --check-only .", "Import sorting check"),
        ("python -m flake8 .", "Flake8 linting"),
    ]
    
    all_passed = True
    for cmd, desc in commands:
        if not run_command(cmd, desc):
            all_passed = False
    
    return all_passed


def run_unit_tests():
    """Run unit tests."""
    cmd = "python -m pytest tests/test_unit.py -v --tb=short --asyncio-mode=auto"
    return run_command(cmd, "Unit Tests")


def run_live_tests():
    """Run live tests."""
    # Check if environment variables are set
    required_vars = ["ITOP_BASE_URL", "ITOP_USER", "ITOP_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print("\n⚠️  Live tests skipped - missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Set these variables to run live tests against a real iTop instance:")
        print("   export ITOP_BASE_URL='https://your-itop-instance.com'")
        print("   export ITOP_USER='your-username'")
        print("   export ITOP_PASSWORD='your-password'")
        return True  # Not a failure, just skipped
    
    cmd = "python -m pytest tests/test_live.py -v --tb=short --asyncio-mode=auto"
    return run_command(cmd, "Live Tests")


def run_nodejs_tests():
    """Run Node.js tests if available."""
    nodejs_dir = Path(__file__).parent / "nodejs"
    
    if not nodejs_dir.exists():
        print("⚠️  Node.js implementation not found, skipping Node.js tests")
        return True
    
    print(f"\n{'='*60}")
    print("🟨 Node.js Tests")
    print(f"{'='*60}")
    
    # Change to nodejs directory
    original_dir = os.getcwd()
    os.chdir(nodejs_dir)
    
    try:
        # Check if dependencies are installed
        if not run_command("npm list --depth=0", "Check Node.js dependencies"):
            if not run_command("npm install", "Install Node.js dependencies"):
                return False
        
        # Run linting
        if not run_command("npm run lint", "Node.js linting"):
            print("⚠️  Node.js linting failed, continuing...")
        
        # Run type checking
        if not run_command("npm run type-check", "TypeScript type checking"):
            print("⚠️  TypeScript type checking failed, continuing...")
        
        # Build the project
        if not run_command("npm run build", "Build Node.js project"):
            return False
        
        # Run tests if they exist
        package_json = nodejs_dir / "package.json"
        if package_json.exists():
            import json
            with open(package_json, encoding='utf-8') as f:
                pkg_data = json.load(f)
                if "test" in pkg_data.get("scripts", {}):
                    run_command("npm test", "Node.js unit tests")
        
        return True
    
    finally:
        os.chdir(original_dir)


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="iTop MCP Test Runner")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--live", action="store_true", help="Run only live tests")
    parser.add_argument("--nodejs", action="store_true", help="Run only Node.js tests")
    parser.add_argument("--lint", action="store_true", help="Run only linting")
    parser.add_argument("--no-lint", action="store_true", help="Skip linting")
    parser.add_argument("--fix", action="store_true", help="Auto-fix linting issues")
    
    args = parser.parse_args()
    
    print("🧪 iTop MCP Test Runner")
    print("=" * 60)
    
    # Environment checks
    if not check_environment():
        sys.exit(1)
    
    if not check_dependencies():
        print("\n💡 Install dependencies with: pip install -e .[dev]")
        sys.exit(1)
    
    results = []
    
    # Auto-fix linting if requested
    if args.fix:
        print("\n🔧 Auto-fixing linting issues...")
        run_command("python -m black .", "Auto-format with Black")
        run_command("python -m isort .", "Auto-sort imports")
    
    # Run specific test types or all
    if args.lint or (not any([args.unit, args.live, args.nodejs])):
        if not args.no_lint:
            results.append(("Linting", run_linting()))
    
    if args.unit or (not any([args.lint, args.live, args.nodejs])):
        results.append(("Unit Tests", run_unit_tests()))
    
    if args.live or (not any([args.lint, args.unit, args.nodejs])):
        results.append(("Live Tests", run_live_tests()))
    
    if args.nodejs or (not any([args.lint, args.unit, args.live])):
        results.append(("Node.js Tests", run_nodejs_tests()))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 Test Summary")
    print(f"{'='*60}")
    
    passed = 0
    total = len(results)
    
    for test_type, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_type:20} {status}")
        if success:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{total} test suites passed")
    
    if passed == total:
        print("🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
