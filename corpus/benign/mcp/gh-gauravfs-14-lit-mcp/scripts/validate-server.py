#!/usr/bin/env python3
"""
Validate server.json against the MCP schema.
This script can be used locally or in CI to ensure the server.json is valid.
"""

import json
import sys
import urllib.request
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("❌ jsonschema library not found. Install with: uv add jsonschema --dev")
    sys.exit(1)


def validate_server_json():
    """Validate server.json against the MCP schema."""
    server_json_path = Path("server.json")
    
    if not server_json_path.exists():
        print("❌ server.json not found in current directory")
        return False
    
    try:
        # Load the schema
        schema_url = 'https://static.modelcontextprotocol.io/schemas/2025-09-29/server.schema.json'
        print(f"📥 Fetching schema from {schema_url}...")
        schema = json.loads(urllib.request.urlopen(schema_url).read())
        
        # Load our server.json
        print("📄 Loading server.json...")
        with open(server_json_path, 'r') as f:
            data = json.load(f)
        
        # Validate
        print("🔍 Validating against MCP schema...")
        jsonschema.validate(data, schema)
        print("✅ server.json is valid against the MCP schema!")
        return True
        
    except jsonschema.ValidationError as e:
        print(f"❌ Validation error: {e.message}")
        print(f"   Path: {'.'.join(str(p) for p in e.absolute_path)}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = validate_server_json()
    sys.exit(0 if success else 1)
