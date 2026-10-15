"""Session tools: select_platform, select_device, create_session, delete_session."""
from typing import Any, Dict, List, Optional
from appium import webdriver
from appium.options.common import AppiumOptions
import session_store
from logger import info, error, warn


# State for platform and device selection
_selected_platform: Optional[str] = None
_selected_device: Optional[Dict[str, Any]] = None


def select_platform(platform: str) -> Dict[str, Any]:
    """Select platform (iOS or Android)."""
    global _selected_platform
    if platform not in ['ios', 'android']:
        raise ValueError(f"Invalid platform: {platform}")
    
    _selected_platform = platform
    info(f"Platform selected: {platform}")
    return {
        'status': 'success',
        'platform': platform,
        'message': f"Platform {platform} selected"
    }


def get_selected_platform() -> Optional[str]:
    """Get selected platform."""
    return _selected_platform


def select_device(device_id: str, device_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Select device for automation."""
    global _selected_device
    
    _selected_device = {
        'device_id': device_id,
        'device_name': device_name or device_id,
        **kwargs
    }
    
    info(f"Device selected: {device_id}")
    return {
        'status': 'success',
        'device_id': device_id,
        'device_name': _selected_device['device_name'],
        'message': f"Device {device_id} selected"
    }


def get_selected_device() -> Optional[Dict[str, Any]]:
    """Get selected device."""
    return _selected_device.copy() if _selected_device else None


def create_session(
    capabilities: Dict[str, Any],
    appium_server_url: str = "http://localhost:4723",
    **kwargs
) -> Dict[str, Any]:
    """Create new Appium session."""
    try:
        if session_store.has_active_session():
            warn("Active session already exists, deleting old session")
            session_store.safe_delete_session()
        
        # Create options from capabilities
        options = AppiumOptions()
        for key, value in capabilities.items():
            options.set_capability(key, value)
        
        # Create driver
        driver = webdriver.Remote(
            command_executor=appium_server_url,
            options=options
        )
        
        session_id = driver.session_id
        platform = capabilities.get('platformName', 'unknown').lower()
        device_info = {
            'device_name': capabilities.get('appium:deviceName', 'unknown'),
            'platform_version': capabilities.get('appium:platformVersion', 'unknown'),
            'automation_name': capabilities.get('appium:automationName', 'unknown'),
        }
        
        session_store.set_driver(driver, session_id, platform, device_info)
        
        info(f"Session created: {session_id}")
        return {
            'status': 'success',
            'session_id': session_id,
            'platform': platform,
            'device_info': device_info,
            'message': f"Session {session_id} created successfully"
        }
    except Exception as e:
        error(f"Failed to create session: {e}")
        raise


def delete_session() -> Dict[str, Any]:
    """Delete active session."""
    session_id = session_store.get_session_id()
    
    if not session_store.has_active_session():
        warn("No active session to delete")
        return {
            'status': 'warning',
            'message': 'No active session to delete'
        }
    
    try:
        session_store.safe_delete_session()
        info(f"Session deleted: {session_id}")
        return {
            'status': 'success',
            'session_id': session_id,
            'message': f"Session {session_id} deleted successfully"
        }
    except Exception as e:
        error(f"Failed to delete session: {e}")
        raise


def open_notifications() -> Dict[str, Any]:
    """Open notifications panel."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        driver.open_notifications()
        info("Notifications panel opened")
        return {
            'status': 'success',
            'message': 'Notifications panel opened'
        }
    except Exception as e:
        error(f"Failed to open notifications: {e}")
        raise
