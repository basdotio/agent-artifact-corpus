"""
Enhanced test generator that uses Page Object Models.
Creates pytest tests using page objects for better maintainability.

Benefits:
- Cleaner test code
- Centralized locator management
- Reusable page methods
- Easier to maintain when UI changes
"""
import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from generate_page_objects import generate_page_objects, identify_pages_from_workflow
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def generate_test_with_page_objects(workflow_results: Dict[str, Any], 
                                   test_filename: str,
                                   output_dir: str = 'generated_tests') -> Dict[str, Any]:
    """
    Generate pytest test that uses Page Objects instead of raw locators.
    
    Test methods will look like:
        login_page.enter_email('user@test.com')
        login_page.click_signin_button()
    
    Instead of:
        element = driver.find_element(XPATH, '//TextField[@name="Email"]')
        element.send_keys('user@test.com')
    """
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract pages from workflow
        pages = identify_pages_from_workflow(workflow_results)
        
        # Get platform info
        platform = determine_platform(workflow_results)
        
        # Generate imports
        code_lines = [
            f'"""',
            f'Pytest test auto-generated from workflow execution.',
            f'Uses Page Object Model (POM) for clean, maintainable test code.',
            f'"""',
            f'import pytest',
            f'from appium import webdriver',
            f'from appium.webdriver.common.appiumby import AppiumBy',
        ]
        
        if platform.lower() == 'ios':
            code_lines.append('from appium.options.ios import XCUITestOptions')
        else:
            code_lines.append('from appium.options.android import UiAutomator2Options')
        
        # Import page objects
        code_lines.append('')
        code_lines.append('# Import Page Objects')
        for page_name in pages.keys():
            class_name = ''.join(word.capitalize() for word in page_name.split('_'))
            code_lines.append(f'from page_objects.{page_name} import {class_name}')
        
        # Add fixture
        code_lines.extend([
            '',
            '',
            '@pytest.fixture',
            'def driver():',
            '    """Initialize Appium driver with capabilities."""',
        ])
        
        if platform.lower() == 'ios':
            code_lines.extend([
                '    options = XCUITestOptions()',
                '    options.device_name = "iPhone Simulator"',
                '    options.bundle_id = "com.example.app"',
                '    options.use_simulator = True',
            ])
        else:
            code_lines.extend([
                '    options = UiAutomator2Options()',
                '    options.device_name = "emulator-5554"',
                '    options.app = "/path/to/app.apk"',
            ])
        
        code_lines.extend([
            '    ',
            '    driver_instance = webdriver.Remote(',
            '        "http://localhost:4723",',
            '        options=options',
            '    )',
            '    yield driver_instance',
            '    driver_instance.quit()',
            '',
            '',
        ])
        
        # Add test function header
        test_name = Path(test_filename).stem
        code_lines.extend([
            f'def test_{test_name}(driver):',
            f'    """Test {test_name} workflow."""',
        ])
        
        # Add page object instantiation
        for page_name in pages.keys():
            class_name = ''.join(word.capitalize() for word in page_name.split('_'))
            code_lines.append(f'    {page_name} = {class_name}(driver)')
        
        code_lines.append('')
        
        # Extract actions and convert to page object calls
        results = workflow_results.get('results', [])
        action_count = 0
        last_found_element = None  # Track last found element for subsequent actions
        
        for step_idx, step_result in enumerate(results, 1):
            actions_executed = step_result.get('actions_executed', [])
            current_page = infer_page_from_step(step_idx)
            
            for action in actions_executed:
                tool = action.get('tool', '')
                action_result = action.get('result', {})
                
                if action_result.get('status') == 'success':
                    if tool == 'appium_screenshot':
                        code_lines.append(f'    # Step {step_idx}: Take screenshot')
                        code_lines.append(f'    driver.save_screenshot("screenshot_step_{step_idx}.png")')
                        code_lines.append('')
                        action_count += 1
                    
                    elif tool == 'appium_find_element':
                        selector = action_result.get('selector', '')
                        element_name = extract_element_name(selector)
                        last_found_element = element_name
                        code_lines.append(f'    # Step {step_idx}: Find {element_name}')
                    
                    elif tool == 'appium_set_value':
                        text = action_result.get('text', '')
                        if last_found_element:
                            method_name = f'enter_{last_found_element}'
                            code_lines.append(f'    # Step {step_idx}: Enter text in {last_found_element}')
                            code_lines.append(f'    {current_page}.{method_name}("{text}")')
                            code_lines.append('')
                            action_count += 1
                        else:
                            # Fallback: create generic enter_text method call
                            code_lines.append(f'    # Step {step_idx}: Enter text (element: unknown)')
                            code_lines.append(f'    # TODO: Update with correct element-specific method')
                            code_lines.append('')
                    
                    elif tool == 'appium_click':
                        if last_found_element:
                            method_name = f'click_{last_found_element}'
                            code_lines.append(f'    # Step {step_idx}: Click {last_found_element}')
                            code_lines.append(f'    {current_page}.{method_name}()')
                            code_lines.append('')
                            action_count += 1
                        else:
                            # Fallback: create generic click method call
                            code_lines.append(f'    # Step {step_idx}: Click element (not found)')
                            code_lines.append(f'    # TODO: Update with correct element-specific method')
                            code_lines.append('')
                            last_found_element = None  # Reset after use
        
        # Add final assertion
        code_lines.extend([
            '',
            '    # Verify workflow completion',
            '    assert driver.current_activity is not None',
        ])
        
        # Write test file
        filepath = os.path.join(output_dir, test_filename)
        with open(filepath, 'w') as f:
            f.write('\n'.join(code_lines))
        
        return {
            'status': 'success',
            'filepath': filepath,
            'filename': test_filename,
            'lines': len(code_lines),
            'actions': action_count,
            'pages_used': len(pages),
            'platform': platform
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to generate test with page objects: {str(e)}'
        }


def determine_platform(workflow_results: Dict[str, Any]) -> str:
    """Determine iOS or Android platform from workflow."""
    results = workflow_results.get('results', [])
    for step in results:
        actions = step.get('actions_executed', [])
        for action in actions:
            result = action.get('result', {})
            if 'XCUI' in str(result) or 'XCUIElementType' in str(result):
                return 'iOS'
    return 'iOS'  # Default


def infer_page_from_step(step_num: int) -> str:
    """Infer page object name from step number."""
    mapping = {
        1: 'home_page',
        2: 'home_page',
        3: 'login_page',
        4: 'login_page',
        5: 'login_page',
        6: 'login_page',
        7: 'login_page',
        8: 'home_page',
        9: 'home_page',
        10: 'product_page',
        11: 'product_details_page',
        12: 'product_details_page',
        13: 'cart_page',
    }
    return mapping.get(step_num, 'home_page')


def extract_element_name(selector: str) -> str:
    """Extract meaningful element name from selector."""
    if 'Email' in selector:
        return 'email_field'
    elif 'Password' in selector:
        return 'password_field'
    elif 'Sign In' in selector or 'Login' in selector:
        return 'signin_button'
    elif 'Add to Cart' in selector:
        return 'add_to_cart_button'
    elif 'Crew Neck' in selector:
        return 'crew_neck_product'
    elif 'Product' in selector or 'product' in selector:
        return 'product'
    elif 'Cart' in selector:
        return 'cart_button'
    elif 'Checkout' in selector:
        return 'checkout_button'
    elif 'Continue' in selector:
        return 'continue_button'
    else:
        # Fallback: try to extract a meaningful name from selector
        import re
        # Look for text patterns in selectors
        text_match = re.search(r"['\"]([^'\"]+)['\"]", selector)
        if text_match:
            text = text_match.group(1)
            # Convert to snake_case
            name = re.sub(r'[^a-zA-Z0-9]+', '_', text).lower().strip('_')
            return name if name else 'found_element'
        return 'found_element'


def main():
    """Demo test generation with page objects."""
    print("This module integrates with the main test generation pipeline.")
    print("Call generate_test_with_page_objects() from run_yaml.py")


if __name__ == '__main__':
    main()
