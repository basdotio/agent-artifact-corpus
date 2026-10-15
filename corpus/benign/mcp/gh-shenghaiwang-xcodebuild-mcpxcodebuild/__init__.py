from .server import run


def main():
    """MCP xcodebuild Server - Building iOS Xcode workspace/project"""
    import asyncio
    asyncio.run(run())


if __name__ == "__main__":
    main()