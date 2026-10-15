"""Direct MCP Tool Executor - No subprocess needed."""
import logging
from typing import Dict, Any, Optional

# Import all tool modules directly
from tools_session import (
    select_platform, select_device, create_session, delete_session, open_notifications
)
from tools_interactions import (
    appium_find_element, appium_click, appium_double_tap, appium_long_press,
    appium_drag_and_drop, appium_press_key, appium_set_value, appium_get_text,
    appium_get_active_element, appium_screenshot, appium_element_screenshot,
    appium_get_page_source, appium_get_orientation, appium_set_orientation, appium_handle_alert
)
from tools_navigations import (
    appium_scroll, appium_scroll_to_element, appium_swipe
)
from tools_app_management import (
    appium_activate_app, appium_install_app, appium_uninstall_app, appium_terminate_app,
    appium_list_apps, appium_is_app_installed, appium_deep_link
)
from tools_context import (
    appium_get_contexts, appium_switch_context
)
from tools_ios import (
    appium_boot_simulator, appium_setup_wda, appium_install_wda
)
from tools_test_generation import (
    appium_generate_locators, appium_generate_tests
)
from tools_documentation import (
    appium_answer_appium
)

logger = logging.getLogger(__name__)


class MCPClient:
    """Direct MCP tool executor - calls tools directly without subprocess."""
    
    def __init__(self):
        """Initialize MCP client."""
        # Tool registry - maps tool names to functions
        self.tools = {
            # Session management (5)
            "select_platform": select_platform,
            "select_device": select_device,
            "create_session": create_session,
            "delete_session": delete_session,
            "open_notifications": open_notifications,
            
            # Element interactions (16)
            "appium_find_element": appium_find_element,
            "appium_click": appium_click,
            "appium_double_tap": appium_double_tap,
            "appium_long_press": appium_long_press,
            "appium_drag_and_drop": appium_drag_and_drop,
            "appium_press_key": appium_press_key,
            "appium_set_value": appium_set_value,
            "appium_get_text": appium_get_text,
            "appium_get_active_element": appium_get_active_element,
            "appium_screenshot": appium_screenshot,
            "appium_element_screenshot": appium_element_screenshot,
            "appium_get_page_source": appium_get_page_source,
            "appium_get_orientation": appium_get_orientation,
            "appium_set_orientation": appium_set_orientation,
            "appium_handle_alert": appium_handle_alert,
            
            # Navigation (3)
            "appium_scroll": appium_scroll,
            "appium_scroll_to_element": appium_scroll_to_element,
            "appium_swipe": appium_swipe,
            
            # App management (7)
            "appium_activate_app": appium_activate_app,
            "appium_install_app": appium_install_app,
            "appium_uninstall_app": appium_uninstall_app,
            "appium_terminate_app": appium_terminate_app,
            "appium_list_apps": appium_list_apps,
            "appium_is_app_installed": appium_is_app_installed,
            "appium_deep_link": appium_deep_link,
            
            # Context (2)
            "appium_get_contexts": appium_get_contexts,
            "appium_switch_context": appium_switch_context,
            
            # iOS (3)
            "appium_boot_simulator": appium_boot_simulator,
            "appium_setup_wda": appium_setup_wda,
            "appium_install_wda": appium_install_wda,
            
            # Test generation (2)
            "appium_generate_locators": appium_generate_locators,
            "appium_generate_tests": appium_generate_tests,
            
            # Documentation (1)
            "appium_answer_appium": appium_answer_appium
        }
        logger.info(f"✓ MCP Client initialized with {len(self.tools)} tools")
    
    def call_tool(self, tool_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call MCP tool directly."""
        if params is None:
            params = {}
        
        try:
            logger.debug(f"Calling tool: {tool_name} with params: {params}")
            
            # Get tool function
            if tool_name not in self.tools:
                logger.error(f"✗ Unknown tool: {tool_name}")
                return {"status": "error", "error": f"Tool not found: {tool_name}"}
            
            tool_func = self.tools[tool_name]
            
            # Convert camelCase parameter names to snake_case for Python functions
            converted_params = {}
            for key, value in params.items():
                # Convert camelCase to snake_case
                # e.g. elementUUID -> element_uuid, sourceUUID -> source_uuid
                snake_case_key = self._camel_to_snake(key)
                converted_params[snake_case_key] = value
            
            logger.debug(f"Converted params: {converted_params}")
            
            # Call tool directly
            result = tool_func(**converted_params)
            
            logger.info(f"✓ {tool_name} completed")
            return result
            
        except Exception as e:
            logger.error(f"✗ Tool call failed: {e}")
            return {"status": "error", "error": str(e)}
    
    @staticmethod
    def _camel_to_snake(name: str) -> str:
        """Convert camelCase to snake_case."""
        import re
        # Insert underscore before uppercase letters that follow lowercase letters
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        # Insert underscore before uppercase letters that follow lowercase or uppercase letters followed by lowercase
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    # Convenience methods for common tools
    
    def screenshot(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """Take screenshot."""
        params = {}
        if filename:
            params["filename"] = filename
        return self.call_tool("appium_screenshot", params)
    
    def find_element(self, strategy: str, selector: str) -> Dict[str, Any]:
        """Find element."""
        return self.call_tool("appium_find_element", {
            "strategy": strategy,
            "selector": selector
        })
    
    def click_element(self, element_id: str) -> Dict[str, Any]:
        """Click element."""
        return self.call_tool("appium_click", {"elementUUID": element_id})
    
    def set_value(self, element_id: str, value: str) -> Dict[str, Any]:
        """Set element value."""
        return self.call_tool("appium_set_value", {
            "elementUUID": element_id,
            "value": value
        })
    
    def get_text(self, element_id: str) -> Dict[str, Any]:
        """Get element text."""
        return self.call_tool("appium_get_text", {"elementUUID": element_id})
    
    def scroll(self, direction: str, distance: int = 500) -> Dict[str, Any]:
        """Scroll."""
        return self.call_tool("appium_scroll", {
            "direction": direction,
            "distance": distance
        })
    
    def get_page_source(self) -> Dict[str, Any]:
        """Get page source."""
        return self.call_tool("appium_get_page_source", {})
    
    def select_platform(self, platform: str) -> Dict[str, Any]:
        """Select target platform."""
        return self.call_tool("select_platform", {"platform": platform})
    
    def create_session(self, capabilities: Dict[str, Any]) -> Dict[str, Any]:
        """Create Appium session."""
        return self.call_tool("create_session", {"capabilities": capabilities})
    
    def delete_session(self) -> Dict[str, Any]:
        """Delete session."""
        return self.call_tool("delete_session", {})
