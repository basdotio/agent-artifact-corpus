#!/usr/bin/env python3
"""
Test script to verify logging setup works correctly.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("Testing logging setup...")
print(f"Current directory: {os.getcwd()}")
print(f"LOG_LLM_CALLS: {os.getenv('LOG_LLM_CALLS', 'true')}")
print(f"LOG_OUTPUT: {os.getenv('LOG_OUTPUT', 'file')}")
print(f"LOG_FILE: {os.getenv('LOG_FILE', 'claimify_llm.log')}")
print()

# Import and create LLM client
from llm_client import LLMClient

print("Creating LLM client (this should trigger logging setup)...")
client = LLMClient()

print(f"\nLogger created: {client.logger is not None}")
if client.logger:
    print(f"Logger name: {client.logger.name}")
    print(f"Logger handlers: {client.logger.handlers}")
    print(f"Logger level: {client.logger.level}")
    
    # Try to write a test log message
    print("\nWriting test log message...")
    client.logger.info("TEST LOG MESSAGE - If you see this in the log file, logging is working!")
    
    # Check if log file exists
    log_file = os.getenv('LOG_FILE', 'claimify_llm.log')
    if os.path.exists(log_file):
        print(f"\n✓ Log file created: {log_file}")
        print("Contents:")
        with open(log_file, 'r') as f:
            print(f.read())
    else:
        print(f"\n✗ Log file NOT created: {log_file}")
else:
    print("✗ Logger is None - logging disabled")
