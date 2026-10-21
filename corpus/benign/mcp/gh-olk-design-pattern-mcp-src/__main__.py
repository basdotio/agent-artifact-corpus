"""This __main__.py delegates to the click CLI defined in src.main (python -m src)."""

from src.main import cli

if __name__ == "__main__":
    cli()
