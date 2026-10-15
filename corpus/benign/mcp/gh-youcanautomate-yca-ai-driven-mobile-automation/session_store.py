"""Session store for managing WebDriver instances."""
from typing import Optional, Dict, Any
from logger import info, error, warn, debug

# Global driver and session state
_driver: Optional[Any] = None
_session_id: Optional[str] = None
_platform: Optional[str] = None
_device_info: Dict[str, Any] = {}
_element_cache: Dict[str, Any] = {}  # Cache for storing found elements


def set_driver(driver: Any, session_id: str, platform: str, device_info: Dict[str, Any] = None) -> None:
    """Set the current driver instance."""
    global _driver, _session_id, _platform, _device_info, _element_cache
    _driver = driver
    _session_id = session_id
    _platform = platform
    _device_info = device_info or {}
    _element_cache = {}  # Clear element cache when setting new driver
    info(f"Driver session set: {session_id} on {platform}")


def get_driver() -> Optional[Any]:
    """Get the current driver instance."""
    return _driver


def get_session_id() -> Optional[str]:
    """Get the current session ID."""
    return _session_id


def get_platform() -> Optional[str]:
    """Get the current platform."""
    return _platform


def get_device_info() -> Dict[str, Any]:
    """Get device information."""
    return _device_info.copy()


def has_active_session() -> bool:
    """Check if there's an active session."""
    return _driver is not None and _session_id is not None


def clear_session() -> None:
    """Clear the current session."""
    global _driver, _session_id, _platform, _device_info, _element_cache
    if _driver:
        try:
            _driver.quit()
        except Exception as e:
            warn(f"Error closing driver: {e}")
    _driver = None
    _session_id = None
    _platform = None
    _device_info = {}
    _element_cache = {}
    info("Session cleared")


def cache_element(element_id: str, element: Any) -> None:
    """Cache a found element by its ID."""
    global _element_cache
    _element_cache[element_id] = element
    debug(f"Cached element: {element_id}")


def get_cached_element(element_id: str) -> Optional[Any]:
    """Get a cached element by its ID."""
    return _element_cache.get(element_id)


def clear_element_cache() -> None:
    """Clear the element cache."""
    global _element_cache
    _element_cache = {}
    info("Element cache cleared")


def safe_delete_session() -> bool:
    """Safely delete current session."""
    if has_active_session():
        try:
            clear_session()
            return True
        except Exception as e:
            error(f"Error deleting session: {e}")
            return False
    return False
