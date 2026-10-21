@echo off
REM publish.bat - Windows script to help publish the FastMCP Demo to GitHub

echo 🚀 FastMCP Demo - GitHub Publishing Helper
echo =========================================

REM Check if git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Git is not installed. Please install Git first.
    pause
    exit /b 1
)

REM Check if we're in a git repository
if not exist ".git" (
    echo 📁 Initializing Git repository...
    git init
    echo ✅ Git repository initialized
) else (
    echo ✅ Git repository already exists
)

REM Stage all files
echo 📝 Staging files...
git add .

REM Check git status
echo 📊 Git status:
git status --short

REM Prompt for commit message
echo.
set /p commit_msg="📝 Enter commit message (or press Enter for default): "
if "%commit_msg%"=="" set commit_msg=Initial commit: FastMCP Demo with modular architecture and comprehensive testing

REM Commit changes
echo 💾 Committing changes...
git commit -m "%commit_msg%"

echo.
echo 🎯 Next Steps:
echo 1. Create a new repository on GitHub:
echo    - Go to https://github.com/new
echo    - Name: fastmcp-demo (or your preferred name)
echo    - Description: Production-ready FastMCP server with advanced calculator and comprehensive testing
echo    - Make it public
echo    - DON'T initialize with README (we already have one)
echo.
echo 2. Add your GitHub repository as remote:
echo    git remote add origin https://github.com/YOUR_USERNAME/fastmcp-demo.git
echo.
echo 3. Push to GitHub:
echo    git branch -M main
echo    git push -u origin main
echo.
echo 4. Optional: Update the README.github.md file with your actual GitHub username
echo    and rename it to README.md to replace the current one
echo.
echo ✨ Your FastMCP Demo is ready for GitHub!
echo.
echo 📈 Repository will include:
echo    ✅ 4 powerful tools (add, multiply, calculate, greet)
echo    ✅ 36 comprehensive tests
echo    ✅ Security-validated calculator
echo    ✅ Professional documentation
echo    ✅ CI/CD pipeline
echo    ✅ Modular architecture

pause
