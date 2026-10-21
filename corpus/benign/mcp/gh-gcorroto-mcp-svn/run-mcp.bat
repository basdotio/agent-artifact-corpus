@echo off
echo Starting SVN MCP Server...

REM Check whether Node.js is available
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Node.js is not installed or not in PATH
    pause
    exit /b 1
)

REM Check whether the project has been built
if not exist "dist\index.js" (
    echo Building the project...
    npm run build
    if %errorlevel% neq 0 (
        echo Error: Build failed
        pause
        exit /b 1
    )
)

REM Run the MCP server
echo Running SVN MCP Server...
node dist\index.js

pause
