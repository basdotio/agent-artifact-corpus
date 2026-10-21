import os
import sys

# When running pytest from within the backend/ directory, the backend/ directory
# is placed on sys.path (or cwd is ''), which causes `import mcp` to resolve to the
# local `backend/mcp` package instead of the installed third-party `mcp` library.
# Ensure the repository root is on sys.path and remove backend/ from sys.path.
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# If backend/mcp was already imported as `mcp`, drop it from sys.modules
if "mcp" in sys.modules:
    mod_file = getattr(sys.modules["mcp"], "__file__", "") or ""
    if mod_file.startswith(backend_dir):
        del sys.modules["mcp"]

# Temporarily remove backend_dir from sys.path to import third-party mcp into sys.modules
orig_path = list(sys.path)
try:
    sys.path = [p for p in sys.path if os.path.abspath(p or ".") != backend_dir]
    import mcp
    import mcp.server
    import mcp.types
finally:
    sys.path = orig_path

