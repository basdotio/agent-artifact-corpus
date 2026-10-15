#!/usr/bin/env python3
"""
Test script to verify MCP tool works correctly.
"""

import asyncio
import json
from llm_client import LLMClient
from pipeline import ClaimifyPipeline

async def test_extraction():
    """Test the claim extraction pipeline."""
    
    # Read the test file
    with open('text_with_claims.txt', 'r') as f:
        text = f.read()
    
    print("Input text:")
    print("=" * 60)
    print(text)
    print("=" * 60)
    print()
    
    # Initialize client and pipeline
    client = LLMClient()  # No session needed for direct testing
    pipeline = ClaimifyPipeline(client, "What are the facts about Stockholm?")
    
    # Run extraction
    print("Extracting claims...")
    claims = pipeline.run(text)
    
    # Display results
    print()
    print("Extracted Claims:")
    print("=" * 60)
    if claims:
        for i, claim in enumerate(claims, 1):
            print(f"{i}. {claim}")
        print("=" * 60)
        print(f"\nTotal claims extracted: {len(claims)}")
    else:
        print("No claims extracted.")
    print()
    
    # Also show as JSON (as returned by MCP tool)
    print("JSON output (as returned by MCP tool):")
    print(json.dumps(claims, indent=2))

if __name__ == "__main__":
    asyncio.run(test_extraction())
