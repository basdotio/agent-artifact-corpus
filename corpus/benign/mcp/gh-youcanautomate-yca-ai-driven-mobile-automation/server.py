"""Main MCP Server for Appium automation - Python implementation."""
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file
# Try multiple locations: script dir, cwd, then home
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

from mcp.server import Server, stdio_server_params
from mcp.types import Tool, TextContent, ToolResult
import logger
import session_store
import tools_session
import tools_interactions
import tools_navigations
import tools_app_management
import tools_context
import tools_ios
import tools_test_generation
import tools_documentation

# Initialize MCP server
server = Server("appium-mcp-python")


def create_tool(
    name: str,
    description: str,
    input_schema: Dict[str, Any],
    func
) -> Tool:
    """Create a tool definition."""
    return Tool(
        name=name,
        description=description,
        inputSchema=input_schema,
    )


async def handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Handle tool calls and route to appropriate handler."""
    logger.info(f"[TOOL START] {tool_name}", arguments)
    
    try:
        result = None
        
        # Session management tools
        if tool_name == "select_platform":
            result = tools_session.select_platform(arguments.get('platform'))
        elif tool_name == "select_device":
            result = tools_session.select_device(
                arguments.get('device_id'),
                arguments.get('device_name')
            )
        elif tool_name == "create_session":
            result = tools_session.create_session(
                arguments.get('capabilities', {}),
                arguments.get('appium_server_url', 'http://localhost:4723')
            )
        elif tool_name == "delete_session":
            result = tools_session.delete_session()
        elif tool_name == "open_notifications":
            result = tools_session.open_notifications()
        
        # Interaction tools
        elif tool_name == "appium_click":
            result = tools_interactions.appium_click(arguments.get('elementUUID'))
        elif tool_name == "appium_find_element":
            result = tools_interactions.appium_find_element(
                arguments.get('strategy'),
                arguments.get('selector')
            )
        elif tool_name == "appium_double_tap":
            result = tools_interactions.appium_double_tap(arguments.get('elementUUID'))
        elif tool_name == "appium_long_press":
            result = tools_interactions.appium_long_press(
                arguments.get('elementUUID'),
                arguments.get('duration', 2000)
            )
        elif tool_name == "appium_drag_and_drop":
            result = tools_interactions.appium_drag_and_drop(
                arguments.get('sourceUUID'),
                arguments.get('targetUUID')
            )
        elif tool_name == "appium_press_key":
            result = tools_interactions.appium_press_key(
                arguments.get('keyCode'),
                arguments.get('metaState')
            )
        elif tool_name == "appium_set_value":
            result = tools_interactions.appium_set_value(
                arguments.get('elementUUID'),
                arguments.get('value')
            )
        elif tool_name == "appium_get_text":
            result = tools_interactions.appium_get_text(arguments.get('elementUUID'))
        elif tool_name == "appium_get_active_element":
            result = tools_interactions.appium_get_active_element()
        elif tool_name == "appium_get_page_source":
            result = tools_interactions.appium_get_page_source()
        elif tool_name == "appium_screenshot":
            result = tools_interactions.appium_screenshot(arguments.get('filename'))
        elif tool_name == "appium_element_screenshot":
            result = tools_interactions.appium_element_screenshot(arguments.get('elementUUID'))
        elif tool_name == "appium_get_orientation":
            result = tools_interactions.appium_get_orientation()
        elif tool_name == "appium_set_orientation":
            result = tools_interactions.appium_set_orientation(arguments.get('orientation'))
        elif tool_name == "appium_handle_alert":
            result = tools_interactions.appium_handle_alert(arguments.get('action'))
        
        # Navigation tools
        elif tool_name == "appium_scroll":
            result = tools_navigations.appium_scroll(
                arguments.get('direction'),
                arguments.get('distance', 500)
            )
        elif tool_name == "appium_scroll_to_element":
            result = tools_navigations.appium_scroll_to_element(
                arguments.get('elementUUID'),
                arguments.get('direction', 'down'),
                arguments.get('maxSwipes', 5)
            )
        elif tool_name == "appium_swipe":
            result = tools_navigations.appium_swipe(
                arguments.get('startX'),
                arguments.get('startY'),
                arguments.get('endX'),
                arguments.get('endY'),
                arguments.get('duration', 500)
            )
        
        # App management tools
        elif tool_name == "appium_activate_app":
            result = tools_app_management.appium_activate_app(arguments.get('appId'))
        elif tool_name == "appium_install_app":
            result = tools_app_management.appium_install_app(arguments.get('appPath'))
        elif tool_name == "appium_uninstall_app":
            result = tools_app_management.appium_uninstall_app(arguments.get('appId'))
        elif tool_name == "appium_terminate_app":
            result = tools_app_management.appium_terminate_app(arguments.get('appId'))
        elif tool_name == "appium_list_apps":
            result = tools_app_management.appium_list_apps()
        elif tool_name == "appium_is_app_installed":
            result = tools_app_management.appium_is_app_installed(arguments.get('appId'))
        elif tool_name == "appium_deep_link":
            result = tools_app_management.appium_deep_link(arguments.get('url'))
        
        # Context tools
        elif tool_name == "appium_get_contexts":
            result = tools_context.appium_get_contexts()
        elif tool_name == "appium_switch_context":
            result = tools_context.appium_switch_context(arguments.get('contextName'))
        
        # iOS tools
        elif tool_name == "appium_boot_simulator":
            result = tools_ios.appium_boot_simulator(arguments.get('simulatorUDID'))
        elif tool_name == "appium_setup_wda":
            result = tools_ios.appium_setup_wda(
                arguments.get('simulatorUDID'),
                arguments.get('wdaBundleId', 'com.facebook.WebDriverAgentRunner')
            )
        elif tool_name == "appium_install_wda":
            result = tools_ios.appium_install_wda(
                arguments.get('wdaPath'),
                arguments.get('simulatorUDID')
            )
        
        # Test generation tools
        elif tool_name == "appium_generate_locators":
            result = tools_test_generation.appium_generate_locators(
                arguments.get('strategy', 'all')
            )
        elif tool_name == "appium_generate_tests":
            result = tools_test_generation.appium_generate_tests(
                arguments.get('testName'),
                arguments.get('actions', [])
            )
        
        # Documentation tools
        elif tool_name == "appium_answer_appium":
            result = tools_documentation.appium_answer_appium(arguments.get('question'))
        
        else:
            result = {
                'status': 'error',
                'message': f'Unknown tool: {tool_name}'
            }
        
        logger.info(f"[TOOL END] {tool_name}")
        return json.dumps(result)
    
    except Exception as e:
        logger.error(f"[TOOL ERROR] {tool_name}: {str(e)}")
        return json.dumps({
            'status': 'error',
            'message': f'Error executing tool: {str(e)}'
        })


@server.call_tool()
async def call_tool(tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
    """Handle tool calls from clients."""
    output = await handle_tool_call(tool_name, arguments)
    return ToolResult(content=[TextContent(type="text", text=output)])


def register_tools() -> None:
    """Register all MCP tools with the server."""
    
    # Session management tools
    server.add_tool(
        create_tool(
            "select_platform",
            "Select the target platform (iOS or Android)",
            {"type": "object", "properties": {"platform": {"type": "string", "enum": ["ios", "android"]}}, "required": ["platform"]},
            tools_session.select_platform
        )
    )
    
    server.add_tool(
        create_tool(
            "select_device",
            "Select target device for automation",
            {"type": "object", "properties": {"device_id": {"type": "string"}, "device_name": {"type": "string"}}, "required": ["device_id"]},
            tools_session.select_device
        )
    )
    
    server.add_tool(
        create_tool(
            "create_session",
            "Create a new Appium session",
            {"type": "object", "properties": {"capabilities": {"type": "object"}, "appium_server_url": {"type": "string"}}, "required": ["capabilities"]},
            tools_session.create_session
        )
    )
    
    server.add_tool(
        create_tool(
            "delete_session",
            "Delete the current Appium session",
            {"type": "object", "properties": {}},
            tools_session.delete_session
        )
    )
    
    server.add_tool(
        create_tool(
            "open_notifications",
            "Open the notifications panel",
            {"type": "object", "properties": {}},
            tools_session.open_notifications
        )
    )
    
    # Interaction tools
    server.add_tool(
        create_tool(
            "appium_click",
            "Click on an element",
            {"type": "object", "properties": {"elementUUID": {"type": "string"}}, "required": ["elementUUID"]},
            tools_interactions.appium_click
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_find_element",
            "Find element by strategy and selector",
            {"type": "object", "properties": {"strategy": {"type": "string"}, "selector": {"type": "string"}}, "required": ["strategy", "selector"]},
            tools_interactions.appium_find_element
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_screenshot",
            "Take a screenshot",
            {"type": "object", "properties": {"filename": {"type": "string"}}},
            tools_interactions.appium_screenshot
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_get_page_source",
            "Get page source",
            {"type": "object", "properties": {}},
            tools_interactions.appium_get_page_source
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_set_value",
            "Set value on element",
            {"type": "object", "properties": {"elementUUID": {"type": "string"}, "value": {"type": "string"}}, "required": ["elementUUID", "value"]},
            tools_interactions.appium_set_value
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_get_text",
            "Get text from element",
            {"type": "object", "properties": {"elementUUID": {"type": "string"}}, "required": ["elementUUID"]},
            tools_interactions.appium_get_text
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_double_tap",
            "Double tap on element",
            {"type": "object", "properties": {"elementUUID": {"type": "string"}}, "required": ["elementUUID"]},
            tools_interactions.appium_double_tap
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_long_press",
            "Long press on element",
            {"type": "object", "properties": {"elementUUID": {"type": "string"}, "duration": {"type": "integer"}}, "required": ["elementUUID"]},
            tools_interactions.appium_long_press
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_drag_and_drop",
            "Drag element to target",
            {"type": "object", "properties": {"sourceUUID": {"type": "string"}, "targetUUID": {"type": "string"}}, "required": ["sourceUUID", "targetUUID"]},
            tools_interactions.appium_drag_and_drop
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_press_key",
            "Press a key",
            {"type": "object", "properties": {"keyCode": {"type": "string"}, "metaState": {"type": "integer"}}, "required": ["keyCode"]},
            tools_interactions.appium_press_key
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_get_active_element",
            "Get active element",
            {"type": "object", "properties": {}},
            tools_interactions.appium_get_active_element
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_element_screenshot",
            "Take element screenshot",
            {"type": "object", "properties": {"elementUUID": {"type": "string"}}, "required": ["elementUUID"]},
            tools_interactions.appium_element_screenshot
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_get_orientation",
            "Get device orientation",
            {"type": "object", "properties": {}},
            tools_interactions.appium_get_orientation
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_set_orientation",
            "Set device orientation",
            {"type": "object", "properties": {"orientation": {"type": "string"}}, "required": ["orientation"]},
            tools_interactions.appium_set_orientation
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_handle_alert",
            "Handle alert dialog",
            {"type": "object", "properties": {"action": {"type": "string"}}, "required": ["action"]},
            tools_interactions.appium_handle_alert
        )
    )
    
    # Navigation tools
    server.add_tool(
        create_tool(
            "appium_scroll",
            "Scroll in direction",
            {"type": "object", "properties": {"direction": {"type": "string"}, "distance": {"type": "integer"}}, "required": ["direction"]},
            tools_navigations.appium_scroll
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_scroll_to_element",
            "Scroll to element",
            {"type": "object", "properties": {"elementUUID": {"type": "string"}, "direction": {"type": "string"}, "maxSwipes": {"type": "integer"}}, "required": ["elementUUID"]},
            tools_navigations.appium_scroll_to_element
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_swipe",
            "Perform swipe gesture",
            {"type": "object", "properties": {"startX": {"type": "integer"}, "startY": {"type": "integer"}, "endX": {"type": "integer"}, "endY": {"type": "integer"}}, "required": ["startX", "startY", "endX", "endY"]},
            tools_navigations.appium_swipe
        )
    )
    
    # App management tools
    server.add_tool(
        create_tool(
            "appium_activate_app",
            "Activate installed app",
            {"type": "object", "properties": {"appId": {"type": "string"}}, "required": ["appId"]},
            tools_app_management.appium_activate_app
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_install_app",
            "Install app from path",
            {"type": "object", "properties": {"appPath": {"type": "string"}}, "required": ["appPath"]},
            tools_app_management.appium_install_app
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_uninstall_app",
            "Uninstall app",
            {"type": "object", "properties": {"appId": {"type": "string"}}, "required": ["appId"]},
            tools_app_management.appium_uninstall_app
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_terminate_app",
            "Terminate running app",
            {"type": "object", "properties": {"appId": {"type": "string"}}, "required": ["appId"]},
            tools_app_management.appium_terminate_app
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_list_apps",
            "List installed apps",
            {"type": "object", "properties": {}},
            tools_app_management.appium_list_apps
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_is_app_installed",
            "Check if app is installed",
            {"type": "object", "properties": {"appId": {"type": "string"}}, "required": ["appId"]},
            tools_app_management.appium_is_app_installed
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_deep_link",
            "Open deep link",
            {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
            tools_app_management.appium_deep_link
        )
    )
    
    # Context tools
    server.add_tool(
        create_tool(
            "appium_get_contexts",
            "Get available contexts",
            {"type": "object", "properties": {}},
            tools_context.appium_get_contexts
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_switch_context",
            "Switch to context",
            {"type": "object", "properties": {"contextName": {"type": "string"}}, "required": ["contextName"]},
            tools_context.appium_switch_context
        )
    )
    
    # iOS tools
    server.add_tool(
        create_tool(
            "appium_boot_simulator",
            "Boot iOS simulator",
            {"type": "object", "properties": {"simulatorUDID": {"type": "string"}}, "required": ["simulatorUDID"]},
            tools_ios.appium_boot_simulator
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_setup_wda",
            "Setup WebDriverAgent",
            {"type": "object", "properties": {"simulatorUDID": {"type": "string"}, "wdaBundleId": {"type": "string"}}, "required": ["simulatorUDID"]},
            tools_ios.appium_setup_wda
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_install_wda",
            "Install WebDriverAgent",
            {"type": "object", "properties": {"wdaPath": {"type": "string"}, "simulatorUDID": {"type": "string"}}, "required": ["wdaPath", "simulatorUDID"]},
            tools_ios.appium_install_wda
        )
    )
    
    # Test generation tools
    server.add_tool(
        create_tool(
            "appium_generate_locators",
            "Generate locators for page",
            {"type": "object", "properties": {"strategy": {"type": "string"}}},
            tools_test_generation.appium_generate_locators
        )
    )
    
    server.add_tool(
        create_tool(
            "appium_generate_tests",
            "Generate test script",
            {"type": "object", "properties": {"testName": {"type": "string"}, "actions": {"type": "array"}}, "required": ["testName", "actions"]},
            tools_test_generation.appium_generate_tests
        )
    )
    
    # Documentation tools  
    server.add_tool(
        create_tool(
            "appium_answer_appium",
            "Answer questions about Appium",
            {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]},
            tools_documentation.appium_answer_appium
        )
    )
    
    logger.info("All tools registered successfully")


async def main():
    """Main entry point for MCP server."""
    logger.info("Starting Appium MCP Python server")
    
    # Register tools
    register_tools()
    
    # Run server
    async with stdio_server_params() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            stdio_server_params.InitializationOptions()
        )


if __name__ == "__main__":
    asyncio.run(main())
