#!/bin/bash

# Clean dist directory
rm -rf dist
mkdir -p dist

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

# Build TypeScript code
echo "Building TypeScript..."
./node_modules/.bin/tsc

# Make JavaScript files executable
echo "Making JavaScript files executable..."
chmod +x dist/src/index.js

echo "Build completed successfully!"
echo "You can now run the server with: node dist/src/index.js /path/to/your/database.db"