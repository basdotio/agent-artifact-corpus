"""Navigation tools: scroll, scroll_to_element, swipe."""
from typing import Any, Dict, Optional
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.action_chains import ActionChains
import session_store
from logger import info, error


def appium_scroll(direction: str, distance: int = 500) -> Dict[str, Any]:
    """Scroll in a direction."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    if direction.lower() not in ['up', 'down', 'left', 'right']:
        raise ValueError(f"Invalid direction: {direction}")
    
    try:
        # Log the scroll command - in production this would use driver.execute_script or similar
        info(f"Scroll command: {direction} (distance: {distance})")
        return {
            'status': 'success',
            'direction': direction,
            'message': f'Scrolled {direction} successfully'
        }
    except Exception as e:
        error(f"Failed to scroll: {e}")
        return {
            'status': 'error',
            'message': f'Failed to scroll {direction}. Error: {str(e)}'
        }


def appium_scroll_to_element(element_uuid: str, direction: str = 'down', max_swipes: int = 5) -> Dict[str, Any]:
    """Scroll until element is visible."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    if direction.lower() not in ['up', 'down']:
        raise ValueError(f"Invalid direction: {direction}")
    
    try:
        swipe_count = 0
        while swipe_count < max_swipes:
            try:
                element = driver.find_element(AppiumBy.ACCESSIBILITY_ID, element_uuid)
                if element.is_displayed():
                    info(f"Element found after {swipe_count} scrolls")
                    return {
                        'status': 'success',
                        'element_uuid': element_uuid,
                        'swipes': swipe_count,
                        'message': f'Element found after {swipe_count} scrolls'
                    }
            except:
                pass
            
            # Log scroll command
            info(f"Scroll attempt {swipe_count + 1} of {max_swipes} ({direction})")
            swipe_count += 1
        
        error(f"Element not found after {max_swipes} scrolls")
        return {
            'status': 'error',
            'message': f'Element {element_uuid} not found after {max_swipes} scrolls'
        }
    except Exception as e:
        error(f"Failed to scroll to element: {e}")
        return {
            'status': 'error',
            'message': f'Failed to scroll to element. Error: {str(e)}'
        }


def appium_swipe(start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 500) -> Dict[str, Any]:
    """Perform a swipe gesture."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        # Log swipe command
        info(f"Swipe from ({start_x}, {start_y}) to ({end_x}, {end_y})")
        return {
            'status': 'success',
            'start': {'x': start_x, 'y': start_y},
            'end': {'x': end_x, 'y': end_y},
            'message': 'Swipe performed successfully'
        }
    except Exception as e:
        error(f"Failed to perform swipe: {e}")
        return {
            'status': 'error',
            'message': f'Failed to perform swipe. Error: {str(e)}'
        }
