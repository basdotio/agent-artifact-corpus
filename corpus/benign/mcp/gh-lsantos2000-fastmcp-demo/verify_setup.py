"""
Quick verification script to ensure everything is ready for GitHub publishing.
"""

import os
import sys


def check_file_exists(filename, description=""):
    """Check if a file exists and report status."""
    if os.path.exists(filename):
        print(f"✅ {filename} {description}")
        return True
    else:
        print(f"❌ {filename} {description}")
        return False


def main():
    print("🔍 FastMCP Demo - Pre-publish Verification")
    print("=" * 45)

    # Check essential files
    essential_files = [
        ("README.md", "- Main documentation"),
        ("README.github.md", "- GitHub-optimized README"),
        ("README.LinkedInPost.md", "- LinkedIn article"),
        ("LICENSE", "- MIT License"),
        (".gitignore", "- Git ignore rules"),
        ("demo.py", "- Main server file"),
        ("requirements.txt", "- Dependencies"),
        ("pyproject.toml", "- Project configuration"),
    ]

    print("\n📁 Essential Files:")
    all_essential = True
    for filename, desc in essential_files:
        if not check_file_exists(filename, desc):
            all_essential = False

    # Check tools directory
    print("\n🛠️ Tools Package:")
    tools_files = [
        ("tools/__init__.py", "- Package initialization"),
        ("tools/math_tools.py", "- Mathematical operations"),
        ("tools/text_tools.py", "- Text processing"),
    ]

    all_tools = True
    for filename, desc in tools_files:
        if not check_file_exists(filename, desc):
            all_tools = False

    # Check tests directory
    print("\n🧪 Test Suite:")
    test_files = [
        ("tests/__init__.py", "- Test package"),
        ("tests/test_math_tools.py", "- Math tools tests"),
        ("tests/test_text_tools.py", "- Text tools tests"),
        ("tests/test_integration.py", "- Integration tests"),
        ("tests/run_tests.py", "- Test runner"),
        ("tests/README.md", "- Test documentation"),
    ]

    all_tests = True
    for filename, desc in test_files:
        if not check_file_exists(filename, desc):
            all_tests = False

    # Check CI/CD
    print("\n🔄 CI/CD Pipeline:")
    cicd_files = [
        (".github/workflows/ci.yml", "- GitHub Actions workflow"),
    ]

    all_cicd = True
    for filename, desc in cicd_files:
        if not check_file_exists(filename, desc):
            all_cicd = False

    # Check Git status
    print("\n📦 Git Repository:")
    if os.path.exists(".git"):
        print("✅ .git directory exists - Repository initialized")
        git_ready = True
    else:
        print("❌ .git directory missing - Repository not initialized")
        git_ready = False

    # Test imports
    print("\n🔧 Import Tests:")
    try:
        sys.path.insert(0, '.')
        import demo
        print("✅ demo.py imports successfully")
        demo_import = True
    except Exception as e:
        print(f"❌ demo.py import failed: {e}")
        demo_import = False

    try:
        from tools import add, multiply, calculate, greet
        print("✅ All tools import successfully")
        tools_import = True
    except Exception as e:
        print(f"❌ Tools import failed: {e}")
        tools_import = False

    # Summary
    print("\n" + "=" * 45)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 45)

    checks = [
        ("Essential Files", all_essential),
        ("Tools Package", all_tools),
        ("Test Suite", all_tests),
        ("CI/CD Pipeline", all_cicd),
        ("Git Repository", git_ready),
        ("Demo Import", demo_import),
        ("Tools Import", tools_import),
    ]

    passed = sum(1 for _, status in checks if status)
    total = len(checks)

    for check_name, status in checks:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {check_name}")

    print(f"\n🎯 Overall Status: {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 ALL CHECKS PASSED! Your project is ready for GitHub!")
        print("\n🚀 Next steps:")
        print("1. Create a new repository on GitHub")
        print("2. Add remote: git remote add origin https://github.com/USERNAME/fastmcp-demo.git")
        print("3. Push to GitHub: git branch -M main && git push -u origin main")
        return True
    else:
        print(
            f"\n⚠️  {total - passed} issues found. Please fix them before publishing.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
