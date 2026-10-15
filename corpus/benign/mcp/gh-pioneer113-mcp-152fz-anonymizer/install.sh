#!/bin/bash
set -e

echo "=== 152-FZ MCP Server Installer ==="

# 1. Check Python
echo "[*] Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed."
    exit 1
fi

# 2. Virtual Environment
if [ ! -d "venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv venv
else
    echo "[*] Virtual environment already exists."
fi

source venv/bin/activate

# 3. Dependencies
echo "[*] Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Spacy Model
echo "[*] Downloading Russian NLP model (ru_core_news_lg)..."
# Check if model is already present to save time/traffic would be nice, but simple download is safer for version consistecy
python -m spacy download ru_core_news_lg

echo "=== Installation Complete ==="
echo ""
echo "To run the server manually:"
echo "  source venv/bin/activate"
echo "  mcp run main.py"
echo ""
echo "To use via SSH (from your local machine):"
echo "  npx -y @modelcontextprotocol/inspector ssh user@your_vps_ip \"cd $(pwd) && source venv/bin/activate && python main.py\""
