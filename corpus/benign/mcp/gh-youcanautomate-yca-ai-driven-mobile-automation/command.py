"""Command execution module for Appium operations."""
import base64
from typing import Any, Dict, List, Optional
from appium.webdriver.common.appiumby import AppiumBy
import session_store
from logger import info, error, debug


def element_click(driver: Any, element_uuid: str) -> None:
    """Click on an element by UUID."""
    import session_store
    # Get the element from cache
    element = session_store.get_cached_element(element_uuid)
    if not element:
        raise ValueError(f"Element {element_uuid} not found in cache. Make sure to find_element first.")
    element.click()
    debug(f"Clicked element: {element_uuid}")


def element_set_value(driver: Any, element_uuid: str, value: str) -> None:
    """Set value on element by UUID."""
    import session_store
    # Get the element from cache
    element = session_store.get_cached_element(element_uuid)
    if not element:
        raise ValueError(f"Element {element_uuid} not found in cache. Make sure to find_element first.")
    element.send_keys(value)
    debug(f"Set value on element: {element_uuid}")


def element_get_text(driver: Any, element_uuid: str) -> str:
    """Get text from element by UUID."""
    import session_store
    # Get the element from cache
    element = session_store.get_cached_element(element_uuid)
    if not element:
        raise ValueError(f"Element {element_uuid} not found in cache. Make sure to find_element first.")
    text = element.text
    debug(f"Got text from element {element_uuid}: {text}")
    return text


def get_screenshot(driver: Any) -> str:
    """Get screenshot as base64 string."""
    screenshot_bytes = driver.get_screenshot_as_png()
    screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
    debug("Screenshot captured")
    return screenshot_b64


def get_page_source(driver: Any) -> str:
    """Get page source."""
    source = driver.page_source
    debug(f"Page source retrieved, length: {len(source)}")
    return source


def get_active_element(driver: Any) -> Optional[str]:
    """Get the currently active/focused element."""
    try:
        element = driver.switch_to.active_element
        element_id = element.id
        debug(f"Active element: {element_id}")
        return element_id
    except Exception as e:
        error(f"Failed to get active element: {e}")
        return None


def find_elements_by_strategy(
    driver: Any,
    strategy: str,
    selector: str
) -> List[Dict[str, Any]]:
    """Find elements by strategy and selector."""
    strategy_map = {
        'xpath': AppiumBy.XPATH,
        'id': AppiumBy.ID,
        'name': AppiumBy.NAME,
        'class name': AppiumBy.CLASS_NAME,
        'accessibility id': AppiumBy.ACCESSIBILITY_ID,
        'css selector': AppiumBy.CSS_SELECTOR,
        '-android uiautomator': AppiumBy.ANDROID_UIAUTOMATOR,
        '-ios predicate string': AppiumBy.IOS_PREDICATE,
        '-ios class chain': AppiumBy.IOS_CLASS_CHAIN,
    }
    
    if strategy not in strategy_map:
        raise ValueError(f"Unknown strategy: {strategy}")
    
    appium_strategy = strategy_map[strategy]
    elements = driver.find_elements(appium_strategy, selector)
    
    results = []
    for element in elements:
        element_uuid = element.id
        # Cache the element for later use
        import session_store
        session_store.cache_element(element_uuid, element)
        results.append({
            'element-6066-11e4-a52e-4f735466cecf': element_uuid,
            'text': element.text,
            'tag_name': element.tag_name,
        })
    
    debug(f"Found {len(elements)} elements with strategy {strategy} and selector {selector}")
    return results


def get_orientation(driver: Any) -> str:
    """Get device orientation."""
    orientation = driver.orientation
    debug(f"Current orientation: {orientation}")
    return orientation


def set_orientation(driver: Any, orientation: str) -> None:
    """Set device orientation."""
    driver.orientation = orientation
    debug(f"Orientation set to: {orientation}")


def handle_alert(driver: Any, action: str) -> Optional[str]:
    """Handle alert dialog."""
    try:
        alert = driver.switch_to.alert
        if action == "accept":
            text = alert.text
            alert.accept()
            info(f"Alert accepted: {text}")
            return text
        elif action == "dismiss":
            text = alert.text
            alert.dismiss()
            info(f"Alert dismissed: {text}")
            return text
        elif action == "getText":
            text = alert.text
            info(f"Alert text: {text}")
            return text
        else:
            raise ValueError(f"Unknown alert action: {action}")
    except Exception as e:
        error(f"Failed to handle alert: {e}")
        raise
