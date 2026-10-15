#!/usr/bin/env python3
"""Entry point wrapper that ensures .env is loaded before importing chatbot."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# CRITICAL: Load .env BEFORE importing anything else
env_paths = [
    Path(__file__).parent / ".env",  # Script directory
    Path.cwd() / ".env",  # Current working directory
    Path.home() / ".env",  # Home directory
]

for env_path in env_paths:
    if env_path.exists():
        print(f"[DEBUG] Loading .env from: {env_path}")
        load_dotenv(env_path, override=True)
        if os.getenv("BEDROCK_MODEL_ID"):
            print(f"[DEBUG] BEDROCK_MODEL_ID loaded successfully")
        break

# NOW import chatbot after .env is loaded
from chatbot import main

if __name__ == "__main__":
    sys.exit(main())
