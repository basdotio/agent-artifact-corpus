"""Test generation tools: generate_locators, generate_tests."""
from typing import Any, Dict, List
import session_store
import command
from logger import info, error


def appium_generate_locators(strategy: str = 'all') -> Dict[str, Any]:
    """Generate all locators for current page."""
    driver = session_store.get_driver()
    if not driver:
        raise ValueError("No active session")
    
    try:
        page_source = command.get_page_source(driver)
        
        # Parse page source to extract locators
        # This is a simplified implementation
        locators = {
            'xpath': [],
            'id': [],
            'accessibility_id': [],
            'css_selector': [],
            'class_name': [],
        }
        
        # Basic parsing - in reality would use proper XML parsing
        import re
        
        # Find XPath-like selectors
        xpath_pattern = r'resource-id="([^"]*)"'
        for match in re.finditer(xpath_pattern, page_source):
            locators['xpath'].append({
                'value': match.group(1),
                'type': 'resource-id'
            })
        
        info(f"Generated locators: {len(locators)}")
        return {
            'status': 'success',
            'locators': locators,
            'strategy': strategy,
            'message': 'Locators generated successfully'
        }
    except Exception as e:
        error(f"Failed to generate locators: {e}")
        return {
            'status': 'error',
            'message': f'Failed to generate locators. Error: {str(e)}'
        }


def appium_generate_tests(test_name: str, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate test script from recorded actions."""
    try:
        # Build test Python code from actions
        test_code = f'''"""
Generated test: {test_name}
This test was auto-generated from recorded actions.
"""
import unittest
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy

class Test{test_name.replace(" ", "")}(unittest.TestCase):
    def setUp(self):
        # Initialize driver with your capabilities
        pass
    
    def test_{test_name.replace(" ", "_").lower()}(self):
        """Test {test_name}"""
        driver = self.driver
        
        # Generated test steps:
'''
        
        # Add action steps
        for i, action in enumerate(actions):
            action_type = action.get('type', 'unknown')
            if action_type == 'click':
                test_code += f"        # Step {i+1}: Click element\n"
                test_code += f"        element = driver.find_element(AppiumBy.ACCESSIBILITY_ID, '{action.get('elementUUID', '')}')\n"
                test_code += f"        element.click()\n\n"
            elif action_type == 'setText':
                test_code += f"        # Step {i+1}: Set value\n"
                test_code += f"        element = driver.find_element(AppiumBy.ACCESSIBILITY_ID, '{action.get('elementUUID', '')}')\n"
                test_code += f"        element.send_keys('{action.get('value', '')}')\n\n"
            elif action_type == 'assertion':
                test_code += f"        # Step {i+1}: Assertion\n"
                test_code += f"        # {action.get('expectedValue', '')}\n\n"
        
        test_code += '''    def tearDown(self):
        if hasattr(self, 'driver'):
            self.driver.quit()

if __name__ == '__main__':
    unittest.main()
'''
        
        info(f"Test generated: {test_name}")
        return {
            'status': 'success',
            'test_name': test_name,
            'test_code': test_code,
            'action_count': len(actions),
            'message': f'Test script generated for {test_name}'
        }
    except Exception as e:
        error(f"Failed to generate test: {e}")
        return {
            'status': 'error',
            'message': f'Failed to generate test. Error: {str(e)}'
        }
