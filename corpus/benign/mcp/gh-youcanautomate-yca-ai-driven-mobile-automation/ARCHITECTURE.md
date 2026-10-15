# Appium MCP - Detailed Architecture Documentation

## System Overview

**Appium MCP** is an AI-driven mobile test automation framework that provides:
- Multiple user interfaces (CLI, Chatbot, YAML, Python API)
- Core Appium command execution engine
- 8 specialized tool modules for different test operations
- AWS Bedrock AI integration for intelligent test generation
- Automatic code generation (page objects, test scripts)
- Support for iOS and Android platforms

---

## 1. Architecture Layers

### **Layer 1: Input Interfaces** (User Entry Points)
```
┌─────────────────────────────────────────────────────┐
│          INPUT INTERFACES (4 Methods)               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. CLI Commands        → appium-mcp-*             │
│     └─ appium-mcp-chatbot                          │
│     └─ appium-mcp-run-yaml                         │
│     └─ appium-mcp-server                           │
│     └─ appium-mcp-generate-tests                   │
│     └─ appium-mcp-generate-pages                   │
│     └─ appium-mcp-generate-regression              │
│                                                     │
│  2. Interactive Chatbot → chatbot.py               │
│     └─ Step-by-step guided testing                 │
│                                                     │
│  3. YAML Workflows     → *.yaml files              │
│     └─ Define test flows in YAML                   │
│                                                     │
│  4. Python API         → Direct import             │
│     └─ Programmatic access to framework            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Files:**
- `chatbot.py` - Main chatbot entry
- `server.py` - MCP server entry
- `run_yaml.py` - YAML workflow runner
- `generate_test_from_workflow.py` - Test generation
- `generate_page_objects.py` - Page object generation
- `generate_regression_test.py` - Regression test generation

---

### **Layer 2: Control & Routing Layer**
```
┌─────────────────────────────────────────────────────┐
│           CONTROL LAYER (Routers)                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  chatbot.py                                        │
│  ├─ Receives chatbot interactions                  │
│  ├─ Routes to orchestrator                         │
│  └─ Manages chatbot flow                           │
│                                                     │
│  run_yaml.py                                       │
│  ├─ Parses YAML input                              │
│  ├─ Routes to orchestrator                         │
│  └─ Manages workflow execution                     │
│                                                     │
│  server.py (MCP Server)                            │
│  ├─ Registers all tools                            │
│  ├─ Routes MCP protocol messages                   │
│  └─ Coordinates tool execution                     │
│                                                     │
│  generate_*.py                                     │
│  ├─ Accepts workflow data                          │
│  ├─ Generates code from templates                  │
│  └─ Outputs generated files                        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

### **Layer 3: Data Processing Layer**
```
┌─────────────────────────────────────────────────────┐
│         DATA PROCESSING LAYER                       │
├─────────────────────────────────────────────────────┤
│                                                     │
│  yaml_loader.py                                    │
│  ├─ Input: YAML file content                       │
│  ├─ Processing: Parse YAML into dict               │
│  └─ Output: Structured workflow data               │
│                                                     │
│  orchestrator.py                                   │
│  ├─ Input: Chatbot prompts or workflow steps       │
│  ├─ Processing: Break down into Appium commands    │
│  ├─ AI Integration: Call Bedrock for analysis      │
│  └─ Output: Execution commands                     │
│                                                     │
│  chatbot_page_object_orchestrator.py               │
│  ├─ Input: Interactive chatbot steps               │
│  ├─ Processing: Manage chatbot state               │
│  ├─ AI Integration: Claude for UI analysis         │
│  └─ Output: Recorded interactions                  │
│                                                     │
│  config.py                                         │
│  ├─ Input: .env file, CLI args                     │
│  ├─ Processing: Load & validate config             │
│  └─ Output: Configuration dict                     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

### **Layer 4: Core Services (Engine)**
```
┌─────────────────────────────────────────────────────┐
│         CORE SERVICES (Engine)                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  session_store.py                                  │
│  ├─ Manages active WebDriver instances             │
│  ├─ Stores current session state                   │
│  ├─ Tracks selected device/platform                │
│  └─ Provides session to all tools                  │
│  Methods:                                          │
│  ├─ create_session(options)                        │
│  ├─ get_current_session()                          │
│  ├─ delete_session()                               │
│  └─ get_devices()                                  │
│                                                     │
│  command.py                                        │
│  ├─ Core Appium command execution                  │
│  ├─ Wraps WebDriver commands                       │
│  ├─ Error handling & logging                       │
│  └─ Used by all tools                              │
│  Commands:                                         │
│  ├─ find_element(strategy, selector)               │
│  ├─ click(element)                                 │
│  ├─ send_keys(element, text)                       │
│  ├─ get_screenshot()                               │
│  ├─ scroll(direction)                              │
│  └─ wait_for_element(selector)                     │
│                                                     │
│  logger.py                                         │
│  ├─ Application-wide logging                       │
│  ├─ Logs to file & console                         │
│  └─ Configurable log levels                        │
│                                                     │
│  config.py                                         │
│  ├─ Loads environment variables                    │
│  ├─ Validates configuration                        │
│  ├─ Provides config to all modules                 │
│  └─ Handles defaults                               │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

### **Layer 5: Tool Module Layer**
```
┌──────────────────────────────────────────────────────────┐
│         TOOL MODULES (8 Specialized Tools)               │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  1. tools_session.py                                     │
│     ├─ select_platform(ios|android)                     │
│     ├─ select_device(device_name)                       │
│     ├─ create_session()                                 │
│     ├─ delete_session()                                 │
│     └─ open_notifications()                             │
│                                                          │
│  2. tools_interactions.py                                │
│     ├─ appium_click(element)                            │
│     ├─ appium_double_tap(element)                       │
│     ├─ appium_long_press(element)                       │
│     ├─ appium_set_value(element, text)                  │
│     ├─ appium_get_text(element)                         │
│     ├─ appium_screenshot()                              │
│     ├─ appium_element_screenshot(element)               │
│     ├─ appium_get_orientation()                         │
│     ├─ appium_set_orientation(orientation)              │
│     ├─ appium_handle_alert(action, text)                │
│     └─ appium_get_active_element()                      │
│                                                          │
│  3. tools_navigations.py                                │
│     ├─ appium_scroll(direction, amount)                 │
│     ├─ appium_scroll_to_element(selector)               │
│     └─ appium_swipe(x1, y1, x2, y2, duration)           │
│                                                          │
│  4. tools_app_management.py                             │
│     ├─ appium_activate_app(app_id)                      │
│     ├─ appium_install_app(path)                         │
│     ├─ appium_uninstall_app(app_id)                     │
│     ├─ appium_terminate_app(app_id)                     │
│     ├─ appium_list_apps()                               │
│     ├─ appium_is_app_installed(app_id)                  │
│     └─ appium_deep_link(link)                           │
│                                                          │
│  5. tools_context.py                                    │
│     ├─ appium_get_contexts()                            │
│     └─ appium_switch_context(context_name)              │
│                                                          │
│  6. tools_ios.py                                        │
│     ├─ appium_boot_simulator(device_name)               │
│     ├─ appium_setup_wda()                               │
│     └─ appium_install_wda()                             │
│                                                          │
│  7. tools_test_generation.py                            │
│     ├─ appium_generate_locators(page_source)            │
│     ├─ appium_generate_tests(workflow)                  │
│     └─ appium_generate_page_objects(workflow)           │
│                                                          │
│  8. tools_documentation.py                              │
│     └─ appium_answer_appium(question)                   │
│                                                          │
└──────────────────────────────────────────────────────────┘

Each tool:
├─ Receives parameters as JSON
├─ Calls core services (session_store, command)
├─ Executes Appium operations
├─ Returns structured JSON response
└─ Logs all actions
```

---

### **Layer 6: AI Integration Layer**
```
┌─────────────────────────────────────────────────────┐
│        AI INTEGRATION LAYER                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  bedrock_client.py                                 │
│  ├─ Connects to AWS Bedrock                        │
│  ├─ Sends prompts to Claude models                 │
│  ├─ Parses AI responses                            │
│  └─ Caches AI generations                          │
│                                                     │
│  Claude Model Options:                             │
│  ├─ claude-3-5-haiku (fastest, cheapest)          │
│  ├─ claude-3-5-sonnet (balanced)                   │
│  └─ claude-3-opus (most capable)                   │
│                                                     │
│  Use Cases:                                        │
│  ├─ Analyze page source for elements               │
│  ├─ Generate locators from descriptions            │
│  ├─ Generate test code                             │
│  ├─ Generate page objects                          │
│  └─ Interpret user prompts                         │
│                                                     │
│  Integration Points:                               │
│  ├─ orchestrator.py calls Bedrock                  │
│  ├─ chatbot_orchestrator.py calls Bedrock          │
│  └─ tools_test_generation.py calls Bedrock         │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

### **Layer 7: Code Generation Layer**
```
┌──────────────────────────────────────────────────────────┐
│           CODE GENERATION LAYER                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Templates (Jinja2)                                      │
│  ├─ templates/page_object.jinja2                        │
│  │  └─ Template for page object classes                 │
│  └─ templates/test.jinja2                               │
│     └─ Template for test scripts                        │
│                                                          │
│  Generators:                                            │
│  ├─ generate_page_objects.py                            │
│  │  ├─ Input: Element locators, page structure          │
│  │  ├─ Process: Render page_object.jinja2 template      │
│  │  └─ Output: PythonPageObject classes                 │
│  │                                                       │
│  ├─ generate_test_from_workflow.py                      │
│  │  ├─ Input: Workflow steps, interactions              │
│  │  ├─ Process: Render test.jinja2 template             │
│  │  └─ Output: pytest test scripts                      │
│  │                                                       │
│  ├─ generate_test_with_page_objects.py                  │
│  │  ├─ Input: Workflow + page objects                   │
│  │  ├─ Process: Generate tests using page objects       │
│  │  └─ Output: Tests with POM pattern                   │
│  │                                                       │
│  ├─ generate_regression_test.py                         │
│  │  ├─ Input: Previous test runs                        │
│  │  ├─ Process: Generate regression suite               │
│  │  └─ Output: Regression test scripts                  │
│  │                                                       │
│  ├─ locator_validator.py                                │
│  │  ├─ Input: Generated locators                        │
│  │  ├─ Process: Validate against page source            │
│  │  └─ Output: Verified locators                        │
│  │                                                       │
│  └─ locator_validation_service.py                       │
│     ├─ Input: Page source, locator strategy             │
│     ├─ Process: Find element with locator               │
│     └─ Output: Valid/Invalid result                     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

### **Layer 8: Output Layer**
```
┌──────────────────────────────────────────────────────────┐
│             OUTPUT ARTIFACTS                             │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Generated Tests/                                        │
│  ├─ test_*.py files                                     │
│  └─ Auto-generated pytest test scripts                  │
│                                                          │
│  page_objects/                                          │
│  ├─ base_page.py (Base class)                           │
│  ├─ *_page.py (Page classes)                            │
│  └─ Auto-generated POM classes                          │
│                                                          │
│  screenshots/                                           │
│  ├─ step_1.png                                          │
│  ├─ step_2.png                                          │
│  └─ Auto-captured screenshots                           │
│                                                          │
│  prompts/                                               │
│  ├─ *.yaml (Example workflows)                          │
│  └─ Sample YAML definitions                             │
│                                                          │
│  Logs/                                                  │
│  ├─ execution.log                                       │
│  └─ Framework execution logs                            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

### **Layer 9: External Services**
```
┌──────────────────────────────────────────────────────────┐
│           EXTERNAL SERVICES                              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Appium Server                                          │
│  ├─ Location: http://127.0.0.1:4723                    │
│  ├─ Role: Mobile automation backend                     │
│  ├─ Commands: WebDriver protocol                        │
│  └─ Managed by: command.py                              │
│                                                          │
│  iOS/Android Device                                    │
│  ├─ Real device or simulator/emulator                   │
│  ├─ Connected to Appium server                          │
│  ├─ Receives commands from Appium                       │
│  └─ Returns UI state to Appium                          │
│                                                          │
│  AWS Bedrock                                            │
│  ├─ Endpoint: AWS SDK                                   │
│  ├─ Models: Claude 3.5 Haiku, Sonnet, Opus            │
│  ├─ Authentication: AWS credentials                     │
│  └─ Managed by: bedrock_client.py                       │
│                                                          │
│  GitHub (Optional)                                      │
│  ├─ Repository: youcanautomate-yca/ai-driven-...       │
│  ├─ Can push test results                               │
│  └─ Used for: CI/CD integration                         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Data Flow Diagrams

### **2.1 Interactive Chatbot Flow**
```
User Input
    ↓
chatbot.py (receives and validates)
    ↓
chatbot_page_object_orchestrator.py (manages state)
    ↓
session_store.py (get active driver)
    ↓
orchestrator.py (interpret user prompt)
    ├─ Call bedrock_client.py (if needed: AI analysis)
    ├─ Translate to Appium commands
    └─ Return instructions
    ↓
command.py (execute Appium commands)
    ↓
Appium Server (http://localhost:4723)
    ↓
Device/Simulator (Perform action)
    ↓
Return result → command.py → command.py → chatbot.py → User
```

### **2.2 YAML Workflow Flow**
```
YAML File (.yaml)
    ↓
run_yaml.py (reads file)
    ↓
yaml_loader.py (parses YAML)
    ↓
orchestrator.py (processes each workflow step)
    ├─ For each action in YAML:
    │  ├─ Parse natural language
    │  ├─ Call bedrock_client.py (AI analysis)
    │  └─ Break into Appium commands
    │
    └─ Sequence commands
    ↓
session_store.py (get/create session)
    ↓
command.py (execute each command)
    ↓
Appium Server (send to device)
    ↓
Device (actions & responses)
    ↓
Return Results
    ├─ Screenshots: screenshots/
    ├─ Test Code: generated_tests/
    ├─ Page Objects: page_objects/
    └─ Logs: logs/
```

### **2.3 MCP Server Tool Flow**
```
External MCP Client
    ↓
server.py (MCP Server)
    ├─ Receives tool call in MCP protocol
    └─ Route to appropriate tool module
    ↓
Tool Module (e.g., tools_interactions.py)
    ├─ Validate parameters
    ├─ Call session_store.py (get session)
    └─ Call command.py (execute)
    ↓
command.py (Appium execution)
    ↓
Appium Server
    ↓
Device
    ↓
Return Result
    ├─ Convert to JSON response
    └─ Return to MCP Client
```

### **2.4 Code Generation Flow**
```
Recorded Interactions / Workflow
    ↓
Session Data (actions, elements, responses)
    ↓
generate_test_from_workflow.py / generate_page_objects.py
    ├─ Extract elements
    ├─ Analyze interactions
    └─ Call bedrock_client.py (name generation if needed)
    ↓
Jinja2 Templates
    ├─ templates/test.jinja2
    └─ templates/page_object.jinja2
    ↓
Render Template
    ├─ Fill in extracted data
    ├─ Generate Python code
    └─ Format output
    ↓
Output Artifacts
    ├─ generated_tests/test_*.py
    ├─ page_objects/*_page.py
    └─ Log generation details
```

---

## 3. Key Components Detective

### **3.1 Core Components**

| Component | File | Purpose | Dependencies |
|-----------|------|---------|--------------|
| Session Manager | session_store.py | Manages WebDriver instances | Appium, config |
| Command Executor | command.py | Executes Appium commands | session_store, logger |
| Config Manager | config.py | Loads environment config | python-dotenv |
| Logger | logger.py | Application logging | Python logging |
| YAML Parser | yaml_loader.py | Parses YAML workflows | PyYAML |
| Orchestrator | orchestrator.py | Processes workflows | command, bedrock_client |
| Bedrock Client | bedrock_client.py | AWS Bedrock integration | boto3 |
| MCP Client | mcp_client.py | MCP protocol handling | mcp library |

### **3.2 Tool Modules**

| Tool | File | Operations | Tools Count |
|------|------|-----------|------------|
| Session | tools_session.py | Platform/device selection, session mgmt | 5 |
| Interactions | tools_interactions.py | Click, tap, text input, screenshots | 11 |
| Navigation | tools_navigations.py | Scroll, swipe | 3 |
| App Management | tools_app_management.py | Install, launch, uninstall apps | 7 |
| Context | tools_context.py | Switch between contexts | 2 |
| iOS | tools_ios.py | iOS-specific operations | 3 |
| Test Generation | tools_test_generation.py | Generate tests & page objects | 3 |
| Documentation | tools_documentation.py | Answer questions | 1 |
| **Total** | - | - | **35+ tools** |

### **3.3 Generators**

| Generator | File | Input | Output |
|-----------|------|-------|--------|
| Test Gen | generate_test_from_workflow.py | Workflow JSON | test_*.py |
| Page Object Gen | generate_page_objects.py | Elements + interactions | page_objects/*_page.py |
| Page+Test Gen | generate_test_with_page_objects.py | Workflow + structures | Combined tests + POM |
| Regression Gen | generate_regression_test.py | Previous runs | Regression suite |

---

## 4. Configuration System

```
Config Priority Order:
1. Command-line arguments (highest)
2. .env file (local environment)
3. Environment variables (system level)
4. config.py defaults (lowest)

Key Config Variables:
├─ AWS
│  ├─ AWS_REGION (default: us-west-2)
│  ├─ AWS_ACCESS_KEY_ID
│  └─ AWS_SECRET_ACCESS_KEY
├─ Bedrock
│  └─ BEDROCK_MODEL (haiku/sonnet/opus)
├─ Device
│  ├─ PLATFORM (ios/android)
│  ├─ DEVICE_NAME
│  ├─ BUNDLE_ID (iOS)
│  ├─ APP_PACKAGE (Android)
│  └─ APP_ACTIVITY (Android)
├─ Appium
│  ├─ APPIUM_URL (default: http://127.0.0.1:4723)
│  ├─ IMPLICIT_WAIT (default: 10s)
│  └─ EXPLICIT_WAIT (default: 15s)
└─ Logging
   ├─ LOG_LEVEL
   └─ LOG_FILE
```

---

## 5. API & Method Signatures

### **Core Session Methods**
```python
# session_store.py
create_session(device_options: XCUITestOptions | UiAutomator2Options)
get_current_session() -> WebDriver
delete_session()
select_platform(platform: str)
select_device(device_name: str)
```

### **Core Command Methods**
```python
# command.py
find_element(strategy: str, selector: str) -> WebElement
click(element: WebElement | str)
send_keys(element: WebElement | str, text: str)
get_screenshot() -> bytes
scroll(direction: str, amount: int = 3)
wait_for_element(selector: str, timeout: int = 10)
```

### **Orchestrator Methods**
```python
# orchestrator.py
process_workflow(workflow: dict)
interpret_prompt(prompt: str) -> List[Command]
execute_commands(commands: List[Command])
```

### **Bedrock Client Methods**
```python
# bedrock_client.py
invoke_claude(prompt: str, model: str = None) -> str
generate_locators(page_source: str, description: str) -> dict
generate_test_code(workflow: dict) -> str
analyze_ui(page_source: str) -> dict
```

---

## 6. Entry Points & CLI

### **CLI Commands Mapping**

```
Command                          → File                    → Main Function
────────────────────────────────────────────────────────────────────────
appium-mcp-chatbot              → chatbot.py              → main()
appium-mcp-run-yaml             → run_yaml.py             → main()
appium-mcp-server               → server.py               → main()
appium-mcp-generate-tests       → generate_test_from...py → generate_test_from_workflow()
appium-mcp-generate-pages       → generate_page_objects.py→ generate_page_objects()
appium-mcp-generate-regression  → generate_regression...py→ generate_regression_test()
```

### **Python Entry Points**

```python
# From pyproject.toml [project.scripts]
appium-mcp-server = "server:main"
appium-mcp-run-yaml = "run_yaml:main"
appium-mcp-generate-tests = "generate_test_from_workflow:generate_test_from_workflow"
appium-mcp-generate-pages = "generate_page_objects:generate_page_objects"
appium-mcp-generate-regression = "generate_regression_test:generate_regression_test"
appium-mcp-chatbot = "chatbot:main"
```

---

## 7. Error Handling & Logging

### **Error Flow**
```
Exception in any layer
    ↓
logger.py logs error (with context)
    ↓
Appropriate exception raised
    ↓
Caught by calling layer
    ├─ Retry (if applicable)
    ├─ Fallback (if applicable)
    └─ Propagate to user
```

### **Logging Levels**
```
DEBUG   → Detailed internal operations
INFO    → General flow information
WARNING → Non-critical issues
ERROR   → Critical failures
CRITICAL → System failures
```

---

## 8. Dependencies Map

```
External Libraries:
├─ appium-python-client  → Appium WebDriver
├─ boto3                → AWS Bedrock
├─ pydantic             → Data validation
├─ pyyaml               → YAML parsing
├─ jinja2               → Template rendering
├─ python-dotenv        → .env loading
├─ mcp                  → Model Context Protocol
├─ pytest               → Test framework
├─ selenium             → WebDriver base
└─ rich                 → CLI formatting

Internal Imports:
├─ Tools modules import session_store + command
├─ All modules import config + logger
├─ Orchestrators import bedrock_client
└─ Generators import templates + jinja2
```

---

## 9. Execution Sequence Examples

### **Example 1: Interactive Chatbot - "Tap Login Button"**
```
1. User types: "Tap the Login button"
2. chatbot.py receives input
3. chatbot_page_object_orchestrator analyzes step
4. Calls bedrock_client → "find blue button named Login"
5. bedrock_client → AWS Claude → "//XCUIElementTypeButton[@name='Login']"
6. orchestrator.py → "click, xpath, //XCUIElementTypeButton[@name='Login']"
7. session_store.py → get_current_session() → WebDriver
8. command.py.click() → driver.find_element("xpath", "...").click()
9. Appium server → Device → Button clicked
10. command.py captures screenshot
11. Result returned to chatbot.py
12. Display to user with screenshot
```

### **Example 2: YAML Workflow Execution**
```
1. run_yaml.py reads: login_test.yaml
2. yaml_loader.py parses to dict
3. orchestrator.py processes workflow
4. For each step:
   a. Parse natural language
   b. Call bedrock_client for element analysis
   c. Break into Appium commands
   d. Execute via command.py
   e. Store results
5. After all steps:
   a. generate_page_objects.py creates POM classes
   b. generate_test_from_workflow.py creates test scripts
6. Output to:
   - generated_tests/test_login.py
   - page_objects/login_page.py
   - screenshots/step_*.png
```

---

## 10. Extension Points

**To add a new tool:**
```
1. Create tools_my_tool.py in root
2. Implement: def my_tool(params: dict) → dict
3. Register in server.py register_tools()
4. Add to [project.py-modules] in pyproject.toml
5. Tool automatically available via CLI/API
```

**To add a new generator:**
```
1. Create generate_my_thing.py
2. Implement: def generate_my_thing(input: dict) → output
3. Add entry point in pyproject.toml [project.scripts]
4. Now available as: appium-mcp-generate-my-thing
```

---

## Architecture Summary

```
         USER
          ↓
    ┌─────────────┐
    │  INTERFACES │ (CLI, Chatbot, YAML, API)
    └──────┬──────┘
           ↓
    ┌─────────────┐
    │ CONTROLLER  │ (Routers, handlers)
    └──────┬──────┘
           ↓
    ┌─────────────┐
    │ PROCESSORS  │ (Parsing, Orchestration)
    └──────┬──────┘
           ↓
    ┌─────────────┐
    │ AI LAYER    │ (AWS Bedrock, Claude)
    └──────┬──────┘
           ↓
    ┌─────────────┐
    │ CORE ENGINE │ (Session, Command, Config)
    └──────┬──────┘
           ↓
    ┌─────────────┐
    │ TOOLS (8)   │ (Specialized operations)
    └──────┬──────┘
           ↓
    ┌─────────────┐
    │ GENERATION  │ (Code gen with templates)
    └──────┬──────┘
           ↓
    ┌─────────────┐
    │ ARTIFACTS   │ (Tests, POM, Screenshots)
    └─────────────┘
           ↓
         DEVICE
```

This comprehensive documentation provides all details needed to generate architecture diagrams at various levels of detail!
