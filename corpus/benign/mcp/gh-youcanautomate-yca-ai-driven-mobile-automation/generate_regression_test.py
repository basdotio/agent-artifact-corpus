"""
Generate deterministic regression test from captured workflow execution.
Uses real locators (strategy + selector) from successful actions.
Does NOT depend on Bedrock - purely automated interaction replay.

Generated tests use PYTEST framework:
- Modern, fast, powerful testing framework
- Fixture-based setup/teardown with @pytest.fixture
- Simple assert statements
- Excellent reporting and output
- Great for CI/CD pipelines
"""
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from pathlib import Path

# Get logger
logger = logging.getLogger(__name__)

console = Console()


def extract_action_flow(workflow_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract action flow from workflow execution results.
    Maps find_element actions to subsequent click/set_value actions.
    Also captures orphaned clicks/set_values that don't have preceding find_element.
    
    Returns list of executable actions with real locators, combining find + interaction:
    [
        {
            'action': 'click',
            'strategy': 'XPATH',
            'selector': '//Button[@name="Login"]',
            'step_description': 'Click login button'
        },
        {
            'action': 'set_value',
            'strategy': 'ACCESSIBILITY_ID',
            'selector': 'email_field',
            'text': 'user@example.com',
            'step_description': 'Enter email address'
        }
    ]
    """
    action_flow = []
    
    results = workflow_results.get('results', [])
    
    for step_idx, step_result in enumerate(results, 1):
        actions_executed = step_result.get('actions_executed', [])
        
        # Track the last found element for click/set_value mapping
        last_found_element = None
        
        for action_idx, action in enumerate(actions_executed):
            tool = action.get('tool', '')
            params = action.get('params', {})
            action_result = action.get('result', {})
            reasoning = action.get('reasoning', '')
            status = action_result.get('status', 'unknown')
            
            if status == 'success':
                # Capture find_element - store reference but DON'T add to action_flow yet
                if tool == 'appium_find_element':
                    strategy = action_result.get('strategy', params.get('strategy'))
                    selector = action_result.get('selector', params.get('selector'))
                    last_found_element = {
                        'strategy': strategy,
                        'selector': selector,
                        'uuid': action_result.get('elementUUID'),
                        'step_idx': step_idx
                    }
                
                # Capture click using last found element's real locator
                # Also capture orphaned clicks (without preceding find_element)
                elif tool == 'appium_click':
                    if last_found_element:
                        # Use the located element
                        action_flow.append({
                            'action': 'click',
                            'strategy': last_found_element['strategy'],
                            'selector': last_found_element['selector'],
                            'step_description': f'Step {last_found_element["step_idx"]}: Click element'
                        })
                        last_found_element = None
                    else:
                        # Orphaned click - try to extract selector from action_result
                        strategy = action_result.get('strategy', params.get('strategy'))
                        selector = action_result.get('selector', params.get('selector'))
                        if strategy and selector:
                            action_flow.append({
                                'action': 'click',
                                'strategy': strategy,
                                'selector': selector,
                                'step_description': f'Step {step_idx}: Click element'
                            })
                
                # Capture set_value using last found element's real locator
                # Also capture orphaned set_values (without preceding find_element)
                elif tool == 'appium_set_value':
                    text = action_result.get('text', params.get('text', ''))
                    if last_found_element:
                        # Use the located element
                        action_flow.append({
                            'action': 'set_value',
                            'strategy': last_found_element['strategy'],
                            'selector': last_found_element['selector'],
                            'text': text,
                            'step_description': f'Step {last_found_element["step_idx"]}: Enter text'
                        })
                        last_found_element = None
                    else:
                        # Orphaned set_value - try to extract selector from action_result
                        strategy = action_result.get('strategy', params.get('strategy'))
                        selector = action_result.get('selector', params.get('selector'))
                        if strategy and selector:
                            action_flow.append({
                                'action': 'set_value',
                                'strategy': strategy,
                                'selector': selector,
                                'text': text,
                                'step_description': f'Step {step_idx}: Enter text'
                            })
                    last_found_element = None
    
    return action_flow


def generate_test_code(
    test_name: str,
    action_flow: List[Dict[str, Any]],
    platform: str = 'ios',
    device_info: Optional[Dict[str, Any]] = None
) -> str:
    """Generate pytest regression test code from action flow."""
    
    if not device_info:
        device_info = {}
    
    code_lines = [
        '"""',
        f'Regression test: {test_name}',
        'Auto-generated from captured workflow execution.',
        'Uses real locators (XPATH, ACCESSIBILITY_ID, etc.) found during interactive session.',
        'Does NOT depend on AI/Bedrock - purely deterministic automation replay.',
        '',
        'Run with: pytest test_<name>.py -v',
        '"""',
        'import pytest',
        'from appium import webdriver',
        'from appium.webdriver.common.appiumby import AppiumBy',
        'from appium.options.ios import XCUITestOptions',
        'from appium.options.android import UiAutomator2Options',
        '',
        '',
        '@pytest.fixture',
        'def driver():',
        '    """Initialize Appium driver with capabilities."""',
    ]
    
    # Add platform-specific options - use device info from workflow
    if platform == 'ios':
        device_name = device_info.get("device_name") or os.getenv("IOS_DEVICE_NAME", "iPhone 14")
        bundle_id = device_info.get("bundle_id") or os.getenv("IOS_BUNDLE_ID", "com.example.app")
        platform_version = device_info.get("platform_version") or os.getenv("IOS_PLATFORM_VERSION", "17.0")
        
        code_lines.extend([
            '    options = XCUITestOptions()',
            f'    options.device_name = "{device_name}"',
            f'    options.platform_version = "{platform_version}"',
            f'    options.bundle_id = "{bundle_id}"',
            '    options.automation_name = "XCUITest"',
            '    ',
            '    driver_instance = webdriver.Remote(',
            '        "http://localhost:4723/wd/hub",',
            '        options=options',
            '    )',
        ])
    else:  # android
        device_name = device_info.get("device_name") or os.getenv("ANDROID_DEVICE_NAME", "emulator-5554")
        app_package = device_info.get("app_package") or os.getenv("ANDROID_APP_PACKAGE", "com.example.app")
        app_activity = device_info.get("app_activity") or os.getenv("ANDROID_APP_ACTIVITY", ".MainActivity")
        platform_version = device_info.get("platform_version") or os.getenv("ANDROID_PLATFORM_VERSION", "13.0")
        
        code_lines.extend([
            '    options = UiAutomator2Options()',
            f'    options.device_name = "{device_name}"',
            f'    options.app_package = "{app_package}"',
            f'    options.app_activity = "{app_activity}"',
            f'    options.platform_version = "{platform_version}"',
            '    ',
            '    driver_instance = webdriver.Remote(',
            '        "http://localhost:4723/wd/hub",',
            '        options=options',
            '    )',
        ])
    
    code_lines.extend([
        '    yield driver_instance',
        '    driver_instance.quit()',
        '',
        '',
        f'def test_{test_name}(driver):',
        f'    """Test {test_name} workflow."""',
        '',
    ])
    
    # Generate action steps
    step_num = 1
    for action in action_flow:
        action_type = action.get('action')
        description = action.get('step_description', f'Step {step_num}')
        
        code_lines.append(f'    # {description}')
        
        if action_type == 'find_element':
            strategy = action['strategy']
            selector = action['selector'].replace('"', '\\"')  # Escape quotes
            appium_by_value = strategy_to_appiumby(strategy)
            code_lines.append(f'    element = driver.find_element(AppiumBy.{appium_by_value}, "{selector}")')
            code_lines.append('    assert element is not None')
        
        elif action_type == 'click':
            strategy = action['strategy']
            selector = action['selector'].replace('"', '\\"')  # Escape quotes
            appium_by_value = strategy_to_appiumby(strategy)
            code_lines.append(f'    element = driver.find_element(AppiumBy.{appium_by_value}, "{selector}")')
            code_lines.append('    element.click()')
        
        elif action_type == 'set_value':
            strategy = action['strategy']
            selector = action['selector'].replace('"', '\\"')  # Escape quotes
            text = action.get('text', '').replace('"', '\\"')  # Escape quotes
            appium_by_value = strategy_to_appiumby(strategy)
            code_lines.append(f'    element = driver.find_element(AppiumBy.{appium_by_value}, "{selector}")')
            code_lines.append(f'    element.send_keys("{text}")')
        

        code_lines.append('')
        step_num += 1
    
    return '\n'.join(code_lines)


def extract_selector_keywords(selector: str) -> List[str]:
    """Extract meaningful keywords from XPATH/locator selector.
    
    Examples:
    - "//XCUIElementTypeTextField[@value='Email']" -> ['Email', 'email']
    - "//Button[@name='Sign In']" -> ['Sign In', 'Sign', 'In', 'sign', 'in']
    - "type == 'XCUIElementTypeSecureTextField'" -> ['password', 'field']
    - "label CONTAINS 'Crew Neck'" -> ['Crew Neck', 'crew', 'neck']
    - "Accessibility ID: Add to Cart" -> ['add', 'to', 'cart', 'add_to_cart', 'addtocart']
    """
    import re
    keywords = []
    
    # Extract XPath attributes like @value='Email', @name='Sign In'
    attr_pattern = r"@\w+=['\"]([^'\"]+)['\"]"
    matches = re.findall(attr_pattern, selector)
    for match in matches:
        keywords.append(match)
        keywords.append(match.lower())
        words = match.lower().split()
        keywords.extend(words)
        # Add underscore version for multi-word attributes
        if ' ' in match:
            keywords.append(match.lower().replace(' ', '_'))
    
    # Extract iOS predicate patterns: type == 'XCUIElementTypeXXX'
    type_pattern = r"type\s*==\s*['\"]([^'\"]+)['\"]"
    type_matches = re.findall(type_pattern, selector)
    for type_match in type_matches:
        # Extract semantic info: XCUIElementTypeSecureTextField -> password, field
        type_lower = type_match.lower()
        if 'securetextfield' in type_lower:
            keywords.extend(['password', 'secure', 'field', 'secure_text_field'])
        elif 'textfield' in type_lower:
            keywords.extend(['text', 'input', 'field', 'text_field', 'email'])
        elif 'button' in type_lower:
            keywords.extend(['button', 'sign_in', 'signin', 'sign'])
        elif 'statictext' in type_lower:
            keywords.extend(['text', 'label', 'static'])
    
    # Extract iOS predicate text patterns: label CONTAINS[c] 'Email', name CONTAINS 'SignIn'
    # [c] is optional case-insensitive flag
    text_pattern = r"(?:label|name|placeholder)\s+(?:CONTAINS(?:\[[^\]]*\])?|==)\s*['\"]([^'\"]+)['\"]"
    text_matches = re.findall(text_pattern, selector, re.IGNORECASE)
    for text_match in text_matches:
        keywords.append(text_match)
        keywords.append(text_match.lower())
        words = text_match.lower().split()
        keywords.extend(words)
        # Add underscore version for multi-word text
        if ' ' in text_match:
            keywords.append(text_match.lower().replace(' ', '_'))
    
    # Special handling for common accessibility ID patterns
    # "Add to Cart" -> ["add", "cart", "add_to_cart", "addtocart"]
    acessibility_id_pattern = r"accessibility\s+id\s*:?\s*['\"]?([^'\"]*)['\"]?"
    acc_matches = re.findall(acessibility_id_pattern, selector, re.IGNORECASE)
    for acc_match in acc_matches:
        if acc_match.strip():
            keywords.append(acc_match)
            keywords.append(acc_match.lower())
            words = acc_match.lower().split()
            keywords.extend(words)
            if ' ' in acc_match:
                keywords.append(acc_match.lower().replace(' ', '_'))
    
    # Remove duplicates and empty strings, preserve order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        kw_lower = kw.lower().strip()
        if kw_lower and kw_lower not in seen:
            seen.add(kw_lower)
            unique_keywords.append(kw_lower)
    
    return unique_keywords


def match_selector_to_element(selector: str, element_names: List[str]) -> Optional[str]:
    """
    Match a selector to an element name from available page objects.
    Uses multi-strategy scoring with improved matching.
    
    Args:
        selector: The locator selector (XPath or iOS predicate)
        element_names: List of available element names
    
    Returns:
        Best matching element name or None if no match found
    """
    keywords = extract_selector_keywords(selector)
    
    if not keywords or not element_names:
        return None
    
    scored_matches = {}
    
    for element_name in element_names:
        element_lower = element_name.lower()
        element_normalized = element_lower.replace('_', ' ')
        score = 0
        matches_found = 0
        
        for keyword in keywords:
            keyword_lower = keyword.lower().strip()
            
            if not keyword_lower:
                continue
            
            # Strategy 1: Exact element name match (weight: 20)
            if keyword_lower == element_lower or keyword_lower == element_normalized:
                score += 20
                matches_found += 1
            
            # Strategy 2: Exact element name match with underscores (weight: 18)
            elif keyword_lower.replace(' ', '_') == element_lower:
                score += 18
                matches_found += 1
            
            # Strategy 3: Multi-word phrase match (weight: 12)
            elif ' ' in keyword_lower and len(keyword_lower) > 3:
                if keyword_lower in element_normalized or keyword_lower.replace(' ', '_') in element_lower:
                    score += 12
                    matches_found += 1
            
            # Strategy 4: Element name contains keyword as complete word (weight: 10)
            elif keyword_lower in element_lower.split('_'):
                score += 10
                matches_found += 1
            
            # Strategy 5: Keyword fully contained in element name (weight: 7)
            elif len(keyword_lower) > 1 and keyword_lower in element_normalized:
                score += 7
                matches_found += 1
            
            # Strategy 6: Substring match with minimum length 3 (weight: 4)
            elif len(keyword_lower) > 2 and keyword_lower in element_lower:
                score += 4
                matches_found += 1
            
            # Strategy 7: Element word in keyword (for abbreviated keywords)
            elif len(keyword_lower) < 6:
                for element_word in element_lower.split('_'):
                    if len(element_word) > 2 and element_word in keyword_lower:
                        score += 3
                        matches_found += 1
                        break
        
        # Boost score if multiple keywords matched
        if matches_found > 1:
            score += (matches_found - 1) * 3
        
        if score > 0:
            scored_matches[element_name] = score
    
    if scored_matches:
        best_match = max(scored_matches.items(), key=lambda x: x[1])
        # Lowered minimum threshold to catch more matches (>= 3)
        if best_match[1] >= 3:
            return best_match[0]
    
    return None


def generate_test_code_with_page_objects(
    test_name: str,
    page_object_files: List[Dict[str, Any]],
    action_flow: List[Dict[str, Any]] = None,
    platform: str = 'ios',
    device_info: Optional[Dict[str, Any]] = None
) -> str:
    """Generate pytest regression test code using page objects with actual test steps."""
    
    if not device_info:
        device_info = {}
    
    if not action_flow:
        action_flow = []
    
    # Get page object imports and create name mapping
    page_imports = []
    page_instances = []
    page_methods = {}  # Map: element selector -> (page_name, method_name)
    
    if page_object_files:
        for pom_file in page_object_files:
            page_name = pom_file['page_name']
            class_name = ''.join(word.capitalize() for word in page_name.split('_'))
            page_imports.append(f'from page_objects.{page_name} import {class_name}')
            page_instances.append((page_name, class_name))
            
            # Build method mapping for elements
            for elem_name in pom_file.get('element_names', []):
                # Method names will be like: click_email_field, enter_password_field, etc.
                page_methods[elem_name] = (page_name, elem_name)
    
    code_lines = [
        '"""',
        f'Regression test: {test_name}',
        'Auto-generated from captured workflow execution.',
        'Uses Page Object Model for clean, maintainable test code.',
        '',
        'Pages:',
    ]
    
    for _, class_name in page_instances:
        code_lines.append(f'  - {class_name}')
    
    code_lines.extend([
        '',
        'Run with: pytest test_<name>.py -v',
        '"""',
        'import pytest',
        'from appium import webdriver',
        'from appium.webdriver.common.appiumby import AppiumBy',
        'from appium.options.ios import XCUITestOptions',
        'from appium.options.android import UiAutomator2Options',
        '',
        '# Import Page Objects',
    ])
    
    code_lines.extend(page_imports)
    
    code_lines.extend([
        '',
        '',
        '@pytest.fixture',
        'def driver():',
        '    """Initialize Appium driver with capabilities."""',
    ])
    
    # Add platform-specific options - use device info from workflow
    if platform == 'ios':
        device_name = device_info.get("device_name") or os.getenv("IOS_DEVICE_NAME", "iPhone 14")
        bundle_id = device_info.get("bundle_id") or os.getenv("IOS_BUNDLE_ID", "com.example.app")
        platform_version = device_info.get("platform_version") or os.getenv("IOS_PLATFORM_VERSION", "17.0")
        
        code_lines.extend([
            '    options = XCUITestOptions()',
            f'    options.device_name = "{device_name}"',
            f'    options.platform_version = "{platform_version}"',
            f'    options.bundle_id = "{bundle_id}"',
            '    options.automation_name = "XCUITest"',
            '    ',
            '    driver_instance = webdriver.Remote(',
            '        "http://localhost:4723/wd/hub",',
            '        options=options',
            '    )',
        ])
    else:  # android
        device_name = device_info.get("device_name") or os.getenv("ANDROID_DEVICE_NAME", "emulator-5554")
        app_package = device_info.get("app_package") or os.getenv("ANDROID_APP_PACKAGE", "com.example.app")
        app_activity = device_info.get("app_activity") or os.getenv("ANDROID_APP_ACTIVITY", ".MainActivity")
        platform_version = device_info.get("platform_version") or os.getenv("ANDROID_PLATFORM_VERSION", "13.0")
        
        code_lines.extend([
            '    options = UiAutomator2Options()',
            f'    options.device_name = "{device_name}"',
            f'    options.app_package = "{app_package}"',
            f'    options.app_activity = "{app_activity}"',
            f'    options.platform_version = "{platform_version}"',
            '    ',
            '    driver_instance = webdriver.Remote(',
            '        "http://localhost:4723/wd/hub",',
            '        options=options',
            '    )',
        ])
    
    code_lines.extend([
        '    yield driver_instance',
        '    driver_instance.quit()',
        '',
        '',
        f'def test_{test_name}(driver):',
        f'    """Test {test_name} workflow."""',
    ])
    
    # Initialize page objects
    for page_name, class_name in page_instances:
        code_lines.append(f'    {page_name} = {class_name}(driver)')
    
    code_lines.append('')
    
    # Generate test steps from action flow (or template if empty)
    if action_flow:
        code_lines.append('    # Test Steps (from captured workflow)')
        
        step_num = 1
        for idx, action in enumerate(action_flow):
            action_type = action.get('action')
            description = action.get('step_description', f'Step {step_num}')
            
            if action_type in ['find_element', 'click', 'set_value']:
                # Try to find best matching page object method
                selector = action.get('selector', '')
                strategy = action.get('strategy', '')
                text = action.get('text', '')
                
                # Try to match selector to element name using intelligent keyword extraction
                matched_page = None
                matched_method = None
                
                # Get all element names from page_methods
                elem_names = list(page_methods.keys())
                
                # Use smart matching to find best element
                matched_elem_name = match_selector_to_element(selector, elem_names)
                
                if matched_elem_name and matched_elem_name in page_methods:
                    matched_page, _ = page_methods[matched_elem_name]
                    
                    if action_type == 'click' or action_type == 'find_element':
                        matched_method = f'click_{matched_elem_name}'
                    elif action_type == 'set_value':
                        matched_method = f'enter_{matched_elem_name}'
                
                # Generate code
                if matched_page and matched_method:
                    code_lines.append(f'    # {description}')
                    if action_type == 'set_value':
                        text_escaped = text.replace('"', '\\"')
                        code_lines.append(f'    {matched_page}.{matched_method}("{text_escaped}")')
                    elif action_type in ['find_element', 'click']:
                        code_lines.append(f'    {matched_page}.{matched_method}()')
                    current_page = matched_page
                else:
                    # Fallback: Generate raw Appium code for unmatched elements
                    # This ensures all actions are captured, even if not mapped to page objects
                    appium_by_value = strategy_to_appiumby(strategy)
                    selector_escaped = selector.replace('"', '\\"')
                    
                    if action_type == 'find_element':
                        # Only output find if followed by click/set_value
                        is_click_next = (idx + 1 < len(action_flow) and 
                                        action_flow[idx + 1].get('action') == 'click')
                        is_set_next = (idx + 1 < len(action_flow) and 
                                      action_flow[idx + 1].get('action') == 'set_value')
                        if not (is_click_next or is_set_next):
                            # Standalone find - generate code
                            code_lines.append(f'    # {description}')
                            code_lines.append(f'    element = driver.find_element(AppiumBy.{appium_by_value}, "{selector_escaped}")')
                    
                    elif action_type == 'click':
                        prev_was_find = (idx > 0 and action_flow[idx - 1].get('action') == 'find_element')
                        if not prev_was_find:
                            # Orphaned click - generate code
                            code_lines.append(f'    # {description}')
                            code_lines.append(f'    element = driver.find_element(AppiumBy.{appium_by_value}, "{selector_escaped}")')
                            code_lines.append('    element.click()')
                        else:
                            # Click following find - just do click on element from previous find
                            code_lines.append(f'    # {description}')
                            code_lines.append('    element.click()')
                    
                    elif action_type == 'set_value':
                        prev_was_find = (idx > 0 and action_flow[idx - 1].get('action') == 'find_element')
                        text_escaped = text.replace('"', '\\"')
                        if not prev_was_find:
                            # Orphaned set_value - generate code
                            code_lines.append(f'    # {description}')
                            code_lines.append(f'    element = driver.find_element(AppiumBy.{appium_by_value}, "{selector_escaped}")')
                            code_lines.append(f'    element.send_keys("{text_escaped}")')
                        else:
                            # Set_value following find - use element from find
                            code_lines.append(f'    # {description}')
                            code_lines.append(f'    element.send_keys("{text_escaped}")')

            
            code_lines.append('')
            step_num += 1
        
        # Add verification
        if page_instances:
            code_lines.extend([
                '    # Verify workflow completion',
                f'    assert {page_instances[-1][0]}.is_displayed()',
            ])
    else:
        # No action flow - generate template test using available page objects
        code_lines.extend([
            '    # Template test steps (generated from page objects)',
            '    # Workflow was not executed; modify these tests to match your actual workflow'
        ])
        
        if page_instances:
            code_lines.append('    ')
            step_num = 1
            # Generate example calls for each page object's methods
            for page_name, class_name in page_instances:
                code_lines.append(f'    # Example interactions with {class_name}')
                
                # Get the page object file to see what methods are available
                for pom_file in page_object_files:
                    if pom_file['page_name'] == page_name:
                        elem_names = pom_file.get('element_names', [])
                        for elem_name in elem_names[:2]:  # Show first 2 elements as examples
                            code_lines.append(f'    # {page_name}.click_{elem_name}()  # Example step {step_num}')
                            step_num += 1
                code_lines.append('    ')
        else:
            code_lines.append('    # No page objects available - define test steps manually')
    
    return '\n'.join(code_lines)


def strategy_to_appiumby(strategy: str) -> str:
    """Convert strategy string to AppiumBy constant."""
    mapping = {
        'XPATH': 'XPATH',
        'ACCESSIBILITY_ID': 'ACCESSIBILITY_ID',
        'CLASS_NAME': 'CLASS_NAME',
        'ID': 'ID',
        'NAME': 'NAME',
        'PARTIAL_LINK_TEXT': 'PARTIAL_LINK_TEXT',
        'LINK_TEXT': 'LINK_TEXT',
        'TAG_NAME': 'TAG_NAME',
        'CSS_SELECTOR': 'CSS_SELECTOR',
    }
    return mapping.get(strategy, 'XPATH')


def generate_from_workflow(workflow_results: Dict[str, Any], test_name: str, page_object_files: List[Dict[str, Any]] = None, output_dir: str = 'generated_tests') -> Dict[str, Any]:
    """
    Generate regression test from workflow results using page objects.
    
    Args:
        workflow_results: Result dict from orchestrator.execute_workflow()
        test_name: Name for the test (will be converted to snake_case)
        page_object_files: List of page object file info with page names and elements
        output_dir: Output directory for generated test files
    
    Returns:
        Dict with status, file path, and statistics
    """
    
    try:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract action flow from workflow
        action_flow = extract_action_flow(workflow_results)
        
        # If no actions but we have page objects, generate template test
        if not action_flow:
            if not page_object_files:
                return {
                    'status': 'error',
                    'message': 'No executed actions found. Try running Option 1 (Explore) with a device first, or ensure page objects are generated.'
                }
            
            # Generate template test from page objects alone
            logger.info("No executed actions found. Generating template test from page objects...")
            action_flow = []  # Use empty action flow - test will use page object methods directly
        
        # Get device info and platform from workflow results
        device_info = workflow_results.get('device_info', {})
        platform = workflow_results.get('platform', 'ios')
        
        # Generate test code
        if page_object_files:
            # Generate test using page objects
            test_code = generate_test_code_with_page_objects(
                test_name, 
                page_object_files,
                action_flow,  # Pass actual actions!
                platform, 
                device_info
            )
        else:
            # Fallback: generate test with hardcoded locators
            test_code = generate_test_code(test_name, action_flow, platform, device_info)
        
        # Write to file
        test_filename = f'test_{test_name}.py'
        test_filepath = os.path.join(output_dir, test_filename)
        
        with open(test_filepath, 'w') as f:
            f.write(test_code)
        
        # Count non-empty lines
        line_count = len([l for l in test_code.split('\n') if l.strip()])
        
        # Calculate test count - prefer action flow, fall back to page objects
        if action_flow:
            test_count = len(action_flow)
        elif page_object_files:
            # Count total methods available in page objects
            test_count = sum(len(pom.get('element_names', [])) for pom in page_object_files)
        else:
            test_count = 1  # At least 1 template test
        
        return {
            'status': 'success',
            'filepath': test_filepath,
            'filename': test_filename,
            'test_file': test_filename,
            'test_count': test_count,
            'action_count': len(action_flow),
            'line_count': line_count,
            'actions': action_flow,
            'test_code': test_code
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to generate test: {str(e)}'
        }


def main():
    """Demo mode: generate pytest test from sample workflow results."""
    
    # Sample workflow results
    sample_workflow = {
        'status': 'success',
        'workflow_steps': 3,
        'steps_completed': 3,
        'platform': 'ios',
        'results': [
            {
                'status': 'success',
                'actions_executed': [
                    {
                        'tool': 'appium_find_element',
                        'params': {'strategy': 'ACCESSIBILITY_ID', 'selector': 'email_input'},
                        'result': {
                            'status': 'success',
                            'elementUUID': 'uuid-1',
                            'strategy': 'ACCESSIBILITY_ID',
                            'selector': 'email_input',
                            'count': 1
                        }
                    },
                    {
                        'tool': 'appium_set_value',
                        'params': {'elementUUID': 'uuid-1', 'text': 'user@example.com'},
                        'result': {
                            'status': 'success',
                            'elementUUID': 'uuid-1',
                            'text': 'user@example.com'
                        }
                    }
                ]
            },
            {
                'status': 'success',
                'actions_executed': [
                    {
                        'tool': 'appium_find_element',
                        'params': {'strategy': 'XPATH', 'selector': '//XCUIElementTypeButton[@name="Login"]'},
                        'result': {
                            'status': 'success',
                            'elementUUID': 'uuid-2',
                            'strategy': 'XPATH',
                            'selector': '//XCUIElementTypeButton[@name="Login"]',
                            'count': 1
                        }
                    },
                    {
                        'tool': 'appium_click',
                        'params': {'elementUUID': 'uuid-2'},
                        'result': {
                            'status': 'success',
                            'elementUUID': 'uuid-2'
                        }
                    }
                ]
            },
            {
                'status': 'success',
                'actions_executed': [
                    {
                        'tool': 'appium_screenshot',
                        'params': {},
                        'result': {
                            'status': 'success',
                            'filename': 'screenshot'
                        }
                    }
                ]
            }
        ]
    }
    
    # Generate test
    result = generate_from_workflow(sample_workflow, 'login_workflow')
    
    if result.get('status') == 'success':
        console.print(
            Panel(
                Text('✓ Pytest Test Generated Successfully', style='bold green'),
                title='[bold]Test Generation[/bold]',
                expand=False
            )
        )
        console.print(f"  File: {result['filepath']}")
        console.print(f"  Lines: {result['line_count']}")
        console.print(f"  Actions: {result['action_count']}")
        console.print(f"\n  Framework: pytest (modern, fast, powerful)")
        console.print(f"\n  Uses REAL LOCATORS (no AI/Bedrock dependency):")
        for action in result.get('actions', [])[:5]:
            if action.get('strategy') and action.get('selector'):
                console.print(f"    • {action['action']}: {action['strategy']} = {action['selector']}")
        if len(result.get('actions', [])) > 5:
            console.print(f"    ... and {len(result['actions']) - 5} more actions")
        console.print(f"\n  Run with: pytest {result['filepath']} -v")
    else:
        console.print(Panel(
            Text(f"✗ Failed: {result.get('message')}", style='bold red'),
            title='[bold]Test Generation Error[/bold]',
            expand=False
        ))


if __name__ == '__main__':
    main()
