"""Interaction tools: click, find, double_tap, long_press, drag_and_drop, press_key, set_value, get_text, screenshot, etc."""
from typing import Any, Dict, List, Optional
from appium.webdriver.common.appiumby import AppiumBy
import session_store
import command
from logger import info, error, debug


def appium_click(element_uuid: str) -> Dict[str, Any]:
    """Click on an element."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    # Validate UUID
    if not element_uuid:
        error("Click attempted with empty/None UUID")
        return {
            'status': 'error',
            'message': 'Failed to click: elementUUID is required but was empty or None'
        }
    
    if isinstance(element_uuid, str) and ("PLACEHOLDER" in element_uuid or "ELEMENT_UUID" in element_uuid):
        error(f"Click attempted with placeholder UUID: {element_uuid}")
        return {
            'status': 'error',
            'message': f'Failed to click: elementUUID is a placeholder "{element_uuid}", not an actual element. Use the UUID from appium_find_element result.'
        }
    
    try:
        command.element_click(driver, element_uuid)
        debug(f"Clicked element: {element_uuid}")
        return {
            'status': 'success',
            'message': f'Successfully clicked on element {element_uuid}',
            'elementUUID': element_uuid
        }
    except Exception as e:
        error(f"Failed to click on element: {e}")
        return {
            'status': 'error',
            'message': f'Failed to click on element {element_uuid}. Error: {str(e)}'
        }


def appium_find_element(strategy: str, selector: str) -> Dict[str, Any]:
    """Find a specific element by strategy and selector."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        results = command.find_elements_by_strategy(driver, strategy, selector)
        if not results:
            error_msg = f"No element found with {strategy}: {selector}"
            error(error_msg)
            return {
                'status': 'warning',
                'message': error_msg,
                'count': 0,
                'strategy': strategy,
                'selector': selector
            }
        
        # For first element, include its UUID prominently
        first_element_uuid = results[0].get('element-6066-11e4-a52e-4f735466cecf', '')
        
        success_msg = f"Found {len(results)} element(s) with {strategy}"
        info(success_msg)
        
        return {
            'status': 'success',
            'elementUUID': first_element_uuid,
            'elements': results,
            'count': len(results),
            'message': success_msg,
            'strategy': strategy,
            'selector': selector
        }
    except Exception as e:
        error_msg = f"Failed to find element with {strategy}: {selector}. Error: {str(e)}"
        error(error_msg)
        return {
            'status': 'error',
            'message': error_msg,
            'count': 0,
            'strategy': strategy,
            'selector': selector
        }


def appium_double_tap(element_uuid: str) -> Dict[str, Any]:
    """Double tap on an element."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        element = driver.find_element(AppiumBy.ACCESSIBILITY_ID, element_uuid)
        actions = TouchAction(driver)
        actions.tap(element, count=2).perform()
        debug(f"Double tapped element: {element_uuid}")
        return {
            'status': 'success',
            'message': f'Successfully double tapped on element {element_uuid}'
        }
    except Exception as e:
        error(f"Failed to double tap: {e}")
        return {
            'status': 'error',
            'message': f'Failed to double tap on element {element_uuid}. Error: {str(e)}'
        }


def appium_long_press(element_uuid: str, duration: int = 2000) -> Dict[str, Any]:
    """Long press on an element."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        element = driver.find_element(AppiumBy.ACCESSIBILITY_ID, element_uuid)
        actions = TouchAction(driver)
        actions.long_press(element, duration=duration).release().perform()
        debug(f"Long pressed element: {element_uuid}")
        return {
            'status': 'success',
            'message': f'Successfully long pressed on element {element_uuid}'
        }
    except Exception as e:
        error(f"Failed to long press: {e}")
        return {
            'status': 'error',
            'message': f'Failed to long press on element {element_uuid}. Error: {str(e)}'
        }


def appium_drag_and_drop(source_uuid: str, target_uuid: str) -> Dict[str, Any]:
    """Drag element to target."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        source = driver.find_element(AppiumBy.ACCESSIBILITY_ID, source_uuid)
        target = driver.find_element(AppiumBy.ACCESSIBILITY_ID, target_uuid)
        actions = TouchAction(driver)
        actions.long_press(source).move_to(target).release().perform()
        debug(f"Dragged element {source_uuid} to {target_uuid}")
        return {
            'status': 'success',
            'message': f'Successfully dragged element {source_uuid} to {target_uuid}'
        }
    except Exception as e:
        error(f"Failed to drag and drop: {e}")
        return {
            'status': 'error',
            'message': f'Failed to drag and drop. Error: {str(e)}'
        }


def appium_press_key(key_code: str, meta_state: Optional[int] = None) -> Dict[str, Any]:
    """Press a key."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        if meta_state:
            driver.press_keycode(int(key_code), metastate=meta_state)
        else:
            driver.press_keycode(int(key_code))
        debug(f"Pressed key: {key_code}")
        return {
            'status': 'success',
            'message': f'Successfully pressed key {key_code}'
        }
    except Exception as e:
        error(f"Failed to press key: {e}")
        return {
            'status': 'error',
            'message': f'Failed to press key {key_code}. Error: {str(e)}'
        }


def appium_set_value(element_uuid: str, text: str) -> Dict[str, Any]:
    """Set value on element."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        command.element_set_value(driver, element_uuid, text)
        return {
            'status': 'success',
            'message': f'Successfully set value on element {element_uuid}',
            'elementUUID': element_uuid,
            'text': text
        }
    except Exception as e:
        error(f"Failed to set value: {e}")
        return {
            'status': 'error',
            'message': f'Failed to set value on element {element_uuid}. Error: {str(e)}',
            'text': text
        }


def appium_get_text(element_uuid: str) -> Dict[str, Any]:
    """Get text from element."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        text = command.element_get_text(driver, element_uuid)
        return {
            'status': 'success',
            'text': text,
            'message': f'Successfully retrieved text from element {element_uuid}'
        }
    except Exception as e:
        error(f"Failed to get text: {e}")
        return {
            'status': 'error',
            'message': f'Failed to get text from element {element_uuid}. Error: {str(e)}'
        }


def appium_get_active_element() -> Dict[str, Any]:
    """Get active element."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        element_id = command.get_active_element(driver)
        return {
            'status': 'success',
            'element_id': element_id,
            'message': 'Successfully retrieved active element'
        }
    except Exception as e:
        error(f"Failed to get active element: {e}")
        return {
            'status': 'error',
            'message': f'Failed to get active element. Error: {str(e)}'
        }


def appium_get_page_source() -> Dict[str, Any]:
    """Get page source."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        source = command.get_page_source(driver)
        return {
            'status': 'success',
            'source': source,
            'message': 'Successfully retrieved page source'
        }
    except Exception as e:
        error(f"Failed to get page source: {e}")
        return {
            'status': 'error',
            'message': f'Failed to get page source. Error: {str(e)}'
        }


def appium_screenshot(filename: Optional[str] = None) -> Dict[str, Any]:
    """Take a screenshot."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        screenshot_b64 = command.get_screenshot(driver)
        return {
            'status': 'success',
            'screenshot': screenshot_b64,
            'filename': filename,
            'message': 'Screenshot captured successfully'
        }
    except Exception as e:
        error(f"Failed to take screenshot: {e}")
        return {
            'status': 'error',
            'message': f'Failed to take screenshot. Error: {str(e)}'
        }


def appium_element_screenshot(element_uuid: str) -> Dict[str, Any]:
    """Take a screenshot of specific element."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        element = driver.find_element(AppiumBy.ACCESSIBILITY_ID, element_uuid)
        screenshot_b64 = element.screenshot_as_base64
        debug(f"Element screenshot captured: {element_uuid}")
        return {
            'status': 'success',
            'screenshot': screenshot_b64,
            'element_uuid': element_uuid,
            'message': 'Element screenshot captured successfully'
        }
    except Exception as e:
        error(f"Failed to take element screenshot: {e}")
        return {
            'status': 'error',
            'message': f'Failed to take element screenshot. Error: {str(e)}'
        }


def appium_get_orientation() -> Dict[str, Any]:
    """Get device orientation."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        orientation = command.get_orientation(driver)
        return {
            'status': 'success',
            'orientation': orientation,
            'message': 'Successfully retrieved device orientation'
        }
    except Exception as e:
        error(f"Failed to get orientation: {e}")
        return {
            'status': 'error',
            'message': f'Failed to get orientation. Error: {str(e)}'
        }


def appium_set_orientation(orientation: str) -> Dict[str, Any]:
    """Set device orientation."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    if orientation.upper() not in ['PORTRAIT', 'LANDSCAPE']:
        raise ValueError(f"Invalid orientation: {orientation}")
    
    try:
        command.set_orientation(driver, orientation.upper())
        return {
            'status': 'success',
            'orientation': orientation,
            'message': f'Device orientation set to {orientation}'
        }
    except Exception as e:
        error(f"Failed to set orientation: {e}")
        return {
            'status': 'error',
            'message': f'Failed to set orientation. Error: {str(e)}'
        }


def appium_handle_alert(action: str) -> Dict[str, Any]:
    """Handle alert dialog."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    valid_actions = ['accept', 'dismiss', 'getText']
    if action not in valid_actions:
        raise ValueError(f"Invalid action: {action}. Must be one of {valid_actions}")
    
    try:
        text = command.handle_alert(driver, action)
        return {
            'status': 'success',
            'action': action,
            'text': text,
            'message': f'Alert {action}ed successfully'
        }
    except Exception as e:
        error(f"Failed to handle alert: {e}")
        return {
            'status': 'error',
            'message': f'Failed to handle alert. Error: {str(e)}'
        }
