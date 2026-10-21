"""The installed SDK version, shared by the command line and the HTTP client."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("leanwarp-sdk")
except PackageNotFoundError:  # Imported from a source tree without installation.
    __version__ = "0.0.0"
