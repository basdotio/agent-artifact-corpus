import os

import uvicorn
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    from .server import create_starlette_app

    app = create_starlette_app()
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8000"))

    print(f"GitLab MCP server starting on http://{host}:{port}")
    print(f"  SSE endpoint : http://{host}:{port}/sse")
    print(f"  GitLab URL   : {os.environ.get('GITLAB_URL', 'https://gitlab.com')}")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
