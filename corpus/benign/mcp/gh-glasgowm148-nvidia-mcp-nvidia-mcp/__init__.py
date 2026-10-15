"""Android TV / Fire OS / Apple TV Kodi tools (legacy Shield API retained)."""

__version__ = "0.5.10"

from .config import Config, ShieldError  # noqa: E402
from .device import Shield  # noqa: E402

AndroidTV = Shield


class AppleTV(Shield):
    """Explicit Apple TV backend; raw Android file/shell operations are unavailable."""

    def __init__(self, config, **kwargs):
        if config.platform != "apple_tv":
            raise ShieldError("AppleTV requires Config(platform='apple_tv')")
        super().__init__(config, **kwargs)


__all__ = ["AndroidTV", "AppleTV", "Config", "Shield", "ShieldError", "__version__"]
