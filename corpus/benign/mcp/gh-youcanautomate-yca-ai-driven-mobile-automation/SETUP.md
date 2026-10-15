# Complete Setup Guide for appium-mcp

This guide provides detailed step-by-step instructions to set up the `appium-mcp` package from PyPI and get started with mobile test automation.

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Installation Steps](#installation-steps)
3. [Appium Server Setup](#appium-server-setup)
4. [AWS Bedrock Configuration](#aws-bedrock-configuration)
5. [Environment Configuration](#environment-configuration)
6. [Verification & Testing](#verification--testing)
7. [First Test](#first-test)
8. [Troubleshooting](#troubleshooting)

---

## System Requirements

Before starting, ensure your system meets these requirements:

### 1. **Python**
```bash
python --version  # Must be 3.8 or higher
# Output: Python 3.8.x, 3.9.x, 3.10.x, 3.11.x, or 3.12.x
```

### 2. **Node.js and npm** (for Appium)
```bash
node --version    # Must be 14.0.0 or higher
npm --version     # Must be 6.0.0 or higher
```

### 3. **iOS Setup** (for iOS testing)
- **macOS** (Appium for iOS only runs on macOS)
- **Xcode 12+** with Command Line Tools
```bash
xcode-select --install
```

### 4. **Android Setup** (for Android testing)
- **Android SDK** or Android Studio
- **Java Development Kit (JDK)** 11 or higher
- **ANDROID_HOME** environment variable set

### 5. **Git** (for repository access)
```bash
git --version  # Any recent version
```

---

## Installation Steps

### Step 1: Create a Virtual Environment (Recommended)

```bash
# Create project directory
mkdir my_appium_project
cd my_appium_project

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
# .venv\Scripts\activate
```

### Step 2: Install appium-mcp from PyPI

```bash
# Upgrade pip first
pip install --upgrade pip

# Install appium-mcp package
pip install appium-mcp
```

### Step 3: Verify Installation

```bash
# Test import
python -c "import appium_mcp; print('✓ appium-mcp installed successfully')"

# List available CLI commands
appium-mcp-chatbot --help
appium-mcp-server --help
appium-mcp-run-yaml --help
```

### Step 4: Install Appium Server Globally

```bash
# Install Appium
npm install -g appium@latest

# Install required drivers
appium driver install xcuitest   # For iOS
appium driver install uiautomator2  # For Android

# Verify Appium installation
appium --version
```

---

## Appium Server Setup

### Starting Appium Server

Appium must be running in a **separate terminal** for appium-mcp to function.

#### Option 1: Default Port (Recommended)
```bash
# Terminal 1: Start Appium server (listens on port 4723)
appium
```

You should see output like:
```
[Appium] Welcome to Appium v2.x.x
[Appium] Non-default server hostname or ip address set to 127.0.0.1
[Appium] Appium REST http interface listener started on 127.0.0.1:4723
```

#### Option 2: Custom Port
```bash
# Start Appium on specific port
appium --port 4725
```

#### Option 3: With Additional Options
```bash
# Advanced options
appium \
  --address 127.0.0.1 \
  --port 4723 \
  --log-level warn \
  --session-override
```

### Verify Appium Server

In another terminal:
```bash
# Test Appium connectivity
curl http://localhost:4723/status

# Expected response: JSON with Appium version and build info
```

---

## AWS Bedrock Configuration

AWS Bedrock integration provides AI-powered test generation with Claude AI models.

### Step 1: Create AWS Account

1. Go to [aws.amazon.com](https://aws.amazon.com)
2. Click **Sign up** and create a new account
3. Verify email and add payment method

### Step 2: Create AWS IAM User

1. Go to **AWS Console** → **IAM** → **Users**
2. Click **Create user**
3. Enter username: `appium-mcp-user`
4. Click **Next** → **Attach policies directly**
5. Attach these policies:
   - `AmazonBedrockReadOnlyAccess` (to list models)
   - `AmazonBedrockFullAccess` (to invoke models)

### Step 3: Create Access Keys

1. After user created, go to **Security credentials**
2. Click **Create access key**
3. Select **Command Line Interface (CLI)**
4. Copy the **Access Key ID** and **Secret Access Key**

### Step 4: Enable Bedrock Models

1. Go to **AWS Console** → **Bedrock** → **Model access**
2. Click **Modify model access**
3. Enable these models:
   - **Claude 3.5 Haiku** (fast & cheap)
   - **Claude 3.5 Sonnet** (balanced)
   - **Claude 3 Opus** (most capable)
4. Click **Save changes**

### Step 5: Verify AWS Region

Default region: `us-west-2` (where Claude models are available)

⚠️ **Important**: Claude models not available in all regions. Use:
- `us-west-2` (recommended)
- `us-east-1`
- `ap-northeast-1`
- `eu-central-1`

---

## Environment Configuration

### Step 1: Create .env File

Create `.env` file in your project root:

```bash
# Copy example template
cp .env.example .env

# Or create from scratch (see options below)
touch .env
```

### Step 2: Configure AWS Credentials

Edit `.env` and add:

```env
# AWS
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# Bedrock Model Selection (pick one)
# BEDROCK_MODEL=claude-3-5-haiku-20241022    # Fast & cheap (recommended)
BEDROCK_MODEL=claude-3-5-sonnet-20241022     # Balanced (recommended)
# BEDROCK_MODEL=claude-3-opus-20240229       # Most capable but expensive
```

### Step 3: Configure Device (iOS Example)

```env
# iOS Configuration
PLATFORM=ios
DEVICE_NAME=iPhone 14
BUNDLE_ID=com.example.app
APP_PATH=/path/to/app.app
SIMULATOR_UDID=AAAABBBB-CCCC-DDDD-EEEE-FFFF00001111
```

### Step 4: Configure Device (Android Example)

```env
# Android Configuration
PLATFORM=android
DEVICE_NAME=emulator-5554
APP_PACKAGE=com.example.app
APP_ACTIVITY=.MainActivity
DEVICE_ID=ZX1G432ABC
```

### Step 5: Configure Appium Server

```env
# Appium Server (usually localhost:4723)
APPIUM_URL=http://127.0.0.1:4723

# Optional: Automation options
IMPLICIT_WAIT=10
EXPLICIT_WAIT=15
```

---

## Verification & Testing

### Step 1: Verify AWS Credentials

```bash
# Terminal 2: In your project directory (with .venv activated)
python -c "
import boto3
import os
from dotenv import load_dotenv

load_dotenv()
session = boto3.Session(
    region_name=os.getenv('AWS_REGION')
)
bedrock = session.client('bedrock')
models = bedrock.list_foundation_models()
print('✓ AWS credentials valid')
print(f'✓ Available models: {len(models[\"modelSummaries\"])}')
"
```

### Step 2: Verify Bedrock Models

```bash
python -c "
import boto3
import os
from dotenv import load_dotenv

load_dotenv()
bedrock = boto3.client('bedrock', region_name=os.getenv('AWS_REGION'))
models = bedrock.list_foundation_models()

print('Available Claude models:')
for model in models['modelSummaries']:
    if 'claude' in model['modelId'].lower():
        print(f'  - {model[\"modelId\"]}')
"
```

### Step 3: Test Bedrock Connection

```bash
python -c "
import boto3
import os
import json
from dotenv import load_dotenv

load_dotenv()

bedrock = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION'))
model_id = os.getenv('BEDROCK_MODEL', 'claude-3-5-sonnet-20241022')

response = bedrock.invoke_model(
    modelId=model_id,
    body=json.dumps({
        'anthropic_version': 'bedrock-2023-06-01',
        'max_tokens': 100,
        'messages': [{'role': 'user', 'content': 'Say hello'}]
    })
)

result = json.loads(response['body'].read())
print('✓ Bedrock connection successful')
print(f'✓ Model response: {result[\"content\"][0][\"text\"][:50]}...')
"
```

---

## First Test

### Option 1: Interactive Chatbot (Easiest)

```bash
# Terminal 2: With .venv activated
appium-mcp-chatbot

# Follow the interactive prompts to:
# 1. Select platform (iOS/Android)
# 2. Enter device details
# 3. Walk through your app
# 4. Generate tests automatically
```

### Option 2: YAML Workflow

Create `my_first_test.yaml`:

```yaml
version: "1.0"
description: "My first automated test"
platform: "ios"
device_name: "iPhone 14"
bundle_id: "com.example.app"
app_path: "/path/to/app.app"

workflow:
  AppStart:
    - "Take a screenshot"
    
  HomePage:
    - "Tap on the first button"
    - "Wait 1 second"
    - "Take a screenshot"
```

Run it:

```bash
# Terminal 2: With Appium running in Terminal 1
appium-mcp-run-yaml my_first_test.yaml

# Outputs:
# - screenshots/ (captured screenshots)
# - page_objects/ (generated page classes)
# - generated_tests/ (generated Python test code)
```

### Option 3: Python API

```python
from dotenv import load_dotenv
from appium.webdriver.webdriver import WebDriver
from appium.options.ios import XCUITestOptions

load_dotenv()

# Create options
options = XCUITestOptions()
options.device_name = "iPhone 14"
options.bundle_id = "com.example.app"

# Create driver
driver = WebDriver.create_session(
    command_executor="http://127.0.0.1:4723",
    options=options
)

try:
    # Your test code here
    print("✓ iOS app started successfully")
finally:
    driver.quit()
```

---

## Troubleshooting

### Issue: "Appium server not responding"

**Solution:**
```bash
# Verify Appium is running
curl http://localhost:4723/status

# If not working, restart Appium
appium --port 4723

# Check if port 4723 is available
lsof -i :4723
```

### Issue: "AWS credentials error"

**Solution:**
```bash
# Verify .env file exists and has credentials
cat .env | grep AWS

# Test AWS connectivity
python -c "import boto3; boto3.Session().client('bedrock').list_foundation_models()"
```

### Issue: "Bedrock model not found"

**Solution:**
1. Ensure model region is correct (us-west-2)
2. Verify model enabled in AWS Console → Bedrock → Model access
3. Check BEDROCK_MODEL value in .env

### Issue: "Device not found"

**Solution (iOS):**
```bash
# List available simulators
xcrun simctl list devices

# List connected devices
xcrun xcode-select -p

# Check DEVICE_NAME and SIMULATOR_UDID in .env
```

**Solution (Android):**
```bash
# List connected devices
adb devices

# Start emulator
emulator -avd emulator_name

# Check DEVICE_ID in .env
```

### Issue: "Import errors"

**Solution:**
```bash
# Reinstall in clean environment
deactivate  # Exit current .venv
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install appium-mcp
```

### Issue: "Permission denied" errors

**Solution:**
```bash
# Ensure proper permissions
chmod +x ~/.appium_home/*

# On macOS: Allow Appium in Security preferences
# System Preferences → Security & Privacy → Allow Appium
```

---

## Next Steps

After successful setup:

1. **Read the [README.md](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/README.md)** - Overview and quick reference
2. **Explore [INSTALLATION.md](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/INSTALLATION.md)** - Comprehensive AWS setup
3. **Learn [YAML_QUICK_START.md](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/YAML_QUICK_START.md)** - YAML workflows in 5 min
4. **Check [YAML_GUIDE.md](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/YAML_GUIDE.md)** - Complete YAML reference
5. **Review [example workflows](prompts/)** - Ready-to-use templates
6. **Check [DEVELOPMENT.md](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/DEVELOPMENT.md)** - For contributor setup

---

## Support & Resources

- **GitHub Issues**: https://github.com/youcanautomate-yca/ai-driven-mobile-automation/issues
- **GitHub Discussions**: https://github.com/youcanautomate-yca/ai-driven-mobile-automation/discussions
- **PyPI Package**: https://pypi.org/project/appium-mcp/
- **Appium Docs**: https://appium.io/docs/en/2.0/
- **AWS Bedrock**: https://aws.amazon.com/bedrock/
- **Email**: youcanautomate@gmail.com

---

## Quick Reference

### Common Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Start Appium server (Terminal 1)
appium

# Run interactive chatbot (Terminal 2)
appium-mcp-chatbot

# Run YAML workflow
appium-mcp-run-yaml workflow.yaml

# Start MCP server
appium-mcp-server

# Generate tests
appium-mcp-generate-tests workflow.json

# Generate page objects
appium-mcp-generate-pages workflow.json
```

### Environment Variables Quick Check

```bash
# View all configured variables
echo "=== AWS Config ===" && \
grep "^AWS_" .env && \
echo "=== Bedrock ===" && \
grep "^BEDROCK" .env && \
echo "=== Device ===" && \
grep "^(PLATFORM|DEVICE|BUNDLE|APP)" .env
```

---

## Success Indicators

✅ You're ready when you can:

- Run `appium-mcp-chatbot` without errors
- Take a screenshot with `"Take a screenshot"` prompt
- See generated page objects in `page_objects/` folder
- See generated tests in `generated_tests/` folder
- See captured screenshots in `screenshots/` folder

Congratulations! You're now ready to automate mobile testing with AI. 🎉
