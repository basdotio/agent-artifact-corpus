"""
Generate Page Object Model (POM) from captured workflow execution.
Creates organized page classes with locators and action methods.
Enables maintainable test automation with clear separation of concerns.

Page Object Model Benefits:
- Locators organized by page/screen
- Reusable methods for common actions
- Easy maintenance when UI changes
- Cleaner test code
- Better collaboration between teams
"""
import json
import logging
import os
from typing import Dict, Any, List, Optional
from collections import defaultdict
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

logger = logging.getLogger(__name__)
console = Console()

# Setup Jinja2 environment
TEMPLATE_DIR = Path(__file__).parent / 'templates'
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html', 'xml']),
    trim_blocks=True,
    lstrip_blocks=True
)

# Add custom filters
def pascal_case(snake_str: str) -> str:
    """Convert snake_case to PascalCase."""
    return ''.join(word.capitalize() for word in snake_str.split('_'))

jinja_env.filters['pascal_case'] = pascal_case


def identify_pages_from_workflow(workflow_results: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract page/screen information from workflow results.
    Uses screen labels from prompts to detect page boundaries.
    Groups elements by their logical page/screen.
    
    Returns:
    {
        'login_page': [...elements...],
        'home_page': [...elements...],
        'product_details_page': [...elements...]
    }
    """
    pages = defaultdict(list)
    results = workflow_results.get('results', [])
    current_page = 'home_page'  # Default page
    seen_selectors = set()  # Track to avoid duplicates
    
    for step_idx, step_result in enumerate(results, 1):
        # Check if step has a prompt that indicates a page change
        step_prompt = step_result.get('prompt', '').lower()
        
        # Extract page name from "screen: xxx" or "page: xxx" pattern
        detected_page = detect_page_from_prompt(step_prompt)
        if detected_page:
            current_page = detected_page
        
        actions_executed = step_result.get('actions_executed', [])
        
        for action in actions_executed:
            tool = action.get('tool', '')
            params = action.get('params', {})
            action_result = action.get('result', {})
            
            if action_result.get('status') == 'success':
                # Screenshot often indicates page transition
                if tool == 'appium_screenshot':
                    # Current page should already be set from prompt
                    pass
                
                # Capture find_element with locator
                elif tool == 'appium_find_element':
                    strategy = action_result.get('strategy', params.get('strategy'))
                    selector = action_result.get('selector', params.get('selector'))
                    
                    # Debug: Log what we're processing
                    import sys
                    print(f"DEBUG: strategy={strategy!r} | selector={selector!r}", file=sys.stderr)
                    
                    element_name_attempt = generate_element_name(selector, strategy)
                    is_valid = is_valid_locator(selector, strategy)
                    
                    print(f"DEBUG:   valid={is_valid} | name={element_name_attempt}", file=sys.stderr)
                    
                    # Validate selector
                    if not selector or not is_valid:
                        if not is_valid and selector:
                            print(f"🚫 REJECTED: {element_name_attempt:30} | strategy={strategy} | selector={selector[:50]}", file=sys.stderr)
                        continue
                    
                    # Skip duplicates
                    selector_key = f"{strategy}:{selector}"
                    if selector_key in seen_selectors:
                        continue
                    seen_selectors.add(selector_key)
                    
                    element_name = generate_element_name(selector, strategy)
                    
                    # Skip if element name is malformed
                    if not is_valid_element_name(element_name):
                        continue
                    
                    # Refine selector to remove overly complex conditions
                    refined_selector = refine_selector(selector, strategy)
                    
                    pages[current_page].append({
                        'name': element_name,
                        'strategy': strategy,
                        'selector': refined_selector,
                        'action_type': 'find',
                        'step': step_idx,
                        'description': f'Find element: {element_name}'
                    })
                
                # Track click actions
                elif tool == 'appium_click':
                    if pages[current_page]:
                        last_element = pages[current_page][-1]
                        last_element['action_type'] = 'click'
                
                # Track input/set_value
                elif tool == 'appium_set_value':
                    text = action_result.get('text', params.get('text', ''))
                    if pages[current_page]:
                        last_element = pages[current_page][-1]
                        last_element['action_type'] = 'input'
                        last_element['input_value'] = text
    
    return dict(pages)


def detect_page_from_prompt(prompt: str) -> Optional[str]:
    """
    Extract page name from prompt.
    Detects explicit screen markers in format: "[screen: xxx] prompt text"
    
    Examples:
    - "[screen: login screen] Tap on email" -> "login_screen_page"
    - "[screen: home screen] Wait for load" -> "home_screen_page"
    - "[screen: product details screen] Scroll down" -> "product_details_screen_page"
    """
    prompt_lower = prompt.lower()
    
    # Look for "[screen: xxx]" pattern
    if prompt.startswith('[screen:') or '[screen:' in prompt_lower:
        # Find content between [screen: and ]
        start_idx = prompt_lower.find('[screen:')
        if start_idx >= 0:
            content_start = start_idx + len('[screen:')
            end_idx = prompt_lower.find(']', content_start)
            if end_idx > content_start:
                screen_name = prompt[content_start:end_idx].strip()
                # Convert "login screen" -> "login_screen_page"
                if screen_name:
                    return screen_name.replace(' ', '_') + '_page'
    
    return None


def is_valid_locator(selector: str, strategy: str) -> bool:
    """Validate that selector is a proper locator."""
    if not selector or not isinstance(selector, str):
        return False
    
    # Normalize strategy to uppercase for comparison
    strategy_upper = (strategy or '').upper()
    
    # XPATH validation - must have locator syntax, not just plain text
    if strategy_upper == 'XPATH':
        # Must be reasonable length
        if len(selector.strip()) < 3:
            return False
        # Must have locator syntax: //, @, [, or ==
        has_syntax = (selector.startswith('//') or '@' in selector or 
                      '[' in selector or '==' in selector)
        if not has_syntax:
            # Reject plain text that is just words/spaces (no locator syntax at all)
            if selector and all(c.isalpha() or c.isspace() for c in selector):
                return False
    else:
        # For other strategies (ACCESSIBILITY_ID, ID, -ios predicate string, etc.)
        # Require minimum length of at least 1 character
        if len(selector.strip()) < 1:
            return False
    
    return True


def refine_selector(selector: str, strategy: str) -> str:
    """
    Refine/simplify overly complex selectors to be more maintainable.
    
    Rules:
    1. Simplify XPath with multiple OR conditions to use the most specific one
    2. Remove redundant conditions that overlap
    3. Prefer exact matches over loose contains/partial matches
    4. For iOS: Prefer @value, @name, @label over complex predicates
    """
    if not selector or strategy.upper() != 'XPATH':
        return selector
    
    import re
    
    # Rule 1: If selector has multiple | (OR) conditions, try to use just the first or most specific one
    if ' | ' in selector:
        parts = selector.split(' | ')
        # Try to pick the most specific (shortest, most qualified) part
        best_part = parts[0]  # Start with first
        for part in parts:
            # Prefer parts with exact attribute matches over loose contains
            if "@" in part and "contains" not in part.lower():
                best_part = part
                break
        selector = best_part.strip()
    
    # Rule 2: Simplify multiple contains conditions - keep only the most restrictive
    # Example: [contains(@label, 'email') or contains(@name, 'email') or contains(@value, 'email')]
    # Becomes: [contains(@value, 'Email')]  (most likely to be correct)
    contains_match = re.findall(r"contains\(@(\w+),\s*['\"]([^'\"]+)['\"]\)", selector)
    if len(contains_match) > 1:
        # Prefer value > name > label > placeholder
        priority_attrs = ['value', 'name', 'label', 'placeholder', 'text']
        for attr in priority_attrs:
            for found_attr, found_text in contains_match:
                if found_attr.lower() == attr.lower():
                    # Reconstruct with just this one condition
                    selector = re.sub(
                        r"\[.*contains\(@\w+,.*?\).*?\]",
                        f"[contains(@{attr}, '{found_text}')]",
                        selector
                    )
                    return selector
    
    # Rule 3: Prefer exact attribute matching over contains
    # If we have both exact and contains, prefer exact
    if "@name=" in selector and "contains(@name" in selector:
        selector = re.sub(r"contains\(@name\s*,\s*['\"]([^'\"]+)['\"]\)", r"@name='\1'", selector)
    
    # Rule 4: Remove redundant element type + generic conditions
    # Example: //XCUIElementTypeTextField[contains(@label, 'email') or contains(@name, 'email') or contains(@value, 'email')]
    # Becomes: //XCUIElementTypeSecureTextField (if it's specifically for password)
    # or just: //XCUIElementTypeTextField[contains(@value, 'Email')]
    
    return selector


def is_valid_element_name(name: str) -> bool:
    """Validate that element name is safe for Python identifiers."""
    if not name or len(name) < 2:
        return False
    
    # Can't have special characters beyond underscore
    invalid_chars = [',', '(', ')', "'", '"', '[', ']']
    for char in invalid_chars:
        if char in name:
            return False
    
    # Must start with letter or underscore
    if not (name[0].isalpha() or name[0] == '_'):
        return False
    
    return True


def generate_element_name(selector: str, strategy: str) -> str:
    """Generate a clean element name from selector."""
    import re
    
    # Key identifiers - exact matches
    if 'Email' in selector or 'email' in selector:
        return 'email_field'
    elif 'Password' in selector or 'password' in selector:
        return 'password_field'
    elif 'Sign In' in selector or 'sign in' in selector.lower():
        return 'signin_button'
    elif 'Login' in selector or 'login' in selector.lower():
        return 'login_button'
    elif 'Submit' in selector or 'submit' in selector.lower():
        return 'submit_button'
    elif 'Cancel' in selector or 'cancel' in selector.lower():
        return 'cancel_button'
    elif 'OK' in selector or 'ok' in selector.lower():
        return 'ok_button'
    elif 'Next' in selector or 'next' in selector.lower():
        return 'next_button'
    elif 'Back' in selector or 'back' in selector.lower():
        return 'back_button'
    elif 'Add to Card' in selector or 'add to cart' in selector.lower():
        return 'add_to_cart_button'
    elif 'Crew Neck' in selector or 'crew neck' in selector.lower():
        return 'crew_neck_product'
    
    # Detect iOS element types from predicates (e.g., "type == 'XCUIElementTypeSecureTextField'")
    if 'XCUIElementTypeSecureTextField' in selector:
        return 'password_field'
    elif 'XCUIElementTypeTextField' in selector:
        # Could be email, username, search, or generic text field
        # Default to input_field; context from nearby elements would help
        return 'text_input_field'
    elif 'XCUIElementTypeButton' in selector:
        return 'button_element'
    
    # Extract from CONTAINS patterns in XPath
    # Pattern: CONTAINS 'text' or CONTAINS[c] 'text' (case-insensitive)
    contains_match = re.findall(r"CONTAINS[^']*'([^']+)'", selector, re.IGNORECASE)
    if contains_match:
        # Take first meaningful match
        for text in contains_match:
            text_clean = text.strip().lower().replace(' ', '_')
            if len(text_clean) > 2 and is_valid_element_name(text_clean):
                # Determine element type from text
                if any(x in text.lower() for x in ['button', 'click', 'tap', 'submit', 'ok', 'sign', 'login']):
                    return text_clean + '_button'
                elif any(x in text.lower() for x in ['search', 'input', 'email', 'password', 'text', 'field']):
                    return text_clean + '_field'
                elif any(x in text.lower() for x in ['size', 'm', 's', 'l', 'xl']):
                    return 'size_' + text_clean
                else:
                    # Generic element (product, card, item, etc.)
                    return text_clean + '_element'
    
    # Extract from @name attribute
    if '@name=' in selector or '@name =' in selector:
        name_match = re.search(r"@name\s*=\s*['\"]([^'\"]+)['\"]", selector)
        if name_match:
            text = name_match.group(1).strip().lower().replace(' ', '_')
            if is_valid_element_name(text):
                return text + '_field'
    
    # Extract from @label attribute
    if '@label=' in selector or '@label =' in selector:
        label_match = re.search(r"@label\s*=\s*['\"]([^'\"]+)['\"]", selector)
        if label_match:
            text = label_match.group(1).strip().lower().replace(' ', '_')
            if is_valid_element_name(text):
                return text + '_label'
    
    # Extract from @placeholder attribute
    if '@placeholder=' in selector or '@placeholder =' in selector:
        placeholder_match = re.search(r"@placeholder\s*=\s*['\"]([^'\"]+)['\"]", selector)
        if placeholder_match:
            text = placeholder_match.group(1).strip().lower().replace(' ', '_')
            if is_valid_element_name(text):
                return text + '_field'
    
    # Extract from @value attribute
    if '@value=' in selector or '@value =' in selector:
        value_match = re.search(r"@value\s*=\s*['\"]([^'\"]+)['\"]", selector)
        if value_match:
            text = value_match.group(1).strip().lower().replace(' ', '_')
            if is_valid_element_name(text):
                return text + '_element'
    
    # Fallback: use hash of selector (for complex/generic selectors)
    return f'element_{abs(hash(selector)) % 10000}'


def generate_page_object_code(page_name: str, elements: List[Dict[str, Any]]) -> str:
    """Generate Page Object Model class code for a page using Jinja2 template."""
    class_name = ''.join(word.capitalize() for word in page_name.split('_'))
    page_display_name = page_name.replace('_', ' ').title()
    
    # Load and render template
    template = jinja_env.get_template('page_object.jinja2')
    
    # Prepare elements for template
    template_elements = []
    for elem in elements:
        original_strategy = (elem['strategy'] or '').upper().replace(' ', '_').replace('-', '_').strip('_')
        selector = elem['selector']
        
        # If original strategy was iOS predicate, convert to XPath format
        if original_strategy == 'IOS_PREDICATE_STRING':
            # Convert iOS predicate to XPath
            selector = convert_ios_predicate_to_xpath(selector)
        
        template_elements.append({
            'name': elem['name'],
            'strategy': strategy_to_appiumby(elem['strategy']),
            'selector': selector.replace('"', '\\"'),
            'action_type': elem.get('action_type', 'find'),
            'input_value': elem.get('input_value', '')
        })
    
    # Render template
    code = template.render(
        class_name=class_name,
        page_display_name=page_display_name,
        elements=template_elements
    )
    
    return code


def strategy_to_appiumby(strategy: str) -> str:
    """Convert strategy string to AppiumBy constant."""
    # Normalize strategy to uppercase and handle variations
    strategy_normalized = (strategy or '').upper().replace(' ', '_').replace('-', '_')
    # Strip leading/trailing underscores that may result from normalization
    strategy_normalized = strategy_normalized.strip('_')
    
    mapping = {
        'XPATH': 'XPATH',
        'ACCESSIBILITY_ID': 'ACCESSIBILITY_ID',
        'ID': 'ID',
        'NAME': 'NAME',
        'CLASS_NAME': 'CLASS_NAME',
        'CSS_SELECTOR': 'CSS_SELECTOR',
        'IOS_PREDICATE_STRING': 'XPATH',  # iOS predicates are converted to XPath
    }
    
    # Try exact match first
    if strategy_normalized in mapping:
        return mapping[strategy_normalized]
    
    # Default to XPATH for unknown/unrecognized strategies
    # (safer than returning unknown attribute names)
    return 'XPATH'


def convert_ios_predicate_to_xpath(predicate: str) -> str:
    """
    Convert iOS predicate string to valid XPath format.
    
    Examples:
    - "type == 'XCUIElementTypeTextField' AND label CONTAINS[c] 'email'"
      -> "//XCUIElementTypeTextField[contains(@label, 'email')]"
    - "label CONTAINS 'Crew Neck'"
      -> "//*[contains(@label, 'Crew Neck')]"
    """
    import re
    
    # Remove '-ios predicate string:' prefix if present
    if predicate.startswith('-ios predicate string:'):
        predicate = predicate[len('-ios predicate string:'):].strip()
    
    # Extract type if specified (e.g., "type == 'XCUIElementTypeTextField'")
    element_type = "*"
    type_match = re.search(r"type\s*==\s*['\"]([^'\"]+)['\"]", predicate)
    if type_match:
        element_type = type_match.group(1)
        # Remove type from predicate for further processing
        predicate = re.sub(r"type\s*==\s*['\"][^'\"]+['\"]\s*AND\s*", "", predicate)
        predicate = re.sub(r"\s*AND\s*type\s*==\s*['\"][^'\"]+['\"]", "", predicate)
    
    # Convert predicates to XPath conditions
    conditions = []
    
    # Handle CONTAINS (case-insensitive) -> contains()
    contains_matches = re.findall(r"(label|name|placeholder|value|text)\s+CONTAINS\[c\]\s*['\"]([^'\"]+)['\"]", predicate, re.IGNORECASE)
    for attr, value in contains_matches:
        conditions.append(f"contains(@{attr.lower()}, '{value}')")
    
    # Handle CONTAINS (case-sensitive) -> contains()
    contains_matches = re.findall(r"(label|name|placeholder|value|text)\s+CONTAINS\s+['\"]([^'\"]+)['\"]", predicate, re.IGNORECASE)
    for attr, value in contains_matches:
        conditions.append(f"contains(@{attr.lower()}, '{value}')")
    
    # Build XPath
    if conditions:
        xpath = f"//{element_type}[{' or '.join(conditions)}]"
    else:
        xpath = f"//{element_type}"
    
    return xpath


def parse_existing_page_object(filepath: str) -> List[Dict[str, Any]]:
    """
    Parse an existing page object file to extract element locators.
    
    Returns list of dicts with: name, strategy, selector
    """
    elements = []
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        import re
        # Match patterns like: EMAIL_FIELD_LOCATOR = (AppiumBy.XPATH, "type == 'email'")
        # Use pattern that correctly handles nested quotes
        pattern = r'(\w+)_LOCATOR\s*=\s*\(\s*AppiumBy\.(\w+)\s*,\s*"([^"]*)"\s*\)'
        
        for match in re.finditer(pattern, content):
            elem_name_upper = match.group(1)
            strategy = match.group(2)
            selector = match.group(3)
            
            # Convert back to lowercase with underscores (UPPER_NAME -> upper_name)
            elem_name = elem_name_upper.lower()
            
            elements.append({
                'name': elem_name,
                'strategy': strategy,
                'selector': selector
            })
    except (FileNotFoundError, IOError):
        pass
    
    return elements


def merge_elements_without_duplicates(existing: List[Dict[str, Any]], new: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge new elements with existing, removing duplicates.
    
    Duplicates are detected by: element name (primary key)
    When same element name appears in both, NEW replaces EXISTING (updates selector).
    This prevents duplication when Bedrock returns slightly different selectors.
    """
    # Create dict keyed by element name for fast lookup
    merged_dict = {}
    
    # Add existing elements first
    for elem in existing:
        name = elem.get('name', '').lower()
        if name:
            merged_dict[name] = elem
    
    # Update with new elements (NEW replaces OLD if same name)
    for new_elem in new:
        name = new_elem.get('name', '').lower()
        if name:
            merged_dict[name] = new_elem
    
    # Convert back to list, maintaining order (new elements last)
    result = list(merged_dict.values())
    return result


def generate_page_objects(workflow_results: Dict[str, Any], output_dir: str = 'page_objects') -> Dict[str, Any]:
    """
    Generate Page Object Model files from workflow results.
    Merges with existing page objects (appends, no duplicates).
    
    Args:
        workflow_results: Result dict from orchestrator.execute_workflow()
        output_dir: Directory where POM files will be saved
    
    Returns:
        Dict with status, file paths, and page object info
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract pages and elements from workflow
        pages = identify_pages_from_workflow(workflow_results)
        
        if not pages:
            return {
                'status': 'error',
                'message': 'No pages identified in workflow'
            }
        
        generated_files = []
        
        # Generate a file for each page
        for page_name, new_elements in pages.items():
            if not new_elements:
                continue
            
            filename = f'{page_name}.py'
            filepath = os.path.join(output_dir, filename)
            
            # Check if file exists and merge with existing elements
            elements_to_write = new_elements
            if os.path.exists(filepath):
                existing_elements = parse_existing_page_object(filepath)
                if existing_elements:
                    logger.debug(f"Merging: {len(existing_elements)} existing + {len(new_elements)} new elements from {filename}")
                    elements_to_write = merge_elements_without_duplicates(existing_elements, new_elements)
                    logger.debug(f"Result: {len(elements_to_write)} total elements (duplicates removed)")
            
            # Generate page object code with merged elements
            code = generate_page_object_code(page_name, elements_to_write)
            
            # Write to file
            with open(filepath, 'w') as f:
                f.write(code)
            
            generated_files.append({
                'page_name': page_name,
                'filepath': filepath,
                'filename': filename,
                'elements': len(elements_to_write),
                'element_names': [e['name'] for e in elements_to_write]
            })
        
        # Generate __init__.py for imports
        init_content = '"""Page Object Model package."""\n\n'
        for file_info in generated_files:
            class_name = ''.join(word.capitalize() for word in file_info['page_name'].split('_'))
            init_content += f'from .{file_info["page_name"]} import {class_name}\n'
        
        page_names = [f'"{f["page_name"]}"' for f in generated_files]
        init_content += f'\n__all__ = [{", ".join(page_names)}]\n'
        
        with open(os.path.join(output_dir, '__init__.py'), 'w') as f:
            f.write(init_content)
        
        return {
            'status': 'success',
            'output_dir': output_dir,
            'page_count': len(generated_files),
            'files': generated_files,
            'total_elements': sum(f['elements'] for f in generated_files)
        }
    
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Failed to generate page objects: {str(e)}'
        }


def main():
    """Demo: generate page objects from sample workflow."""
    
    sample_workflow = {
        'status': 'success',
        'results': [
            {
                'status': 'success',
                'actions_executed': [
                    {
                        'tool': 'appium_screenshot',
                        'result': {'status': 'success'}
                    },
                    {
                        'tool': 'appium_find_element',
                        'params': {'strategy': 'XPATH', 'selector': '//TextField[@name="Email"]'},
                        'result': {
                            'status': 'success',
                            'strategy': 'XPATH',
                            'selector': '//TextField[@name="Email"]'
                        }
                    },
                    {
                        'tool': 'appium_set_value',
                        'params': {'text': 'user@example.com'},
                        'result': {'status': 'success', 'text': 'user@example.com'}
                    }
                ]
            },
            {
                'status': 'success',
                'actions_executed': [
                    {
                        'tool': 'appium_find_element',
                        'params': {'strategy': 'XPATH', 'selector': '//Button[@name="Password"]'},
                        'result': {
                            'status': 'success',
                            'strategy': 'XPATH',
                            'selector': '//SecureTextField[@placeholder="Password"]'
                        }
                    },
                    {
                        'tool': 'appium_set_value',
                        'params': {'text': 'Test123'},
                        'result': {'status': 'success', 'text': 'Test123'}
                    }
                ]
            },
            {
                'status': 'success',
                'actions_executed': [
                    {
                        'tool': 'appium_find_element',
                        'params': {'strategy': 'XPATH', 'selector': '//Button[@name="Sign In"]'},
                        'result': {
                            'status': 'success',
                            'strategy': 'XPATH',
                            'selector': '//Button[@name="Sign In"]'
                        }
                    },
                    {
                        'tool': 'appium_click',
                        'result': {'status': 'success'}
                    }
                ]
            }
        ]
    }
    
    # Generate page objects
    result = generate_page_objects(sample_workflow)
    
    if result.get('status') == 'success':
        console.print(
            Panel(
                Text('✓ Page Objects Generated Successfully', style='bold green'),
                title='[bold cyan]Page Object Model[/bold cyan]',
                expand=False
            )
        )
        console.print(f"  Output directory: {result['output_dir']}")
        console.print(f"  Pages created: {result['page_count']}")
        console.print(f"  Total elements: {result['total_elements']}")
        console.print(f"\n  Generated files:")
        for file_info in result['files']:
            console.print(f"    • {file_info['filename']}")
            console.print(f"      Elements: {', '.join(file_info['element_names'][:3])}")
            if len(file_info['element_names']) > 3:
                console.print(f"      ... and {len(file_info['element_names']) - 3} more")
    else:
        console.print(Panel(
            Text(f"✗ Failed: {result.get('message')}", style='bold red'),
            title='[bold]Generation Error[/bold]',
            expand=False
        ))


if __name__ == '__main__':
    main()
