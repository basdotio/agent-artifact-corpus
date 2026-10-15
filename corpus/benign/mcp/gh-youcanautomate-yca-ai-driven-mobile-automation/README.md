# Appium MCP - AI-Driven Mobile Test Automation

Professional mobile test automation framework with AI-powered test generation, Page Object Model support, and AWS Bedrock integration.

**Supported Platforms**: iOS | Android  
**Python Version**: 3.8+  
**License**: MIT

## ✨ Features

- **Interactive Chatbot**: Walk through your app testing in natural language
- **AI-Generated Tests**: Automatically generate test code from your interactions
- **Page Object Model**: Auto-generate clean, reusable page objects
- **YAML Workflows**: Define test flows in simple YAML, AI handles execution
- **Multi-Platform**: iOS and Android support
- **Element Discovery**: Automatic element locator generation
- **Screenshot Capture**: Automatic screenshots at each step
- **AWS Integration**: Use Claude AI via Bedrock for test generation

## � Prerequisites

Before you start, ensure you have:

1. **Python 3.8 or higher**
   ```bash
   python --version
   ```

2. **Node.js 14+ and npm** (for Appium)
   ```bash
   node --version
   npm --version
   ```

## 📦 Installation

> **📖 Detailed Setup Guide**: For complete step-by-step instructions including:
> - System requirements verification
> - Virtual environment setup  
> - Appium server configuration
> - AWS Bedrock integration (AI-powered tests)
> - Device configuration (iOS/Android)
> - Troubleshooting guide
>
> **→ See [SETUP.md](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/SETUP.md) (Recommended for first-time users)**

### From PyPI (Recommended)
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install appium-mcp
pip install appium-mcp
```

> **📖 Detailed PyPI Installation Guide**: See [PYPI_INSTALL.md](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/PYPI_INSTALL.md) for complete step-by-step instructions

### From Source (Development)
```bash
git clone https://github.com/youcanautomate-yca/ai-driven-mobile-automation.git
cd ai-driven-mobile-automation
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

## 🔧 Setup Appium Server

> **For complete Appium setup guide including prerequisites → See [INSTALLATION.md](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/INSTALLATION.md)**

Appium server must be running for appium-mcp to work.

### Installation
```bash
# Install globally (one-time)
npm install -g appium

# Install drivers
appium driver install xcuitest   # iOS
appium driver install uiautomator2  # Android
```

### Start Server
```bash
# Terminal 1: Start Appium (runs on port 4723)
appium

# You should see:
# [Appium] Welcome to Appium v2.x.x
# ...
# [Appium] Server listening on http://127.0.0.1:4723
```

## 🎯 CLI Commands

Once installed, you have access to these commands:

### Interactive Chatbot (Easy!)
```bash
appium-mcp-chatbot
```
Perfect for beginners - guides you through test generation step-by-step.

### Run YAML Workflows
```bash
appium-mcp-run-yaml my_workflow.yaml
```
Execute predefined test workflows from YAML files.

### Generate Tests
```bash
appium-mcp-generate-tests workflow.json
```
Auto-generate test scripts from recorded interactions.

### Start MCP Server
```bash
appium-mcp-server
```
Start the Model Context Protocol server for integration.

## 📝 YAML Workflow Examples

### Example 1: Simple Login Test

Create a file `login_test.yaml`:
```yaml
version: "1.0"
description: "Login test"
platform: "ios"
device_name: "iPhone 14"
bundle_id: "com.example.app"
app_path: "/path/to/app.app"

workflow:
  LoginScreen:
    - "Take a screenshot to see the app"
    - "Tap on the email field"
    - "Type user@example.com"
    - "Tap on the password field"
    - "Type MyPassword123"
    - "Tap the Sign In button"
    - "Wait 2 seconds for login to complete"
    
  HomeScreen:
    - "Take a screenshot to verify login success"
    - "Verify that Welcome message is visible"
```

Run it:
```bash
appium-mcp-run-yaml login_test.yaml
```

### Example 2: E-Commerce Purchase Flow

Create `purchase_flow.yaml`:
```yaml
version: "1.0"
description: "Complete purchase flow"
platform: "android"
device_name: "emulator"
app_package: "com.myapp"
app_activity: ".MainActivity"

workflow:
  HomePage:
    - "Take screenshot"
    - "Scroll down to see products"
    - "Tap on first product"
    
  ProductPage:
    - "Take screenshot"
    - "Tap on size selector"
    - "Choose size M"
    - "Tap Add to Cart button"
    - "Verify item added message"
    
  CartPage:
    - "Tap on shopping cart icon"
    - "Take screenshot"
    - "Tap Checkout button"
    
  CheckoutPage:
    - "Enter shipping address"
    - "Enter payment details"
    - "Tap Place Order"
    - "Verify order confirmation"
```

Run it:
```bash
appium-mcp-run-yaml purchase_flow.yaml
```

### YAML File Structure

```yaml
version: "1.0"                    # YAML version (required)
description: "Test description"   # What this test does
platform: "ios" or "android"     # Target platform (required)
device_name: "iPhone 14"         # Device name/simulator
bundle_id: "com.example.app"     # iOS bundle ID
app_package: "com.example.app"   # Android package (Android only)
app_activity: ".MainActivity"    # Android activity (Android only)
app_path: "/path/to/app.app"     # Path to app binary

workflow:                         # Test steps
  ScreenName:                     # Group steps by screen
    - "Natural language prompt"   # AI executes this
    - "Another step"
    - "..."
  
  NextScreen:
    - "Step 1"
    - "Step 2"
```

### How YAML Workflows Work

1. **Write prompts in natural language** - No tool names needed
2. **AI inspects the current screen** - Analyzes app UI
3. **AI finds the right elements** - Uses element locators
4. **AI performs the action** - Click, type, scroll, etc.
5. **Auto-generates page objects** - Reusable code
6. **Auto-generates test code** - Ready-to-run tests

**Example**: Write one line:
```
"Tap on the email field and type test@example.com"
```

A generates Python code:
```python
class LoginPage:
    def enter_email(self, email):
        self.find_element("email_field").send_keys(email)
```

## 💻 Full Example: Running a Test

### Step 1: Create YAML file
Save as `test_app.yaml`:
```yaml
version: "1.0"
description: "Simple app test"
platform: "ios"
device_name: "iPhone 14"
bundle_id: "com.testapp"
app_path: "./app/TestApp.app"

workflow:
  Start:
    - "Take a screenshot"
    - "Tap the start button"
    - "Wait 1 second"
    - "Take final screenshot"
```

### Step 2: Start Appium (Terminal 1)
```bash
appium
```

### Step 3: Run the test (Terminal 2)
```bash
cd my_project
source venv/bin/activate
appium-mcp-run-yaml test_app.yaml
```

### Step 4: View results
- Generated test: `generated_tests/test_app.py`
- Page objects: `page_objects/StartPage.py`
- Screenshots: `screenshots/`

## 🤖 Python API Usage

Use appium-mcp as a Python library:

```python
from appium_mcp import MobileAutomationFramework
from appium.options.ios import XCUITestOptions

# Initialize framework
framework = MobileAutomationFramework()

# Create options
options = XCUITestOptions()
options.device_name = "iPhone 14"
options.bundle_id = "com.example.app"

# Create session
driver = framework.create_session(options)

# Use driver like standard Appium
driver.find_element("xpath", "//XCUIElementTypeButton[@name='Login']").click()

# Generate test code from session
test_code = framework.generate_test("my_test")
print(test_code)

# Cleanup
driver.quit()
```

## 📚 Comprehensive Guides

- **[Complete Setup Guide](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/SETUP.md)** ⭐ **START HERE** - Step-by-step installation, system requirements, Appium setup, AWS Bedrock configuration, device setup, and troubleshooting for PyPI users
- **[Installation Guide](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/INSTALLATION.md)** - AWS Bedrock integration details, model comparison, cost estimation, and advanced setup
- **[YAML Workflow Guide](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/YAML_GUIDE.md)** - Complete YAML workflow reference and examples
- **[YAML Quick Start](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/YAML_QUICK_START.md)** - 5-minute quick start for YAML workflows
- **[Chatbot Guide](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/CHATBOT_GUIDE.md)** - Interactive chatbot step-by-step guide
- **[Development Guide](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/DEVELOPMENT.md)** - Contributing, testing, and building from source

## 🆘 Troubleshooting

### "Appium server not responding"
```bash
# Make sure Appium is running
appium

# Check if running on correct port
curl http://localhost:4723/status
```

### "Connection refused"
```bash
# Restart Appium
appium --port 4723

# Verify config
appium-mcp-run-yaml --help
```

### "Element not found"
- Take a screenshot first: `"Take a screenshot"`
- Check the actual element name in the app
- Use more specific natural language: "Tap on the blue Login button"

### Import errors after installation
```bash
# Reinstall in clean environment
python -m venv fresh_env
source fresh_env/bin/activate
pip install appium-mcp
```

## 🔗 Resources

- **PyPI Package**: https://pypi.org/project/appium-mcp/
- **GitHub Repository**: https://github.com/youcanautomate-yca/ai-driven-mobile-automation
- **Appium Documentation**: https://appium.io/docs/en/2.0/
- **Report Issues**: https://github.com/youcanautomate-yca/ai-driven-mobile-automation/issues

## 📄 License

MIT License - see LICENSE file for details

## 👥 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📞 Support

- **GitHub Issues**: https://github.com/youcanautomate-yca/ai-driven-mobile-automation/issues
- **Email**: youcanautomate@gmail.com
- **Documentation**: https://github.com/youcanautomate-yca/ai-driven-mobile-automation/wiki

## Architecture

The server is organized into modular components:

```
ai-driven-mobile-automation/
├── server.py              # Main MCP server and tool registration
├── session_store.py       # Global driver and session management
├── command.py             # Core Appium command execution
├── logger.py              # Logging utilities
├── tools_session.py       # Session management tools
├── tools_interactions.py  # Element interaction tools
├── tools_navigations.py   # Navigation tools
├── tools_app_management.py # App management tools
├── tools_context.py       # Context switching tools
├── tools_ios.py           # iOS-specific tools
├── tools_test_generation.py # Test generation tools
├── tools_documentation.py  # Documentation/help tools
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Mirrored Tools from TypeScript Implementation

### Session Management
- `select_platform` - Select iOS or Android platform
- `select_device` - Select target device
- `create_session` - Create new Appium session
- `delete_session` - Delete active session
- `open_notifications` - Open notifications panel

### Element Interactions
- `appium_click` - Click on element
- `appium_find_element` - Find element by strategy/selector
- `appium_double_tap` - Double tap element
- `appium_long_press` - Long press element
- `appium_drag_and_drop` - Drag element to target
- `appium_press_key` - Press key
- `appium_set_value` - Set text value
- `appium_get_text` - Get element text
- `appium_get_active_element` - Get focused element
- `appium_screenshot` - Take screenshot
- `appium_element_screenshot` - Screenshot of element
- `appium_get_orientation` - Get device orientation
- `appium_set_orientation` - Set device orientation
- `appium_handle_alert` - Handle alert dialogs

### Navigation
- `appium_scroll` - Scroll up/down/left/right
- `appium_scroll_to_element` - Scroll until element visible
- `appium_swipe` - Perform swipe gesture

### App Management
- `appium_activate_app` - Activate installed app
- `appium_install_app` - Install app
- `appium_uninstall_app` - Uninstall app
- `appium_terminate_app` - Terminate running app
- `appium_list_apps` - List installed apps
- `appium_is_app_installed` - Check if app installed
- `appium_deep_link` - Open deep link

### Context Management
- `appium_get_contexts` - Get available contexts
- `appium_switch_context` - Switch between contexts

### iOS Tools
- `appium_boot_simulator` - Boot iOS simulator
- `appium_setup_wda` - Setup WebDriverAgent
- `appium_install_wda` - Install WebDriverAgent

### Test Generation
- `appium_generate_locators` - Generate element locators
- `appium_generate_tests` - Generate test scripts

### Documentation
- `appium_answer_appium` - Answer Appium questions

## YAML Workflow Automation

Simple, clean YAML workflows. Define screen names, write prompts, let AI handle everything else!

### Quick Example

Create `workflow.yml`:
```yaml
version: "1.0"
description: "Login and purchase"
platform: "ios"
device_name: "iPhone 16"
bundle_id: "com.example.ecommerce"

# Screen-based workflow - group prompts by screen
workflow:
  LoginScreen:
    - "Enter email user@example.com"
    - "Enter password mypassword"
    - "Click login button"
  
  HomeScreen:
    - "Click first product"
    - "View product details"
  
  CartScreen:
    - "Add item to cart"
    - "Click checkout"
  
  CheckoutScreen:
    - "Enter shipping address"
    - "Enter payment details"
    - "Complete purchase"
  
  OrderConfirmationScreen:
    - "Take screenshot"
```

### Run Workflow

```bash
appium-mcp-run-yaml workflow.yml
```

### What Happens Automatically

**For each prompt:**
1. ✅ AI inspects the current screen
2. ✅ Analyzes page source to find elements
3. ✅ Determines the right element to interact with
4. ✅ Performs the action (click, type, scroll, etc.)
5. ✅ Creates page object with discovered elements
6. ✅ Generates test code with reusable methods

### Auto-Generated Page Objects

From this YAML:
```yaml
LoginScreen:
  - "Enter email user@example.com"
```

AI generates:
```python
class LoginScreen:
    def login(self, email, password):
        self.email_field.send_keys(email)
        self.password_field.send_keys(password)
        self.login_button.click()
```

### Why This Approach?

- **No Tool Names** - Just write natural language
- **No Element Selectors** - AI finds them automatically
- **No Manual Page Objects** - Generated automatically
- **No ID/Xpath Maintenance** - AI updates as UI changes
- **Clean & Readable** - Anyone can write the YAML

### Advanced Features
- **Error Recovery** - AI retries with different approaches
- **Screenshots** - Automatic at each step
- **Element Waiting** - AI waits for elements to appear
- **Scroll Handling** - AI scrolls to find elements
- **Multi-Platform** - iOS and Android

### YAML Guides
- [YAML Quick Start](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/YAML_QUICK_START.md) - 5-minute guide
- [YAML Comprehensive Guide](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/YAML_GUIDE.md) - Full reference
- [Example Workflows](prompts/) - Ready-to-use examples

## Usage Example

```python
import asyncio
from mcp.client import StdioClient

async def main():
    # Create client
    client = StdioClient("python", ["server.py"])
    
    # Call a tool
    result = await client.call_tool(
        "select_platform",
        {"platform": "ios"}
    )
    print(result)

asyncio.run(main())
```

## Tool Schemas

Each tool includes:
- `name`: Unique tool identifier
- `description`: Human-readable description
- `inputSchema`: JSON schema for parameters
- `execute`: Async function that implements the tool

## Error Handling

All tools return a status JSON response:

```json
{
    "status": "success|error|warning",
    "message": "Human-readable message",
    ...tool-specific fields
}
```

## Logging

Logs are written to stderr with format:
```
[TOOL START] tool_name: arguments
[TOOL END] tool_name
[TOOL ERROR] tool_name: error message
```

## Differences from TypeScript Implementation

1. **Async/Await**: Python version uses async/await instead of Promise-based TypeScript
2. **Module Organization**: Simplified into single Python files instead of separate TypeScript modules
3. **Error Handling**: Try-catch blocks instead of TypeScript error handling
4. **Type System**: Uses type hints instead of TypeScript types

## Contributing

To add new tools:

1. Create a function in the appropriate `tools_*.py` file
2. Register it in `server.py` in the `register_tools()` function
3. Document the tool parameters and return values

## License

Same as parent appium-mcp project.

## Related

- [TypeScript Implementation](../appium-mcp/README.md)
- [Appium Documentation](https://appium.io)
- [MCP Specification](https://modelcontextprotocol.io)
