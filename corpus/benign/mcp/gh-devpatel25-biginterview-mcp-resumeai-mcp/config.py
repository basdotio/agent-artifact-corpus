"""Settings loaded from env / .env (paths, timeouts, pacing)."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    base_url: str
    data_dir: Path
    profile_dir: Path
    headless: bool
    browser_channel: str | None
    nav_timeout_ms: int
    human_delay_min_s: float
    human_delay_max_s: float


def load_settings() -> Settings:
    load_dotenv()
    env = os.environ.get
    data_dir = Path(env("DATA_DIR", "~/.resumeai-mcp")).expanduser()
    return Settings(
        base_url=env("BASE_URL", "https://neu.biginterview.com").rstrip("/"),
        data_dir=data_dir,
        profile_dir=Path(env("PROFILE_DIR", str(data_dir / "resumeai-profile"))).expanduser(),
        headless=env("HEADLESS", "true").lower() in ("1", "true", "yes"),
        browser_channel=env("BROWSER_CHANNEL", "chrome") or None,
        nav_timeout_ms=int(env("NAV_TIMEOUT_MS", "30000")),
        human_delay_min_s=float(env("HUMAN_DELAY_MIN_S", "2")),
        human_delay_max_s=float(env("HUMAN_DELAY_MAX_S", "5")),
    )


def private_dir(path: Path) -> Path:
    """Create `path` (and parents) and force 0700 — mkdir's mode is subject to umask (§14)."""
    path.mkdir(parents=True, exist_ok=True)
    path.chmod(0o700)
    return path
