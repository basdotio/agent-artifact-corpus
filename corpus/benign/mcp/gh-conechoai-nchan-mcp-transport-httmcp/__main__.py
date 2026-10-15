#!/usr/bin/env python
import argparse
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from httmcp import OpenAPIMCP


parser = argparse.ArgumentParser(
    prog="httmcp",
    description="HTTMCP CLI - Deploy OpenAPI services with Nchan MCP Transport",
)
parser.add_argument("-f", "--openapi-file", required=True, help="OpenAPI specification URL or file path")
parser.add_argument("-n", "--name", default="", help="Name of this MCP server (default: '')")
parser.add_argument("-p", "--publish-server", required=True, help="Nchan publish server URL (e.g., http://nchan:80)")
parser.add_argument("-H", "--host", default="0.0.0.0", help="Host to bind the server (default: 0.0.0.0)")
parser.add_argument("-P", "--port", type=int, default=8000, help="Port to bind the server (default: 8000)")

args = parser.parse_args()


def create_app():
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Load the OpenAPI specification and create mcp server
        openapi_server = await OpenAPIMCP.from_openapi(
            args.openapi_file,
            name=args.name,
            publish_server=args.publish_server
        )
        app.include_router(openapi_server.router)
        print(f"✅ Successfully mounted OpenAPI from {args.openapi_file}")
        print(f"🔌 Connected to Nchan publish server: {args.publish_server}")
        print(f"🚀 Server running at http://{args.host}:{args.port}")
        print(f"🚀 Server name: {args.name or openapi_server.name}")
        print(f"🚀 Server endpoint: {args.publish_server}{openapi_server.router.prefix}")
        yield

    return FastAPI(lifespan=lifespan)

app = create_app()

def main():
    # Run the server
    uvicorn.run(
        app,
        host=args.host, 
        port=args.port,
    )

if __name__ == "__main__":
    main()
