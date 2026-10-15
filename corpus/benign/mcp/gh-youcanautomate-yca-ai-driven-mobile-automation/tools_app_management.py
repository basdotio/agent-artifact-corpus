"""App management tools: activate_app, install_app, uninstall_app, terminate_app, list_apps, is_app_installed, deep_link."""
from typing import Any, Dict, List, Optional
import session_store
from logger import info, error


def appium_activate_app(app_id: str) -> Dict[str, Any]:
    """Activate an installed app."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        driver.activate_app(app_id)
        info(f"App activated: {app_id}")
        return {
            'status': 'success',
            'app_id': app_id,
            'message': f'App {app_id} activated successfully'
        }
    except Exception as e:
        error(f"Failed to activate app: {e}")
        return {
            'status': 'error',
            'message': f'Failed to activate app {app_id}. Error: {str(e)}'
        }


def appium_install_app(app_path: str) -> Dict[str, Any]:
    """Install an app from path."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        driver.install_app(app_path)
        info(f"App installed: {app_path}")
        return {
            'status': 'success',
            'app_path': app_path,
            'message': f'App {app_path} installed successfully'
        }
    except Exception as e:
        error(f"Failed to install app: {e}")
        return {
            'status': 'error',
            'message': f'Failed to install app {app_path}. Error: {str(e)}'
        }


def appium_uninstall_app(app_id: str) -> Dict[str, Any]:
    """Uninstall an app."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        result = driver.remove_app(app_id)
        info(f"App uninstalled: {app_id}")
        return {
            'status': 'success',
            'app_id': app_id,
            'message': f'App {app_id} uninstalled successfully'
        }
    except Exception as e:
        error(f"Failed to uninstall app: {e}")
        return {
            'status': 'error',
            'message': f'Failed to uninstall app {app_id}. Error: {str(e)}'
        }


def appium_terminate_app(app_id: str) -> Dict[str, Any]:
    """Terminate a running app."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        driver.terminate_app(app_id)
        info(f"App terminated: {app_id}")
        return {
            'status': 'success',
            'app_id': app_id,
            'message': f'App {app_id} terminated successfully'
        }
    except Exception as e:
        error(f"Failed to terminate app: {e}")
        return {
            'status': 'error',
            'message': f'Failed to terminate app {app_id}. Error: {str(e)}'
        }


def appium_list_apps() -> Dict[str, Any]:
    """List all installed apps."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        # Method varies by platform
        platform = session_store.get_platform()
        if platform == 'ios':
            apps = driver.execute_script('mobile: listApps', {'scope': 'user'})
        else:
            apps = driver.execute_script('mobile: queryAppState', {'appPackage': 'com.android.launcher'})
        
        info(f"Listed apps: {len(apps) if isinstance(apps, list) else 1}")
        return {
            'status': 'success',
            'apps': apps if isinstance(apps, list) else [apps],
            'message': 'Apps listed successfully'
        }
    except Exception as e:
        error(f"Failed to list apps: {e}")
        return {
            'status': 'error',
            'message': f'Failed to list apps. Error: {str(e)}'
        }


def appium_is_app_installed(app_id: str) -> Dict[str, Any]:
    """Check if app is installed."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        is_installed = driver.is_app_installed(app_id)
        info(f"App installed check: {app_id} = {is_installed}")
        return {
            'status': 'success',
            'app_id': app_id,
            'is_installed': is_installed,
            'message': f'App {app_id} is {"installed" if is_installed else "not installed"}'
        }
    except Exception as e:
        error(f"Failed to check app installation: {e}")
        return {
            'status': 'error',
            'message': f'Failed to check if app {app_id} is installed. Error: {str(e)}'
        }


def appium_deep_link(url: str) -> Dict[str, Any]:
    """Open deep link."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        driver.execute_script('mobile: deepLink', {'url': url})
        info(f"Deep link opened: {url}")
        return {
            'status': 'success',
            'url': url,
            'message': f'Deep link {url} opened successfully'
        }
    except Exception as e:
        error(f"Failed to open deep link: {e}")
        return {
            'status': 'error',
            'message': f'Failed to open deep link {url}. Error: {str(e)}'
        }
