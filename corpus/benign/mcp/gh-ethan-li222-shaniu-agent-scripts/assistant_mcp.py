"""Launch Shaniu MCP; stdout is reserved for protocol messages."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from shaniu.mcp.stdio import main
if __name__ == '__main__':
    main()
