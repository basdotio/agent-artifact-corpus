"""AWS Bedrock integration for NLP prompt interpretation."""
import json
import os
import boto3
import logging
import re
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

logger = logging.getLogger(__name__)
console = Console()


def extract_elements_from_page_source(page_source: str, max_elements: int = 20) -> List[Dict[str, str]]:
    """Extract key interactive elements from page source XML/HTML."""
    if not page_source:
        return []
    
    elements = []
    
    # Look for common patterns in the page source
    # For XCUITest elements
    patterns = [
        (r'<XCUIElementTypeTextField[^>]*name="([^"]*)"', 'TextInput'),
        (r'<XCUIElementTypeSecureTextField[^>]*name="([^"]*)"', 'PasswordInput'),
        (r'<XCUIElementTypeButton[^>]*name="([^"]*)"', 'Button'),
        (r'<XCUIElementTypeStaticText[^>]*name="([^"]*)"', 'Text'),
        (r'name="([^"]*)"[^>]*type="text"', 'TextInput'),
        (r'name="([^"]*)"[^>]*type="password"', 'PasswordInput'),
        (r'<button[^>]*>([^<]*)</button>', 'Button'),
    ]
    
    for pattern, element_type in patterns:
        matches = re.findall(pattern, page_source, re.IGNORECASE)
        for match in matches[:3]:  # Limit to first 3 of each type
            if match.strip():
                elements.append({
                    'name': match.strip(),
                    'type': element_type,
                    'use': f"accessibility id='{match.strip()}' or xpath containing '{match.strip()}'"
                })
    
    # Remove duplicates while preserving order
    seen = set()
    unique_elements = []
    for elem in elements:
        key = (elem['name'], elem['type'])
        if key not in seen and len(unique_elements) < max_elements:
            seen.add(key)
            unique_elements.append(elem)
    
    return unique_elements


# All 51 available tools documentation
TOOLS_DOCUMENTATION = """
AVAILABLE MOBILE AUTOMATION TOOLS (51 Total):

SESSION MANAGEMENT (5):
1. select_platform(platform: "ios"|"android") - Select target platform
2. select_device(device_id: string, device_name?: string) - Select specific device
3. create_session(capabilities: object, appium_server_url?: string) - Create automation session
4. delete_session() - End automation session
5. open_notifications() - Open notifications panel

ELEMENT INTERACTIONS (16):
6. appium_find_element(strategy: string, selector: string) - Find element by strategy. Valid strategies: "xpath", "id", "name", "class name", "accessibility id", "css selector", "-android uiautomator", "-ios predicate string", "-ios class chain"
7. appium_click(elementUUID: string) - Click element
8. appium_double_tap(elementUUID: string) - Double tap element
9. appium_long_press(elementUUID: string, duration?: number) - Long press element
10. appium_drag_and_drop(sourceUUID: string, targetUUID: string) - Drag element to target
11. appium_press_key(keyCode: string, metaState?: number) - Press keyboard key
12. appium_set_value(elementUUID: string, text: string) - Type text in element (note: parameter is 'text' not 'value')
13. appium_get_text(elementUUID: string) - Read element text
14. appium_get_active_element() - Get currently focused element
15. appium_screenshot(filename?: string) - Capture full page screenshot
16. appium_element_screenshot(elementUUID: string) - Screenshot specific element
17. appium_get_page_source() - Get page hierarchy/DOM
18. appium_get_orientation() - Get device orientation
19. appium_set_orientation(orientation: "PORTRAIT"|"LANDSCAPE") - Set device orientation
20. appium_handle_alert(action: "accept"|"dismiss"|"getText") - Handle alert dialogs

NAVIGATION (3):
21. appium_scroll(direction: "up"|"down"|"left"|"right", distance?: number) - Scroll page
22. appium_scroll_to_element(elementUUID: string, direction?, maxSwipes?) - Scroll until element visible
23. appium_swipe(startX: number, startY: number, endX: number, endY: number, duration?) - Swipe gesture

APP MANAGEMENT (7):
24. appium_activate_app(appId: string) - Activate/switch app
25. appium_install_app(appPath: string) - Install app from file
26. appium_uninstall_app(appId: string) - Uninstall app
27. appium_terminate_app(appId: string) - Stop running app
28. appium_list_apps() - List installed apps
29. appium_is_app_installed(appId: string) - Check if app is installed
30. appium_deep_link(url: string) - Open deep link

CONTEXT (2):
31. appium_get_contexts() - Get available contexts (native/webview)
32. appium_switch_context(contextName: string) - Switch between native and web contexts

iOS SPECIFIC (3):
33. appium_boot_simulator(simulatorUDID: string) - Start iOS simulator
34. appium_setup_wda(simulatorUDID: string, wdaBundleId?: string) - Setup WebDriverAgent
35. appium_install_wda(wdaPath: string, simulatorUDID: string) - Install WebDriverAgent

TEST GENERATION (2):
36. appium_generate_locators(strategy?: string) - Extract element locators from page
37. appium_generate_tests(testName: string, actions: array) - Generate test script from actions

DOCUMENTATION (1):
38. appium_answer_appium(question: string) - Answer questions about Appium
"""


class BedrockClient:
    """AWS Bedrock client for Claude integration."""
    
    def __init__(
        self,
        region: str = "us-east-1",
        model_id: str = None,
        max_tokens: int = 2000,
        anthropic_version: str = None
    ):
        """Initialize Bedrock client.
        
        Args:
            region: AWS region
            model_id: Model ID to use. If None, checks BEDROCK_MODEL_ID env var
            max_tokens: Maximum tokens for response
            anthropic_version: Bedrock API version. If None, checks BEDROCK_ANTHROPIC_VERSION env var
        """
        self.region = region
        # Use environment variable or provided parameter
        self.model_id = model_id or os.getenv("BEDROCK_MODEL_ID")
        self.max_tokens = max_tokens
        # Try to use inference profile if available (recommended for Haiku)
        self.inference_profile_arn = os.getenv("BEDROCK_INFERENCE_PROFILE_ARN")
        self.anthropic_version = anthropic_version or os.getenv("BEDROCK_ANTHROPIC_VERSION")
        
        # Validate model_id is configured
        if not self.model_id:
            raise ValueError(
                "BEDROCK_MODEL_ID environment variable must be set. "
                "Example: export BEDROCK_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0"
            )
        
        try:
            self.client = boto3.client("bedrock-runtime", region_name=region)
            logger.info(f"✓ Bedrock client initialized: {self.model_id}")
        except Exception as e:
            logger.error(f"✗ Failed to initialize Bedrock: {e}")
            raise
    
    def interpret_prompt(
        self,
        prompt: str,
        platform: str = "ios",
        device_info: Optional[Dict[str, Any]] = None,
        page_source: Optional[str] = None,
        execution_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Use Claude to interpret a natural language prompt and suggest MCP tools.
        
        Args:
            prompt: Natural language instruction (e.g., "Click the login button")
            platform: Target platform (ios/android)
            device_info: Device information for context
            page_source: Current page source/hierarchy for context
            execution_history: Previous action results to provide context (e.g., found element UUIDs)
        
        Returns:
            Dict with suggested actions and tool calls
        """
        
        device_context = ""
        if device_info:
            device_context = f"""
Device Information:
- Platform: {device_info.get('platform', platform)}
- Device Name: {device_info.get('device_name', 'Unknown')}
- App Bundle/Package: {device_info.get('bundle_id') or device_info.get('app_package', 'Unknown')}
"""
        
        # Build execution history context
        execution_context = ""
        last_found_element = None  # Track most recent element find
        
        if execution_history:
            execution_context = "\n\nRECENT EXECUTION HISTORY & FOUND ELEMENTS:\n"
            for i, action in enumerate(execution_history, 1):
                tool = action.get('tool', 'unknown')
                status = action.get('status', 'unknown')
                result = action.get('result', {})
                
                # Track found elements
                if tool == "appium_find_element" and status == "success":
                    if result.get('elementUUID'):
                        last_found_element = {
                            'uuid': result.get('elementUUID'),
                            'count': result.get('count', 1),
                            'strategy': action.get('params', {}).get('strategy', 'unknown'),
                            'selector': action.get('params', {}).get('selector', '')
                        }
                
                execution_context += f"[{i}] {tool} - {status}\n"
                
                # Include important results
                if tool == "appium_find_element":
                    if result.get('elementUUID'):
                        execution_context += f"    ✓ Element UUID: {result.get('elementUUID')}\n"
                    if result.get('count', 0) > 0:
                        execution_context += f"    Found {result.get('count')} element(s)\n"
                    else:
                        execution_context += f"    ⚠️  Found 0 elements\n"
                elif tool == "appium_click":
                    execution_context += f"    Result: {result.get('message', 'clicked')}\n"
                elif tool == "appium_set_value":
                    execution_context += f"    Result: {result.get('message', 'value set')}\n"
        
        # Add context about how to use the last found element
        if last_found_element:
            execution_context += f"\n*** IMPORTANT: The most recent action found an element ***\n"
            execution_context += f"Element UUID: {last_found_element['uuid']}\n"
            execution_context += f"Strategy: {last_found_element['strategy']}\n"
            execution_context += f"Selector: {last_found_element['selector']}\n"
            execution_context += f"\nFor any interaction with this element (type, click, etc.), use this UUID directly.\n"
            execution_context += f"Do NOT re-find the element - use appium_set_value or appium_click with UUID: {last_found_element['uuid']}\n"
        
        
        page_state = ""
        if page_source:
            # Extract key elements from page source
            extracted_elements = extract_elements_from_page_source(page_source)
            
            logger.debug(f"Extracted {len(extracted_elements)} elements from page")
            for elem in extracted_elements:
                logger.debug(f"  - {elem['type']}: {elem['name']}")
            
            # Debug: Save page source to file for inspection
            try:
                with open('/tmp/page_source_debug.xml', 'w') as f:
                    f.write(page_source)
                logger.debug("Page source saved to /tmp/page_source_debug.xml")
            except:
                pass
            
            # Truncate page source if too long
            source_preview = page_source[:1000] if len(page_source) > 1000 else page_source
            
            elements_info = ""
            if extracted_elements:
                elements_info = "\n\nKey Interactive Elements on Page:\n"
                for elem in extracted_elements:
                    elements_info += f"- {elem['type']}: '{elem['name']}'\n"
            
            page_state = f"""
Current Page State:
{source_preview}{elements_info}
"""
        
        system_prompt = """You are an expert mobile automation engineer. Your task is to interpret natural language instructions and suggest specific tool calls to execute them.

""" + TOOLS_DOCUMENTATION + """

Response Format - Return ONLY a JSON array of action objects:
[
  {
    "tool": "tool_name",
    "params": {key: value},
    "reasoning": "Why this action is needed"
  },
  ...
]

Guidelines:
1. Always start with appium_screenshot to see current state
2. For finding elements on iOS apps - GENERATE PRECISE, SPECIFIC SELECTORS:
   - PREFERRED STRATEGIES (in order of precision):
     a) XPath with specific element type + exact attribute: //XCUIElementTypeButton[@name='Sign In']
     b) XPath with element type + value attribute: //XCUIElementTypeTextField[contains(@value, 'Email')]
     c) XPath with element type only: //XCUIElementTypeSecureTextField (only if it's the only one of that type)
   - AVOID: Generic XPath with multiple OR conditions like [contains(@label, 'x') or contains(@name, 'x') or contains(@value, 'x')]
   - Instead: Always pick ONE specific attribute that best matches (value > name > label > placeholder)
   - Use "accessibility id" strategy ONLY if element has a distinct accessible name
   - For TextFields: Prefer specific predicates like [-ios predicate string] type == 'XCUIElementTypeTextField' AND value == 'Email'
3. CRITICAL: When find_element succeeds, it returns an "elementUUID" field. Always use that exact UUID for subsequent interactions (click, set_value, etc.)
4. For text input: ALWAYS use "appium_set_value" with TWO parameters - "elementUUID" (from find result) and "text" (the text to enter)
5. When finding a field for data entry, look for input fields that match the context (email field, password field, etc.)
6. If find returns 0 elements, try alternative strategies rather than guessing - use predicate strings or class chains
7. Always include reasoning for each action
8. Return valid JSON ONLY (no markdown wrapping)
9. IMPORTANT: Match parameter names EXACTLY from tool definitions (e.g., use "text" not "value" for appium_set_value)
10. NEVER generate placeholder UUIDs like "ELEMENT_UUID_FROM_PREVIOUS_FIND" - reference the actual UUID returned by find_element
11. CRITICAL RULE FOR WORKFLOW STEPS:
    *** If a prompt references "field you just found" or "element you just found":
    - DO NOT re-find the element
    - DO get the element UUID from "RECENT EXECUTION HISTORY & FOUND ELEMENTS" section
    - DO use that exact UUID with appium_set_value or appium_click
    - DO NOT generate appium_find_element again unless the field is truly lost or context has changed
    Example: If execution history shows "Element UUID: 11000000...", and prompt says "type into the field you just found",
    generate: {"tool": "appium_set_value", "params": {"elementUUID": "11000000...", "text": "..."}}
12. Sequential workflow context: Each prompt follows from previous actions in the same session.
    Previous steps' found elements remain cached and available during current step.
    Reference them directly rather than re-finding.
13. FIND + CLICK/INTERACT IN ONE STEP:
    When a prompt asks to tap/click/interact with an element:
    - FIRST generate appium_find_element to locate the element
    - THEN immediately generate appium_click (or appium_set_value, etc.) using the found element UUID
    - DO NOT generate find+click as two sequential "find" operations
    - The UUID from "Element UUID:" in the RECENT EXECUTION HISTORY is the one to use
    Example: For "Tap on the Sign In button":
    [
      { "tool": "appium_find_element", "params": {"strategy": "xpath", "selector": "//XCUIElementTypeButton[@name='Sign In']"} },
      { "tool": "appium_click", "params": {"elementUUID": "<use_the_found_uuid_here>"} }
    ]
13. AUTO-HEALING WITH FALLBACK STRATEGIES:
    When an action fails (status: "warning" or "error"), suggest alternative strategies:
    - For find_element failures: Try different strategies in sequence:
      1. accessibility id
      2. -ios predicate string with different attributes
      3. xpath with different selectors
      4. label-based predicates
    - For interaction failures (click, set_value): Suggest retrying with the same element UUID
    - Include "reason_for_retry" field when suggesting fallback strategies
    - Always provide 2-3 alternative approaches as the next actions if current strategy fails
    Example: If appium_find_element with "accessibility id" returns 0 elements,
    suggest trying "-ios predicate string" with class/type checks as the fallback."""
        
        user_message = f"""{device_context}
{page_state}
{execution_context}

Task: """ + prompt + """

Respond with ONLY a valid JSON array of tool calls."""
        
        try:
            logger.debug(f"Calling Bedrock: {self.model_id}")
            
            # Use converse API with inference profile ARN if available
            model_or_arn = self.inference_profile_arn or self.model_id
            
            response = self.client.converse(
                modelId=model_or_arn,
                system=[{"text": system_prompt}],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"text": user_message}
                        ]
                    }
                ],
                inferenceConfig={
                    "maxTokens": self.max_tokens,
                    "temperature": 0.7,
                    "topP": 0.9
                }
            )
            
            # Extract text from converse response
            response_body = response
            
            # Parse response from converse API
            content_block = response_body.get("output", {}).get("message", {}).get("content", [{}])[0]
            content = content_block.get("text", "")
            
            logger.debug(f"Bedrock raw response: {content[:500]}")
            
            # Extract JSON from response
            json_str = content.strip()
            
            # Try to extract from markdown code blocks
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
            
            actions = json.loads(json_str)
            if not isinstance(actions, list):
                actions = [actions]
            
            # Log actions in beautiful, readable format using Rich
            console.print()
            
            # Create header panel
            header = Text(f"✓ BEDROCK RESPONSE: {len(actions)} action(s) suggested", style="bold white on green")
            console.print(Panel(header, border_style="green", expand=False))
            
            for i, action in enumerate(actions, 1):
                tool = action.get("tool", "unknown")
                reasoning = action.get("reasoning", "No reasoning provided")
                params = action.get("params", {})
                
                # Create table for parameters
                param_table = Table(show_header=False, box=None, padding=(0, 1), expand=False)
                param_table.add_column(style="cyan", no_wrap=True)
                param_table.add_column(style="white", no_wrap=False)
                
                if params:
                    for param_key, param_val in params.items():
                        # Truncate long values for readability
                        if isinstance(param_val, str) and len(param_val) > 65:
                            display_val = param_val[:62] + "..."
                        else:
                            display_val = str(param_val)
                        param_table.add_row(f"{param_key}:", display_val)
                
                # Build the action content
                action_content = f"[bold cyan]🔧 Tool:[/bold cyan] {tool}\n"
                action_content += f"[bold cyan]📝 Reasoning:[/bold cyan] {reasoning}\n"
                action_content += f"[bold cyan]📋 Parameters:[/bold cyan]\n"
                
                # Create action panel
                if params:
                    param_str = "\n".join(f"  {k}: {str(v)[:62] + '...' if isinstance(v, str) and len(str(v)) > 65 else v}" for k, v in params.items())
                    action_panel_content = f"[bold cyan]🔧 Tool:[/bold cyan] {tool}\n[bold cyan]📝 Reasoning:[/bold cyan] {reasoning}\n[bold cyan]📋 Parameters:[/bold cyan]\n{param_str}"
                else:
                    action_panel_content = f"[bold cyan]🔧 Tool:[/bold cyan] {tool}\n[bold cyan]📝 Reasoning:[/bold cyan] {reasoning}\n[bold cyan]📋 Parameters:[/bold cyan] None"
                
                console.print(Panel(
                    action_panel_content,
                    title=f"[bold]Action {i}/{len(actions)}[/bold]",
                    border_style="cyan",
                    expand=False
                ))
            
            console.print()
            
            return {
                "status": "success",
                "actions": actions,
                "raw_response": content
            }
            
        except Exception as e:
            logger.error(f"✗ Failed to interpret prompt: {e}")
            return {
                "status": "error",
                "error": str(e),
                "actions": []
            }
    
    def validate_action(self, action: Dict[str, Any]) -> bool:
        """Validate that action uses available tool."""
        valid_tools = {
            # Session
            "select_platform", "select_device", "create_session", "delete_session", "open_notifications",
            # Interactions
            "appium_find_element", "appium_click", "appium_double_tap", "appium_long_press",
            "appium_drag_and_drop", "appium_press_key", "appium_set_value", "appium_get_text",
            "appium_get_active_element", "appium_screenshot", "appium_element_screenshot",
            "appium_get_page_source", "appium_get_orientation", "appium_set_orientation", "appium_handle_alert",
            # Navigation
            "appium_scroll", "appium_scroll_to_element", "appium_swipe",
            # App management
            "appium_activate_app", "appium_install_app", "appium_uninstall_app", "appium_terminate_app",
            "appium_list_apps", "appium_is_app_installed", "appium_deep_link",
            # Context
            "appium_get_contexts", "appium_switch_context",
            # iOS
            "appium_boot_simulator", "appium_setup_wda", "appium_install_wda",
            # Test generation
            "appium_generate_locators", "appium_generate_tests",
            # Documentation
            "appium_answer_appium"
        }
        return action.get("tool") in valid_tools
