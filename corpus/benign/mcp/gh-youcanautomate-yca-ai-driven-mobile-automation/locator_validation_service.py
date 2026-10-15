"""
LOCATOR VALIDATION SERVICE

Validates locators automatically during chatbot workflow.
Ensures only verified locators are added to page objects.

This is integrated into the chatbot pipeline for automatic validation.

Usage:
    from locator_validation_service import LocatorValidationService
    
    service = LocatorValidationService(appium_url, device_info)
    
    # Validate candidate locators
    validated = service.validate_locators({
        'email_field': (AppiumBy.XPATH, "//XCUIElementTypeTextField[1]"),
        'password_field': (AppiumBy.XPATH, "//XCUIElementTypeSecureTextField[1]"),
        'signin_btn': (AppiumBy.ACCESSIBILITY_ID, "Sign In"),
    })
    
    # Only verified locators returned
    for name, locator, status in validated['passed']:
        page_object.add_locator(name, locator)
"""
import time
import logging
from typing import Dict, List, Tuple, Optional
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException, TimeoutException

logger = logging.getLogger(__name__)


class LocatorValidationService:
    """Validates locators against the actual app."""
    
    def __init__(self, appium_url: str, device_info: Dict, platform: str = "ios"):
        """
        Initialize validation service.
        
        Args:
            appium_url: Appium server URL (e.g., 'http://localhost:4723')
            device_info: Device configuration dict with keys:
                - device_name, platform_version, bundle_id (iOS)
                - or device_name, platform_version, app_package, app_activity (Android)
            platform: 'ios' or 'android'
        """
        self.appium_url = appium_url
        self.device_info = device_info
        self.platform = platform.lower()
        self.driver = None
        self.validation_results = []
    
    def connect(self) -> bool:
        """Connect to Appium server and app."""
        try:
            if self.platform == "ios":
                options = XCUITestOptions()
                options.device_name = self.device_info.get('device_name')
                options.platform_version = self.device_info.get('platform_version')
                options.bundle_id = self.device_info.get('bundle_id')
                options.automation_name = "XCUITest"
            else:
                options = UiAutomator2Options()
                options.device_name = self.device_info.get('device_name')
                options.platform_version = self.device_info.get('platform_version')
                options.app_package = self.device_info.get('app_package')
                options.app_activity = self.device_info.get('app_activity')
                options.automation_name = "UiAutomator2"
            
            self.driver = webdriver.Remote(
                f"{self.appium_url}/wd/hub",
                options=options
            )
            time.sleep(1)  # Wait for app
            logger.info("✓ Connected to Appium and app")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to connect to app: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from app."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✓ Disconnected from app")
            except:
                pass
            self.driver = None
    
    def validate_single_locator(self, name: str, by: str, value: str, 
                                should_be_displayed: bool = True) -> Dict:
        """
        Validate a single locator.
        
        Returns:
            {
                'name': str,
                'locator': str,
                'by': str,
                'status': 'PASS' | 'FAIL' | 'WARN',
                'reason': str,
                'count': int
            }
        """
        result = {
            'name': name,
            'locator': value,
            'by': by,
            'status': None,
            'reason': None,
            'count': 0
        }
        
        if not self.driver:
            result['status'] = 'FAIL'
            result['reason'] = 'Driver not connected'
            return result
        
        try:
            elements = self.driver.find_elements(by, value)
            result['count'] = len(elements)
            
            if len(elements) == 0:
                result['status'] = 'FAIL'
                result['reason'] = 'Element not found'
            elif len(elements) == 1:
                elem = elements[0]
                if should_be_displayed:
                    if elem.is_displayed():
                        result['status'] = 'PASS'
                        result['reason'] = 'Found and displayed'
                    else:
                        result['status'] = 'FAIL'
                        result['reason'] = 'Found but not displayed'
                else:
                    result['status'] = 'PASS'
                    result['reason'] = 'Found'
            else:
                # Multiple elements - check if first is displayable
                elem = elements[0]
                if should_be_displayed and elem.is_displayed():
                    result['status'] = 'WARN'
                    result['reason'] = f'Multiple elements ({len(elements)}), using first'
                else:
                    result['status'] = 'FAIL'
                    result['reason'] = f'Multiple elements ({len(elements)})'
                    
        except Exception as e:
            result['status'] = 'FAIL'
            result['reason'] = f'Exception: {str(e)}'
        
        return result
    
    def validate_locators(self, locator_dict: Dict[str, Tuple[str, str]], 
                         should_be_displayed: bool = True) -> Dict:
        """
        Validate multiple locators from page object.
        
        Args:
            locator_dict: {
                'element_name': (AppiumBy.XPATH, 'locator_value'),
                'another_element': (AppiumBy.ACCESSIBILITY_ID, 'name'),
                ...
            }
            should_be_displayed: Whether elements must be visible
        
        Returns:
            {
                'passed': [(name, locator, by), ...],
                'warned': [(name, locator, by, reason), ...],
                'failed': [(name, locator, reason), ...],
                'total': int,
                'success_rate': float
            }
        """
        if not self.driver:
            logger.warning("Driver not connected, connecting now...")
            if not self.connect():
                return {
                    'passed': [],
                    'warned': [],
                    'failed': list(locator_dict.items()),
                    'total': len(locator_dict),
                    'success_rate': 0.0
                }
        
        passed = []
        warned = []
        failed = []
        
        logger.info(f"\nValidating {len(locator_dict)} locators...")
        
        for name, locator_tuple in locator_dict.items():
            if not isinstance(locator_tuple, tuple) or len(locator_tuple) != 2:
                failed.append((name, locator_tuple, "Invalid locator format"))
                continue
            
            by, value = locator_tuple
            result = self.validate_single_locator(name, by, value, should_be_displayed)
            
            if result['status'] == 'PASS':
                passed.append((name, value, by))
                logger.info(f"  ✓ {name}")
            elif result['status'] == 'WARN':
                warned.append((name, value, by, result['reason']))
                logger.warning(f"  ⚠ {name}: {result['reason']}")
            else:
                failed.append((name, value, result['reason']))
                logger.error(f"  ✗ {name}: {result['reason']}")
        
        total = len(locator_dict)
        success_count = len(passed) + len(warned)
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        logger.info(f"\n📊 Results: {len(passed)} passed, {len(warned)} warned, {len(failed)} failed")
        logger.info(f"✓ Success rate: {success_rate:.1f}%")
        
        return {
            'passed': passed,
            'warned': warned,
            'failed': failed,
            'total': total,
            'success_rate': success_rate
        }
    
    def validate_page_object_locators(self, page_object_class, 
                                      appium_by_module=AppiumBy) -> Dict:
        """
        Validate all locators in a page object class.
        
        Args:
            page_object_class: The page object class to validate
            appium_by_module: AppiumBy module (for testing)
        
        Returns:
            Validation result dict with passed/warned/failed locators
        """
        # Extract locator attributes from page object
        locator_dict = {}
        for attr_name in dir(page_object_class):
            if attr_name.endswith('_LOCATOR'):
                attr_value = getattr(page_object_class, attr_name)
                if isinstance(attr_value, tuple) and len(attr_value) == 2:
                    locator_dict[attr_name] = attr_value
        
        if not locator_dict:
            logger.warning(f"No locators found in {page_object_class.__name__}")
            return {'passed': [], 'warned': [], 'failed': [], 'total': 0, 'success_rate': 0}
        
        logger.info(f"Validating {page_object_class.__name__}: {len(locator_dict)} locators")
        return self.validate_locators(locator_dict)
    
    def get_verified_locators_dict(self, validation_result: Dict) -> Dict:
        """
        Extract only verified (passed + warned) locators from validation result.
        
        Returns dict ready to add to page object:
            {
                'element_name': (AppiumBy.XPATH, 'value'),
                ...
            }
        """
        locators = {}
        
        for name, value, by in validation_result.get('passed', []):
            # Convert string locator strategy to AppiumBy constant
            by_constant = self._string_to_appiumby(by)
            locators[f"{name}_LOCATOR"] = (by_constant, value)
        
        for name, value, by, reason in validation_result.get('warned', []):
            logger.warning(f"Including warned locator {name}: {reason}")
            by_constant = self._string_to_appiumby(by)
            locators[f"{name}_LOCATOR"] = (by_constant, value)
        
        return locators
    
    @staticmethod
    def _string_to_appiumby(by_string: str):
        """Convert string locator strategy to AppiumBy constant."""
        if isinstance(by_string, str):
            # Handle string names like "xpath", "accessibility id"
            by_lower = by_string.lower().replace(" ", "_")
            return getattr(AppiumBy, by_lower.upper(), AppiumBy.XPATH)
        return by_string


def validate_and_update_page_object(page_object_module, 
                                    appium_url: str,
                                    device_info: Dict,
                                    platform: str = "ios") -> Dict:
    """
    Convenience function: Validate page object and report results.
    
    Args:
        page_object_module: The page object class/module
        appium_url: Appium server URL
        device_info: Device configuration
        platform: Device platform
    
    Returns:
        Validation results
    """
    service = LocatorValidationService(appium_url, device_info, platform)
    
    try:
        if not service.connect():
            return {'error': 'Could not connect to app'}
        
        result = service.validate_page_object_locators(page_object_module)
        
        if result['passed']:
            logger.info(f"\n✓ {len(result['passed'])} verified locators ready to use")
        if result['failed']:
            logger.warning(f"\n✗ {len(result['failed'])} locators need review")
        
        return result
    finally:
        service.disconnect()
