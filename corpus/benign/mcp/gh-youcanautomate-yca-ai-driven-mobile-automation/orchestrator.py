"""Main orchestration engine combining NLP, MCP, and Bedrock."""
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file before anything else
env_paths = [
    Path(__file__).parent / ".env",  # Script directory
    Path.cwd() / ".env",  # Current working directory
    Path.home() / ".env",  # Home directory
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path, override=True)
        break
else:
    # Fallback: try find_dotenv
    dotenv_file = find_dotenv(raise_error_if_not_found=False)
    if dotenv_file:
        load_dotenv(dotenv_file, override=True)

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from bedrock_client import BedrockClient
from mcp_client import MCPClient

# Get logger (will be configured by entry point)
logger = logging.getLogger(__name__)
console = Console()


class MobileAutomationOrchestrator:
    """Orchestrator for NLP-driven mobile automation using Bedrock + Appium MCP."""
    
    def __init__(
        self,
        platform: str = "ios",
        bedrock_region: str = "us-east-1",
        debug: bool = False
    ):
        """Initialize orchestrator."""
        self.platform = platform
        self.debug = debug
        
        # Initialize clients
        logger.info("Initializing Bedrock client...")
        bedrock_region = os.getenv("AWS_REGION", bedrock_region)
        bedrock_model_id = os.getenv("BEDROCK_MODEL_ID")
        bedrock_anthropic_version = os.getenv("BEDROCK_ANTHROPIC_VERSION")
        
        # Validate required configuration
        if not bedrock_model_id:
            raise ValueError(
                "BEDROCK_MODEL_ID environment variable is not set. "
                "Please set it before initializing the orchestrator. "
                "Example: export BEDROCK_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0"
            )
        
        self.bedrock = BedrockClient(
            region=bedrock_region,
            model_id=bedrock_model_id,
            anthropic_version=bedrock_anthropic_version
        )
        
        logger.info("Initializing MCP client...")
        self.mcp = MCPClient()
        
        # State tracking
        self.session_active = False
        self.current_session_id = None
        self.execution_traces = []
        self.executed_actions = []
        
        logger.info(f"✓ Orchestrator initialized: platform={platform}, debug={debug}")
    
    def execute_prompt(
        self,
        prompt: str,
        device_info: Optional[Dict[str, Any]] = None,
        auto_session: bool = True,
        capabilities: Optional[Dict[str, Any]] = None,
        execution_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Execute a natural language prompt on the mobile device.
        
        Args:
            prompt: Natural language instruction (e.g., "Click the login button and take a screenshot")
            device_info: Device information (platform, device_name, bundle_id, etc.)
            auto_session: Automatically create session if needed
            capabilities: Custom Appium capabilities
        
        Returns:
            Execution result with status, actions executed, and traces
        """
        
        start_time = time.time()
        result = {
            "status": "success",
            "prompt": prompt,
            "platform": self.platform,
            "actions_executed": [],
            "execution_traces": [],
            "screenshots": [],
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Step 1: Initialize if needed
            if not self.session_active and auto_session:
                logger.info("Creating new automation session...")
                session_result = self._create_session(device_info or {}, capabilities)
                if session_result.get("status") != "success":
                    return {
                        **result,
                        "status": "error",
                        "error": f"Failed to create session: {session_result.get('error', 'Unknown error')}"
                    }
            
            # Step 2: Get current page state
            logger.info("Capturing current page state...")
            page_source = self._get_page_state()
            
            # Step 3: Ask Bedrock to interpret the prompt
            logger.info("")
            
            # Create request panel
            request_text = f"[bold cyan]🤖 Asking Bedrock to interpret prompt[/bold cyan]\n\n[yellow]{prompt[:100]}{'...' if len(prompt) > 100 else ''}[/yellow]"
            console.print(Panel(request_text, border_style="cyan", expand=False))
            
            # Use incoming execution_history or initialize new one
            if execution_history is None:
                execution_history = []
            else:
                # Log that we're using prior execution context
                logger.info(f"  📜 Using execution history from {len(execution_history)} prior actions")
            
            interpretation = self.bedrock.interpret_prompt(
                prompt=prompt,
                platform=self.platform,
                device_info=device_info or {},
                page_source=page_source,
                execution_history=execution_history if execution_history else None
            )
            
            if interpretation.get("status") != "success":
                return {
                    **result,
                    "status": "error",
                    "error": f"Bedrock interpretation failed: {interpretation.get('error', 'Unknown error')}"
                }
            
            actions = interpretation.get("actions", [])
            
            # Step 4: Execute actions with smart re-prompting for context
            found_elements = {}  # Track found element UUIDs
            i = 0
            while i < len(actions):
                action = actions[i]
                logger.debug(f"\n[{i+1}/{len(actions)}] Executing: {action.get('tool', 'unknown')}")
                logger.debug(f"  Reasoning: {action.get('reasoning', 'N/A')}")
                
                # Validate action
                if not self.bedrock.validate_action(action):
                    logger.warning(f"  ✗ Invalid tool: {action.get('tool')}, skipping")
                    i += 1
                    continue
                
                # Execute action with retry logic for failures
                action_result = None
                retry_count = 0
                max_retries = 3  # Try up to 3 strategies (primary + 2 fallbacks)
                strategy_attempts = []  # Track what strategies we tried
                
                while retry_count <= max_retries:
                    try:
                        # Log current attempt
                        current_strategy = action.get("params", {}).get("strategy", "unknown")
                        current_selector = action.get("params", {}).get("selector", "")[:50]  # Truncate for logging
                        
                        if retry_count == 0:
                            logger.debug(f"  📌 Attempt 1: Using {current_strategy} strategy")
                            logger.debug(f"     Selector: {current_selector}...")
                        else:
                            logger.debug(f"  🔄 Attempt {retry_count + 1}: FALLBACK - Using {current_strategy} strategy")
                            logger.debug(f"     Selector: {current_selector}...")
                        
                        action_result = self._execute_action(action)
                        strategy_attempts.append({
                            'attempt': retry_count + 1,
                            'strategy': current_strategy,
                            'selector': current_selector,
                            'status': action_result.get("status")
                        })
                        
                        # Check if action failed and is a find_element
                        if (action_result.get("status") in ["warning", "error"] and 
                            action.get("tool") == "appium_find_element" and 
                            retry_count < max_retries):
                            
                            error_msg = action_result.get('message', 'Found 0 elements')
                            logger.warning(f"  ❌ Attempt {retry_count + 1} FAILED: {error_msg}")
                            logger.debug(f"  🔄 AUTO-HEALING: Triggering fallback strategy #{retry_count + 1}...")
                            
                            # Build fallback retry prompt
                            strategy_num = retry_count + 1
                            strategies = [
                                "accessibility id (exact element name or label)",
                                "-ios predicate string (search by element type and visible text)",
                                "xpath with alternative criteria or label-based selectors"
                            ]
                            fallback_strategy = strategies[retry_count] if retry_count < len(strategies) else "alternative element locators"
                            
                            retry_prompt = (
                                "ORIGINAL PROMPT: " + prompt + "\n\n"
                                f"SELF-HEALING AUTO-RETRY (Strategy Attempt #{strategy_num + 1}):\n"
                                f"Previous attempts failed:\n"
                                f"- Attempt {retry_count}: {current_strategy} with selector '{action.get('params', {}).get('selector', '')}' → {error_msg}\n\n"
                                f"NEXT STRATEGY TO TRY: {fallback_strategy}\n"
                                f"Generate a NEW find_element action with this alternative strategy.\n"
                                f"Include 'reason_for_fallback' in reasoning field."
                            )
                            
                            logger.debug(f"     Re-prompting Bedrock with fallback: {fallback_strategy}")
                            
                            # Re-interpret with fallback instruction
                            new_interpretation = self.bedrock.interpret_prompt(
                                prompt=retry_prompt,
                                platform=self.platform,
                                device_info=device_info or {},
                                page_source=page_source,
                                execution_history=execution_history
                            )
                            
                            if new_interpretation.get("status") == "success":
                                new_actions = new_interpretation.get("actions", [])
                                if new_actions and new_actions[0]:
                                    action = new_actions[0]  # Update action with fallback
                                    new_strategy = action.get("params", {}).get("strategy", "unknown")
                                    logger.debug(f"  ✓ Generated new action with strategy: {new_strategy}")
                                    retry_count += 1
                                    continue  # Retry with new strategy
                            else:
                                logger.error(f"  ✗ Bedrock re-interpretation failed: {new_interpretation.get('error', 'Unknown error')}")
                            
                            retry_count += 1
                        else:
                            # Action succeeded or is not a find_element - continue normally
                            if action_result.get("status") == "success" and retry_count > 0:
                                logger.debug(f"  ✅ SUCCESS on attempt {retry_count + 1} (after {retry_count} fallback(s))")
                            break
                        
                    except Exception as e:
                        logger.error(f"  ✗ Execution error on attempt {retry_count + 1}: {e}")
                        strategy_attempts.append({
                            'attempt': retry_count + 1,
                            'strategy': action.get("params", {}).get("strategy", "unknown"),
                            'status': 'error',
                            'error': str(e)
                        })
                        retry_count += 1
                        if retry_count > max_retries:
                            action_result = {
                                "status": "error",
                                "result": str(e)
                            }
                            break
                
                # Log summary of strategy attempts if we had multiple tries
                if len(strategy_attempts) > 1:
                    logger.debug(f"  📊 Strategy Summary: {len(strategy_attempts)} attempt(s)")
                    for attempt in strategy_attempts:
                        logger.debug(f"     - Attempt {attempt['attempt']}: {attempt['strategy']} → {attempt['status']}")
                
                # Track execution with full result for context
                try:
                    # Smart element UUID injection: if action has no valid UUID but we have a found element,
                    # Use the most recent found element with matching description
                    if (action.get("tool") in ["appium_click", "appium_set_value", "appium_double_tap", "appium_long_press"] 
                        and action_result and action_result.get("status") in ["error", "warning"]):
                        
                        # Check if error is about missing element UUID
                        error_msg = action_result.get("message", "").lower()
                        if "uuid" in error_msg or "element" in error_msg or action.get("params", {}).get("elementUUID") is None:
                            # Try to find recently found element that matches the prompt context
                            for hist_action in reversed(execution_history):
                                if (hist_action.get("tool") == "appium_find_element" 
                                    and hist_action.get("status") == "success" 
                                    and hist_action.get("result", {}).get("elementUUID")):
                                    
                                    # Check if selector/strategy mentions the same element we're trying to interact with
                                    hist_selector = hist_action.get("params", {}).get("selector", "").lower()
                                    action_reasoning = action.get("reasoning", "").lower()
                                    
                                    if any(keyword in hist_selector or keyword in action_reasoning 
                                          for keyword in ["sign in", "signin", "button"]):
                                        
                                        logger.info(f"  🔧 Auto-injecting element UUID from recent find: {hist_action.get('result', {}).get('elementUUID')}")
                                        action["params"]["elementUUID"] = hist_action.get("result", {}).get("elementUUID")
                                        
                                        # Re-execute with the injected UUID
                                        logger.info(f"  ↻ Retrying {action.get('tool')} with found element UUID")
                                        action_result = self._execute_action(action)
                                        break
                    
                    executed_action = {
                        "tool": action.get("tool"),
                        "params": action.get("params"),
                        "status": action_result.get("status", "unknown"),
                        "reasoning": action.get("reasoning"),
                        "result": action_result  # Include full result for Bedrock context
                    }
                    result["actions_executed"].append(executed_action)
                    execution_history.append(executed_action)
                    
                    # If find succeeded, cache the element UUID
                    if action.get("tool") == "appium_find_element" and action_result.get("status") == "success":
                        if action_result.get("elementUUID"):
                            found_elements[len(actions)] = action_result.get("elementUUID")
                            logger.debug(f"  Found element cached: {action_result.get('elementUUID')}")
                            
                            # Check if next action uses placeholder UUID or missing UUID - if so, re-ask Bedrock with context
                            if i + 1 < len(actions):
                                next_action = actions[i + 1]
                                next_params = next_action.get("params", {})
                                next_uuid = next_params.get("elementUUID")
                                
                                # Check if next action references placeholder UUIDs or has no UUID
                                has_placeholder = (
                                    next_uuid is None or 
                                    next_uuid == "" or
                                    (isinstance(next_uuid, str) and ("PLACEHOLDER" in next_uuid or "ELEMENT_UUID" in next_uuid))
                                )
                                
                                if has_placeholder and next_action.get("tool") in ["appium_click", "appium_set_value", "appium_double_tap", "appium_long_press"]:
                                    logger.debug(f"  Detected invalid/missing UUID in next action - re-asking Bedrock with found element context")
                                    
                                    # Build updated prompt with the found element
                                    updated_prompt = f"Use the element that was just found (UUID: {action_result.get('elementUUID')}) to perform the next action. " + prompt
                                    
                                    # Re-interpret with execution history
                                    re_interpretation = self.bedrock.interpret_prompt(
                                        prompt=updated_prompt,
                                        platform=self.platform,
                                        device_info=device_info or {},
                                        page_source=page_source,
                                        execution_history=execution_history
                                    )
                                    
                                    if re_interpretation.get("status") == "success":
                                        new_actions = re_interpretation.get("actions", [])
                                        if new_actions:
                                            # Replace remaining actions with new ones
                                            actions = actions[:i+1] + new_actions
                                            logger.debug(f"  Re-generated {len(new_actions)} actions with proper UUID context")
                    
                    # Handle screenshots
                    if action.get("tool") == "appium_screenshot" and action_result.get("screenshot"):
                        result["screenshots"].append({
                            "timestamp": datetime.now().isoformat(),
                            "tool": action.get("tool"),
                            "data": action_result.get("screenshot")[:100]  # Truncate for logging
                        })
                    
                    logger.debug(f"  \u2713 Completed: {action_result.get('status', 'success')}")
                    i += 1
                    
                except Exception as e:
                    logger.error(f"  ✗ Action failed: {e}")
                    result["actions_executed"].append({
                        "tool": action.get("tool"),
                        "params": action.get("params"),
                        "status": "error",
                        "error": str(e)
                    })
                    i += 1
            
            result["execution_time_seconds"] = time.time() - start_time
            console.print()
            
            # Create completion panel
            completion_text = Text(f"✓ PROMPT EXECUTION COMPLETED in {result['execution_time_seconds']:.2f}s", style="bold white on green")
            console.print(Panel(completion_text, border_style="green", expand=False))
            return result
            
        except Exception as e:
            logger.error(f"✗ Execution failed: {e}")
            return {
                **result,
                "status": "error",
                "error": str(e),
                "execution_time_seconds": time.time() - start_time
            }
    
    def execute_workflow(
        self,
        prompts: List[str],
        device_info: Optional[Dict[str, Any]] = None,
        capabilities: Optional[Dict[str, Any]] = None,
        stop_on_error: bool = False
    ) -> Dict[str, Any]:
        """
        Execute multiple prompts in sequence.
        
        Args:
            prompts: List of natural language prompts
            device_info: Device information
            capabilities: Appium capabilities
            stop_on_error: Stop workflow on first error
        
        Returns:
            Workflow execution result
        """
        
        workflow_start = time.time()
        results = []
        workflow_execution_history = []  # Accumulate across all steps
        
        logger.info(f"Starting workflow with {len(prompts)} steps")
        
        try:
            # Create session once at the beginning
            if not self.session_active:
                logger.info("Creating session for workflow...")
                session_result = self._create_session(device_info or {}, capabilities)
                if session_result.get("status") != "success":
                    return {
                        "status": "error",
                        "error": f"Failed to create session: {session_result.get('error')}"
                    }
            
            # Execute each prompt
            for i, prompt in enumerate(prompts):
                logger.info(f"\n[Step {i+1}/{len(prompts)}] {prompt}")
                
                # Pass accumulated execution history to this step
                result = self.execute_prompt(
                    prompt=prompt,
                    device_info=device_info,
                    auto_session=False,  # Session already created
                    execution_history=workflow_execution_history  # Pass prior execution history
                )
                
                # Accumulate actions from this step into workflow history
                for action in result.get("actions_executed", []):
                    workflow_execution_history.append(action)
                
                results.append(result)
                
                if result.get("status") != "success" and stop_on_error:
                    logger.error(f"Workflow stopping due to error at step {i+1}")
                    break
                
                # Small delay between prompts
                time.sleep(0.5)
            
            return {
                "status": "success",
                "workflow_steps": len(prompts),
                "steps_completed": len(results),
                "results": results,
                "device_info": device_info or {},
                "platform": self.platform,
                "total_time_seconds": time.time() - workflow_start
            }
            
        finally:
            # Cleanup session
            self._delete_session()
    
    def generate_test_script(
        self,
        test_name: str,
        actions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate test script from executed actions."""
        try:
            logger.info(f"Generating test script: {test_name}")
            result = self.mcp.call_tool("appium_generate_tests", {
                "testName": test_name,
                "actions": actions
            })
            
            if result.get("status") == "success":
                logger.info(f"✓ Test script generated: {test_name}")
            
            return result
            
        except Exception as e:
            logger.error(f"✗ Failed to generate test script: {e}")
            return {"status": "error", "error": str(e)}
    
    # Private helper methods
    
    def _create_session(
        self,
        device_info: Dict[str, Any],
        capabilities: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create Appium session."""
        try:
            # Select platform
            platform_result = self.mcp.select_platform(self.platform)
            if platform_result.get("status") != "success":
                return platform_result
            
            # Create default or custom capabilities
            if capabilities:
                caps = capabilities
            else:
                caps = self._get_default_capabilities(device_info)
            
            # Create session
            session_result = self.mcp.create_session(caps)
            
            if session_result.get("status") == "success":
                self.session_active = True
                self.current_session_id = session_result.get("session_id")
                logger.info(f"✓ Session created: {self.current_session_id}")
            
            return session_result
            
        except Exception as e:
            logger.error(f"✗ Session creation failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def _delete_session(self) -> Dict[str, Any]:
        """Delete Appium session."""
        try:
            if self.session_active:
                result = self.mcp.delete_session()
                self.session_active = False
                self.current_session_id = None
                logger.info("✓ Session deleted")
                return result
            return {"status": "success"}
        except Exception as e:
            logger.error(f"✗ Session deletion failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def _get_page_state(self) -> str:
        """Get current page state."""
        try:
            result = self.mcp.get_page_source()
            if result.get("status") == "success":
                source = result.get("source", "")
                # Return first 1000 chars for context
                return source[:1000] if source else ""
            return ""
        except Exception as e:
            logger.warning(f"Could not get page state: {e}")
            return ""
    
    def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single MCP action."""
        tool_name = action.get("tool")
        params = action.get("params", {})
        
        try:
            result = self.mcp.call_tool(tool_name, params)
            return result
        except Exception as e:
            logger.error(f"Failed to execute {tool_name}: {e}")
            return {"status": "error", "error": str(e)}
    
    def _get_default_capabilities(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate default Appium capabilities based on platform and device info."""
        if self.platform == "ios":
            return {
                "platformName": "iOS",
                "platformVersion": device_info.get("platform_version", "18.0"),
                "appium:automationName": "XCUITest",
                "appium:deviceName": device_info.get("device_name", "iPhone Simulator"),
                "appium:bundleId": device_info.get("bundle_id", "com.example.app")
            }
        else:  # android
            return {
                "platformName": "Android",
                "platformVersion": device_info.get("platform_version", "13.0"),
                "appium:automationName": "UiAutomator2",
                "appium:deviceId": device_info.get("device_id", "emulator-5554"),
                "appium:appPackage": device_info.get("app_package", "com.example.app"),
                "appium:appActivity": device_info.get("app_activity", ".MainActivity")
            }
    
    def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up...")
        self._delete_session()
        logger.info("✓ Cleanup completed")
