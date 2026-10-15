"""Local console entry point."""

from junglebridge_mcp.server import create_server


def main() -> None:
    """Run STDIO without opening a listening socket."""
    create_server().run(transport="stdio", show_banner=False)


if __name__ == "__main__":
    main()
