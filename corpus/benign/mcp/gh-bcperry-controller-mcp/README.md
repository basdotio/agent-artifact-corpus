# Xbox Controller MCP Server

An MCP (Model Context Protocol) server that provides Xbox controller emulation capabilities using FastMCP and vgamepad.

## Features

- **Button Control**: Press, release, or tap any Xbox controller button
- **Analog Sticks**: Control left and right analog stick positions
- **Triggers**: Set left and right trigger values
- **State Management**: Get current controller state and reset to neutral
- **Simulation Mode**: Runs without hardware drivers for testing and development
- **Hardware Mode**: Full virtual controller support with ViGEmBus driver
- **Cross-platform**: Works on Windows (primary), with potential Linux support

## Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Windows OS (recommended for best vgamepad support)

## Installation

### Using uv (Recommended)

1. Clone or download this repository
2. Install dependencies using uv:

```bash
uv sync
```

This will create a virtual environment and install all dependencies from `pyproject.toml`.

### Alternative: Using pip

If you prefer to use pip:

```bash
pip install -r requirements.txt
```

### For Hardware Mode (Optional)

To enable actual controller input (instead of simulation mode):

1. Install ViGEmBus driver:
   - Download from: https://github.com/ViGEm/ViGEmBus/releases
   - Run `ViGEmBus_Setup_x64.exe` as Administrator
   - Reboot your system

Without the ViGEmBus driver, the server runs in **simulation mode** where controller state is tracked but no actual input is sent to the system.

## Usage

### Running the MCP Server

With uv:
```bash
uv run main.py
```

Or with Python directly:
```bash
python main.py
```

The server will start and listen for MCP connections. It automatically detects whether to run in hardware mode (with ViGEmBus) or simulation mode.

### Available Tools

#### Button Controls
- **`press_button(button)`**: Press a controller button
- **`release_button(button)`**: Release a controller button  
- **`tap_button(button, duration=0.1)`**: Tap a button (press and release)

#### Analog Controls
- **`set_left_stick(x, y)`**: Set left stick position (-1.0 to 1.0)
- **`set_right_stick(x, y)`**: Set right stick position (-1.0 to 1.0)
- **`set_triggers(left, right)`**: Set trigger values (0.0 to 1.0)

#### State Management
- **`reset_controller()`**: Reset controller to neutral state
- **`get_controller_state()`**: Get current controller state
- **`list_available_buttons()`**: List all available button names
- **`get_system_info()`**: Get system information and setup status

### Available Buttons

- **Face Buttons**: `A`, `B`, `X`, `Y`
- **Shoulder Buttons**: `LB`, `RB`
- **Menu Buttons**: `BACK`, `START`
- **Stick Clicks**: `LS`, `RS`
- **D-Pad**: `DPAD_UP`, `DPAD_DOWN`, `DPAD_LEFT`, `DPAD_RIGHT`

### Example Usage with MCP Client

```python
# Press the A button
await client.call_tool("press_button", {"button": "A"})

# Move left stick to upper right
await client.call_tool("set_left_stick", {"x": 0.5, "y": 0.5})

# Set both triggers to half press
await client.call_tool("set_triggers", {"left": 0.5, "right": 0.5})

# Tap the X button for 0.2 seconds
await client.call_tool("tap_button", {"button": "X", "duration": 0.2})

# Reset everything
await client.call_tool("reset_controller", {})
```

## Architecture

- **FastMCP**: Provides the MCP server framework
- **vgamepad**: Handles virtual Xbox controller creation and input injection
- **Pydantic**: Data validation and serialization
- **Dual Mode Operation**: 
  - **Hardware Mode**: Full virtual controller with ViGEmBus driver
  - **Simulation Mode**: State tracking without actual input (fallback mode)

## Coordinate Systems

### Analog Sticks
- **Range**: -1.0 to 1.0 for both X and Y axes
- **X-axis**: -1.0 (left) to 1.0 (right)
- **Y-axis**: -1.0 (down) to 1.0 (up)

### Triggers
- **Range**: 0.0 (not pressed) to 1.0 (fully pressed)

## Project Files

- **`main.py`**: Main MCP server implementation with Xbox controller emulation
- **`pyproject.toml`**: Project configuration and dependencies (uv/pip compatible)
- **`requirements.txt`**: Python dependencies for pip users
- **`uv.lock`**: Lockfile for exact dependency versions (uv)
- **`mcp-config.json`**: MCP client configuration file
- **`README.md`**: This documentation

## Configuration for MCP Clients

To use this server with Claude Desktop or other MCP clients, add the configuration from `mcp-config.json` to your MCP client settings:

```json
{
  "mcpServers": {
    "xbox-controller": {
      "command": "python",
      "args": ["main.py"],
      "cwd": "c:\\Users\\blain\\Documents\\git\\controller_mcp",
      "env": {},
      "description": "Xbox Controller Emulator MCP Server - Provides tools to emulate Xbox controller inputs including buttons, analog sticks, and triggers. Supports both hardware mode (with ViGEmBus) and simulation mode."
    }
  }
}
```

### Using with uv

If you're using uv, you can also configure it to use uv for execution:

```json
{
  "mcpServers": {
    "xbox-controller": {
      "command": "uv",
      "args": ["run", "main.py"],
      "cwd": "c:\\Users\\blain\\Documents\\git\\controller_mcp",
      "env": {},
      "description": "Xbox Controller Emulator MCP Server - Provides tools to emulate Xbox controller inputs including buttons, analog sticks, and triggers. Supports both hardware mode (with ViGEmBus) and simulation mode."
    }
  }
}
```

## Troubleshooting

### Hardware vs Simulation Mode

The server automatically detects whether the ViGEmBus driver is available:
- **Hardware Mode**: Virtual controller inputs are sent to the system
- **Simulation Mode**: Controller state is tracked but no actual input is sent

Check the console output when starting the server to see which mode is active.

### Windows
- Ensure you have the necessary permissions to create virtual devices
- Some antivirus software may block virtual device creation
- The first run might require administrator privileges
- If ViGEmBus installation fails, the server will still work in simulation mode

### Gaming Applications
- Most games should detect the virtual controller automatically (hardware mode only)
- You can verify the controller is working in Windows' "Game Controllers" settings
- Some games may require the virtual controller to be the only controller connected
- In simulation mode, no actual controller input is sent to games

### Development and Testing
- Use simulation mode for testing and development without affecting other applications
- Use the `get_system_info()` tool to check the current mode and setup status
- All MCP tools work in both modes - only the actual input injection differs

## Development

### Project Structure

The project uses modern Python tooling:
- **uv** for fast dependency management and virtual environments
- **pyproject.toml** for project configuration
- **FastMCP** for MCP server implementation
- **Pydantic** for data validation

### Adding New Features

The server is built modularly. To add new functionality:

1. Add methods to the `XboxControllerEmulator` class in `main.py`
2. Create corresponding MCP tools using the `@mcp.tool()` decorator
3. Update the documentation
4. Test in both hardware and simulation modes

### Development Setup

1. Clone the repository
2. Install development dependencies:
   ```bash
   uv sync --dev
   ```
3. Run the server:
   ```bash
   uv run main.py
   ```

### Testing

- The server includes comprehensive logging for both hardware and simulation modes
- Test individual functions by running the server and connecting with an MCP client
- Use the `get_system_info()` tool to verify the setup
- All functionality works in simulation mode for testing without hardware dependencies

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.