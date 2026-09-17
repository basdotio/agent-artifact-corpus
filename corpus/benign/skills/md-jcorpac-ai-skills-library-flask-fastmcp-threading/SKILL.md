---
name: fastmcp-threading
description: Running Flask web servers concurrently with FastMCP standard I/O blocking event loops.
---

# fastmcp-threading

## Purpose
`FastMCP` by default utilizes the main thread's standard inputs and outputs to communicate via the MCP Protocol. This is a blocking loop. If you want to run a management API or dashboard (e.g., using `Flask`) alongside it in the same process, you cannot block the main thread with both loops.

## Usage

Start the `Flask` application inside a separate background thread with `daemon=True`. This keeps the main thread free for `FastMCP`, while allowing the web server to handle background API requests natively.

```python
import threading
from flask import Flask
from mcp.server.fastmcp import FastMCP

app = Flask("Management Interface")
mcp = FastMCP("Tool Service")

@app.route("/")
def index():
    return "API is active"

def main():
    # Start Flask API in a non-blocking background thread
    flask_thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=5000, use_reloader=False)
    )
    flask_thread.daemon = True # Allows program to exit when mcp loop dies
    flask_thread.start()

    # FastMCP blocks the main thread
    mcp.run()

if __name__ == "__main__":
    main()
```

## Resources
- Python Threading Library
- Flask Runtime Considerations
