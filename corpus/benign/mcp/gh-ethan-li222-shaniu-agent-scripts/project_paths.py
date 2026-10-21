"""Resolve optional engine checkouts without a developer-specific drive path."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def moneyprinter_project():
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    path = Path(os.getenv('SHANIU_MPT_PROJECT') or 'vendor/moneyprinter').expanduser()
    return (path if path.is_absolute() else ROOT / path).resolve()
