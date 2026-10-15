# PyPI Installation Instructions

This guide provides step-by-step instructions for installing `appium-mcp` from PyPI.

## Prerequisites

Before installing appium-mcp, ensure you have:

1. **Python 3.8 or higher**
   ```bash
   python --version
   ```

2. **Node.js 14+ and npm** (for Appium)
   ```bash
   node --version
   npm --version
   ```

## Installation Steps

### Step 1: Create a Virtual Environment

```bash
python -m venv .venv
```

### Step 2: Activate the Virtual Environment

**On macOS/Linux:**
```bash
source .venv/bin/activate
```

**On Windows:**
```bash
.venv\Scripts\activate
```

### Step 3: Upgrade pip (Optional but Recommended)

```bash
pip install --upgrade pip
```

### Step 4: Install appium-mcp

```bash
pip install appium-mcp
```

### Step 5: Verify Installation

```bash
appium-mcp-chatbot --help
```

You should see help output for the chatbot command.

## Quick Start After Installation

### 1. Start Appium Server

In a new terminal (keep virtual environment activated):
```bash
appium
```

You should see:
```
[Appium] Welcome to Appium v2.x.x
...
[Appium] Server listening on http://127.0.0.1:4723
```

### 2. Run the Interactive Chatbot

In another terminal (with .venv activated):
```bash
appium-mcp-chatbot
```

This opens an interactive session where you can describe test actions in natural language.

### 3. Run a YAML Workflow

Create a file `test.yaml`:
```yaml
version: "1.0"
description: "Simple test"
platform: "ios"
device_name: "iPhone 14"
bundle_id: "com.example.app"

workflow:
  Start:
    - "Take a screenshot"
    - "Tap the start button"
    - "Wait 1 second"
    - "Take final screenshot"
```

Run it:
```bash
appium-mcp-run-yaml test.yaml
```

## Common Commands

Once installed, you can use:

```bash
# Interactive chatbot for test generation
appium-mcp-chatbot

# Run YAML workflow files
appium-mcp-run-yaml workflow.yaml

# Generate tests from interaction logs
appium-mcp-generate-tests log.json

# Start MCP server
appium-mcp-server
```

## Deactivating Virtual Environment

When done, deactivate the virtual environment:
```bash
deactivate
```

## Troubleshooting

### Command not found: appium-mcp-chatbot

**Solution:** Ensure your virtual environment is activated:
```bash
source .venv/bin/activate
```

### ModuleNotFoundError: No module named 'appium_mcp'

**Solution:** Reinstall the package:
```bash
pip install --force-reinstall appium-mcp
```

### Appium server connection refused

**Solution:** Ensure Appium server is running:
```bash
appium
```

Should be listening on `http://127.0.0.1:4723`

## Next Steps

1. **Setup Guide**: Read [SETUP.md](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/SETUP.md) for complete configuration
2. **AWS Bedrock Integration**: See [INSTALLATION.md](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/INSTALLATION.md) for AI-powered test generation
3. **YAML Workflows**: Check [YAML_QUICK_START.md](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/YAML_QUICK_START.md) for quick examples
4. **Full Documentation**: Visit [README.md](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/README.md)

## Getting Help

- Check the [GitHub repository](https://github.com/youcanautomate-yca/ai-driven-mobile-automation)
- Review [Chatbot Guide](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/CHATBOT_GUIDE.md)
- Check [Troubleshooting in SETUP.md](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/SETUP.md#troubleshooting)
