#!/usr/bin/env python3

import json
import subprocess
import sys
import time
import os


def test_mcp_server():
    """Test the MCP server by sending requests directly."""

    # --- START OF FIX ---
    # Get the directory of the current script (testing/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Get the parent directory (the project root)
    project_root = os.path.dirname(script_dir)
    # --- END OF FIX ---

    # Start the MCP server process
    process = subprocess.Popen(
        [sys.executable, "mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0,  # Unbuffered
        cwd=project_root  # Tell the process where to run from
    )

    try:
        # Give the process a moment to start
        time.sleep(2)

        # Initialise the server
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }

        print("Sending initialisation request...")
        request_line = json.dumps(init_request) + "\n"

        # Use communicate() to send data and read output
        stdout_output, stderr_output = process.communicate(input=request_line, timeout=30)

        print("=== STDOUT ===")
        print(stdout_output)
        print("=== STDERR ===")
        print(stderr_output)
        print("=== END ===")

        # Parse responses
        if stdout_output.strip():
            for line in stdout_output.strip().split('\n'):
                if line.strip():
                    try:
                        response = json.loads(line)
                        print(f"Parsed response: {json.dumps(response, indent=2)}")
                    except json.JSONDecodeError:
                        print(f"Non-JSON line: {line}")

    except subprocess.TimeoutExpired:
        print("Process timed out")
        process.kill()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()


def simple_function_test():
    """Test the function directly without MCP protocol."""
    print("=== Testing function directly ===")
    # Add project root to sys.path to allow importing youtube_tool
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    sys.path.insert(0, project_root)

    from youtube_tool import get_youtube_transcript

    try:
        result = get_youtube_transcript("What is an API? by MuleSoft", force_whisper=False)
        print("Direct function result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Direct function error: {e}")


if __name__ == "__main__":
    print("1. Testing MCP server...")
    test_mcp_server()

    print("\n" + "=" * 50 + "\n")

    print("2. Testing function directly...")
    simple_function_test()