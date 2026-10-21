#!/bin/bash

echo "Starting SVN MCP Server..."

# Check whether Node.js is available
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed or not in PATH"
    exit 1
fi

# Check whether the project has been built
if [ ! -f "dist/index.js" ]; then
    echo "Building the project..."
    npm run build
    if [ $? -ne 0 ]; then
        echo "Error: Build failed"
        exit 1
    fi
fi

# Run the MCP server
echo "Running SVN MCP Server..."
node dist/index.js
