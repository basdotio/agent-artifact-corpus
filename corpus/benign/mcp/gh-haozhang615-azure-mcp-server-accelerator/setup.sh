#!/bin/bash
# Quick setup script for MCP Azure Container App deployment

set -e  # Exit on any error

echo "🚀 MCP Azure Container App - Quick Setup"
echo "========================================"
echo ""

# Check if azd is installed
if ! command -v azd &> /dev/null; then
    echo "❌ Azure Developer CLI (azd) is not installed"
    echo "📦 Please install it from: https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd"
    exit 1
fi

# Check if user is logged in
if ! azd auth login --check-status &> /dev/null; then
    echo "🔐 Not logged into Azure. Logging in now..."
    azd auth login
else
    echo "✅ Already logged into Azure"
fi

echo ""
echo "✅ Setup complete! You're ready to deploy."
echo ""
echo "� To deploy, simply run:"
echo "   azd up"
echo ""
echo "💡 You will be prompted to choose:"
echo "   - Environment name (unique identifier for your deployment)"
echo "   - Azure region (location where resources will be created)"
echo ""
echo "🎯 That's it! No other configuration needed."
