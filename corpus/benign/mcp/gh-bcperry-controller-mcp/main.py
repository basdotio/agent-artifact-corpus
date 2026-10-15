#!/usr/bin/env python3

import asyncio
import time
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

try:
    import vgamepad as vg
    VGAMEPAD_AVAILABLE = True
except Exception as e:
    VGAMEPAD_AVAILABLE = False
    VGAMEPAD_ERROR = str(e)

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel



class ControllerState(BaseModel):
    """Represents the current state of the Xbox controller"""
    left_stick_x: float = 0.0  # -1.0 to 1.0
    left_stick_y: float = 0.0  # -1.0 to 1.0
    right_stick_x: float = 0.0  # -1.0 to 1.0
    right_stick_y: float = 0.0  # -1.0 to 1.0
    left_trigger: float = 0.0  # 0.0 to 1.0
    right_trigger: float = 0.0  # 0.0 to 1.0
    buttons_pressed: Dict[str, bool] = {}


class XboxControllerEmulator:
    """Xbox controller emulator with fallback simulation mode"""
    
    def __init__(self):
        self.state = ControllerState()
        self.simulation_mode = not VGAMEPAD_AVAILABLE
        
        if not self.simulation_mode:
            try:
                self.gamepad = vg.VX360Gamepad()
            except Exception as e:
                print(f"Warning: Failed to initialize virtual gamepad: {e}")
                print("Falling back to simulation mode.")
                self.simulation_mode = True
                self.gamepad = None
        else:
            self.gamepad = None
            print(f"Warning: vgamepad not available: {VGAMEPAD_ERROR if VGAMEPAD_AVAILABLE else 'Module not found'}")
            print("Running in simulation mode - controller state will be tracked but no actual input will be sent.")
        
        self.button_map = {
            'A': 'XUSB_GAMEPAD_A',
            'B': 'XUSB_GAMEPAD_B', 
            'X': 'XUSB_GAMEPAD_X',
            'Y': 'XUSB_GAMEPAD_Y',
            'LB': 'XUSB_GAMEPAD_LEFT_SHOULDER',
            'RB': 'XUSB_GAMEPAD_RIGHT_SHOULDER',
            'BACK': 'XUSB_GAMEPAD_BACK',
            'START': 'XUSB_GAMEPAD_START',
            'LS': 'XUSB_GAMEPAD_LEFT_THUMB',
            'RS': 'XUSB_GAMEPAD_RIGHT_THUMB',
            'DPAD_UP': 'XUSB_GAMEPAD_DPAD_UP',
            'DPAD_DOWN': 'XUSB_GAMEPAD_DPAD_DOWN',
            'DPAD_LEFT': 'XUSB_GAMEPAD_DPAD_LEFT',
            'DPAD_RIGHT': 'XUSB_GAMEPAD_DPAD_RIGHT',
        }
        
        # Initialize button states
        for button in self.button_map.keys():
            self.state.buttons_pressed[button] = False
    
    def _log_action(self, action: str, details: str = ""):
        """Log controller actions for debugging/simulation"""
        mode_prefix = "[SIM]" if self.simulation_mode else "[HW]"
        print(f"{mode_prefix} {action}{f' - {details}' if details else ''}")
    
    def press_button(self, button: str) -> bool:
        """Press a button on the controller"""
        if button not in self.button_map:
            return False
            
        self.state.buttons_pressed[button] = True
        self._log_action(f"Press {button}")
        
        if not self.simulation_mode and self.gamepad:
            try:
                vg_button = getattr(vg.XUSB_BUTTON, self.button_map[button])
                self.gamepad.press_button(button=vg_button)
                self.gamepad.update()
            except Exception as e:
                self._log_action(f"Error pressing {button}", str(e))
                
        return True
    
    def release_button(self, button: str) -> bool:
        """Release a button on the controller"""
        if button not in self.button_map:
            return False
            
        self.state.buttons_pressed[button] = False
        self._log_action(f"Release {button}")
        
        if not self.simulation_mode and self.gamepad:
            try:
                vg_button = getattr(vg.XUSB_BUTTON, self.button_map[button])
                self.gamepad.release_button(button=vg_button)
                self.gamepad.update()
            except Exception as e:
                self._log_action(f"Error releasing {button}", str(e))
                
        return True
    
    def tap_button(self, button: str, duration: float = 0.1) -> bool:
        """Tap a button (press and release after duration)"""
        if self.press_button(button):
            time.sleep(duration)
            return self.release_button(button)
        return False
    
    def set_left_stick(self, x: float, y: float):
        """Set left stick position (-1.0 to 1.0 for both axes)"""
        x = max(-1.0, min(1.0, x))
        y = max(-1.0, min(1.0, y))
        
        self.state.left_stick_x = x
        self.state.left_stick_y = y
        self._log_action(f"Left stick", f"x={x:.2f}, y={y:.2f}")
        
        if not self.simulation_mode and self.gamepad:
            try:
                x_value = int(x * 32767)
                y_value = int(y * 32767)
                self.gamepad.left_joystick(x_value=x_value, y_value=y_value)
                self.gamepad.update()
            except Exception as e:
                self._log_action(f"Error setting left stick", str(e))
    
    def set_right_stick(self, x: float, y: float):
        """Set right stick position (-1.0 to 1.0 for both axes)"""
        x = max(-1.0, min(1.0, x))
        y = max(-1.0, min(1.0, y))
        
        self.state.right_stick_x = x
        self.state.right_stick_y = y
        self._log_action(f"Right stick", f"x={x:.2f}, y={y:.2f}")
        
        if not self.simulation_mode and self.gamepad:
            try:
                x_value = int(x * 32767)
                y_value = int(y * 32767)
                self.gamepad.right_joystick(x_value=x_value, y_value=y_value)
                self.gamepad.update()
            except Exception as e:
                self._log_action(f"Error setting right stick", str(e))
    
    def set_triggers(self, left: float, right: float):
        """Set trigger values (0.0 to 1.0)"""
        left = max(0.0, min(1.0, left))
        right = max(0.0, min(1.0, right))
        
        self.state.left_trigger = left
        self.state.right_trigger = right
        self._log_action(f"Triggers", f"left={left:.2f}, right={right:.2f}")
        
        if not self.simulation_mode and self.gamepad:
            try:
                left_value = int(left * 255)
                right_value = int(right * 255)
                self.gamepad.left_trigger(value=left_value)
                self.gamepad.right_trigger(value=right_value)
                self.gamepad.update()
            except Exception as e:
                self._log_action(f"Error setting triggers", str(e))
    
    def reset_controller(self):
        """Reset controller to neutral state"""
        self._log_action("Reset controller")
        
        if not self.simulation_mode and self.gamepad:
            try:
                self.gamepad.reset()
                self.gamepad.update()
            except Exception as e:
                self._log_action(f"Error resetting controller", str(e))
        
        # Reset state regardless of hardware mode
        self.state = ControllerState()
        for button in self.button_map.keys():
            self.state.buttons_pressed[button] = False
    
    def get_state(self) -> Dict[str, Any]:
        """Get current controller state"""
        state_dict = self.state.model_dump()
        state_dict['simulation_mode'] = self.simulation_mode
        return state_dict


# Global controller instance
controller = XboxControllerEmulator()

# Create FastMCP app
mcp = FastMCP("Xbox Controller Emulator")


@mcp.tool()
def press_button(button: str) -> Dict[str, Any]:
    """
    Press a button on the Xbox controller.
    
    Args:
        button: Button name (A, B, X, Y, LB, RB, BACK, START, LS, RS, DPAD_UP, DPAD_DOWN, DPAD_LEFT, DPAD_RIGHT)
    
    Returns:
        Dict with success status and current button states
    """
    success = controller.press_button(button)
    return {
        "success": success,
        "button": button,
        "action": "pressed",
        "current_state": controller.get_state()
    }


@mcp.tool()
def release_button(button: str) -> Dict[str, Any]:
    """
    Release a button on the Xbox controller.
    
    Args:
        button: Button name (A, B, X, Y, LB, RB, BACK, START, LS, RS, DPAD_UP, DPAD_DOWN, DPAD_LEFT, DPAD_RIGHT)
    
    Returns:
        Dict with success status and current button states
    """
    success = controller.release_button(button)
    return {
        "success": success,
        "button": button,
        "action": "released",
        "current_state": controller.get_state()
    }


@mcp.tool()
def tap_button(button: str, duration: float = 0.1) -> Dict[str, Any]:
    """
    Tap a button on the Xbox controller (press and release).
    
    Args:
        button: Button name (A, B, X, Y, LB, RB, BACK, START, LS, RS, DPAD_UP, DPAD_DOWN, DPAD_LEFT, DPAD_RIGHT)
        duration: How long to hold the button in seconds (default: 0.1)
    
    Returns:
        Dict with success status and action performed
    """
    success = controller.tap_button(button, duration)
    return {
        "success": success,
        "button": button,
        "action": "tapped",
        "duration": duration,
        "current_state": controller.get_state()
    }


@mcp.tool()
def set_left_stick(x: float, y: float) -> Dict[str, Any]:
    """
    Set the left analog stick position.
    
    Args:
        x: X-axis position (-1.0 to 1.0, left to right)
        y: Y-axis position (-1.0 to 1.0, down to up)
    
    Returns:
        Dict with success status and current stick position
    """
    # Clamp values to valid range
    x = max(-1.0, min(1.0, x))
    y = max(-1.0, min(1.0, y))
    
    controller.set_left_stick(x, y)
    return {
        "success": True,
        "stick": "left",
        "x": x,
        "y": y,
        "current_state": controller.get_state()
    }


@mcp.tool()
def set_right_stick(x: float, y: float) -> Dict[str, Any]:
    """
    Set the right analog stick position.
    
    Args:
        x: X-axis position (-1.0 to 1.0, left to right)
        y: Y-axis position (-1.0 to 1.0, down to up)
    
    Returns:
        Dict with success status and current stick position
    """
    # Clamp values to valid range
    x = max(-1.0, min(1.0, x))
    y = max(-1.0, min(1.0, y))
    
    controller.set_right_stick(x, y)
    return {
        "success": True,
        "stick": "right",
        "x": x,
        "y": y,
        "current_state": controller.get_state()
    }


@mcp.tool()
def set_triggers(left: float, right: float) -> Dict[str, Any]:
    """
    Set the trigger values.
    
    Args:
        left: Left trigger value (0.0 to 1.0)
        right: Right trigger value (0.0 to 1.0)
    
    Returns:
        Dict with success status and current trigger values
    """
    # Clamp values to valid range
    left = max(0.0, min(1.0, left))
    right = max(0.0, min(1.0, right))
    
    controller.set_triggers(left, right)
    return {
        "success": True,
        "left_trigger": left,
        "right_trigger": right,
        "current_state": controller.get_state()
    }


@mcp.tool()
def reset_controller() -> Dict[str, Any]:
    """
    Reset the controller to neutral state (all inputs released).
    
    Returns:
        Dict with success status and reset state
    """
    controller.reset_controller()
    return {
        "success": True,
        "action": "reset",
        "current_state": controller.get_state()
    }


@mcp.tool()
def get_controller_state() -> Dict[str, Any]:
    """
    Get the current state of the Xbox controller.
    
    Returns:
        Dict with current controller state including sticks, triggers, and buttons
    """
    return {
        "success": True,
        "current_state": controller.get_state()
    }


@mcp.tool()
def list_available_buttons() -> Dict[str, Any]:
    """
    List all available button names that can be used with the controller.
    
    Returns:
        Dict with list of available button names
    """
    return {
        "success": True,
        "available_buttons": list(controller.button_map.keys()),
        "button_descriptions": {
            "A": "A button (bottom face button)",
            "B": "B button (right face button)",
            "X": "X button (left face button)",
            "Y": "Y button (top face button)",
            "LB": "Left bumper",
            "RB": "Right bumper",
            "BACK": "Back/Select button",
            "START": "Start/Menu button",
            "LS": "Left stick click",
            "RS": "Right stick click",
            "DPAD_UP": "D-pad up",
            "DPAD_DOWN": "D-pad down",
            "DPAD_LEFT": "D-pad left",
            "DPAD_RIGHT": "D-pad right"
        }
    }


@mcp.tool()
def get_system_info() -> Dict[str, Any]:
    """
    Get information about the controller emulation system.
    
    Returns:
        Dict with system information and setup status
    """
    return {
        "success": True,
        "vgamepad_available": VGAMEPAD_AVAILABLE,
        "simulation_mode": controller.simulation_mode,
        "vgamepad_error": VGAMEPAD_ERROR if not VGAMEPAD_AVAILABLE else None,
        "setup_instructions": {
            "windows": "Install ViGEmBus driver from https://github.com/ViGEm/ViGEmBus/releases",
            "note": "Without ViGEmBus, the server runs in simulation mode (state tracking only)"
        }
    }


if __name__ == "__main__":
    """Run the MCP server"""
    print("Starting Xbox Controller MCP Server...")
    print("Available tools:")
    print("- press_button: Press a controller button")
    print("- release_button: Release a controller button")
    print("- tap_button: Tap a controller button")
    print("- set_left_stick: Set left analog stick position")
    print("- set_right_stick: Set right analog stick position")
    print("- set_triggers: Set trigger values")
    print("- reset_controller: Reset controller to neutral state")
    print("- get_controller_state: Get current controller state")
    print("- list_available_buttons: List all available buttons")
    print("- get_system_info: Get system information and setup status")
    print()
    
    if controller.simulation_mode:
        print("⚠️  Running in SIMULATION MODE")
        print("   Controller state will be tracked but no actual input will be sent.")
        print("   To enable hardware mode, install ViGEmBus:")
        print("   https://github.com/ViGEm/ViGEmBus/releases")
        print()
    else:
        print("✅ Hardware mode enabled - virtual controller ready!")
        print()
    
    print("Controller emulator initialized and ready!")
    
    # Run the MCP server
    mcp.run(transport="streamable-http")



