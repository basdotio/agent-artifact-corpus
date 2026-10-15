# Installation Guide

## Latest Stable Release (PyPI)

Install the latest stable version from PyPI:

```bash
pip install appium-mcp
```

## Development Installation

For development and contributing:

```bash
# Clone the repository
git clone https://github.com/youcanautomate-yca/ai-driven-mobile-automation.git
cd ai-driven-mobile-automation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks (optional)
pre-commit install
```

## Prerequisites

### System Requirements
- Python 3.8 or higher
- Node.js 14+ (for Appium server)
- macOS, Linux, or Windows

### For iOS Testing
- Xcode 12.0 or higher
- iOS Simulator or physical iOS device

### For Android Testing
- Android SDK/Emulator
- Java Development Kit (JDK) 8+

## Appium Server Setup

### Installation
```bash
# Install Appium globally
npm install -g appium

# Install Appium drivers
appium driver install xcuitest  # For iOS
appium driver install uiautomator2  # For Android
```

### Start Appium Server
```bash
# Start Appium on default port (4723)
appium

# Or specify custom host/port
appium --address 0.0.0.0 --port 4723
```

## AWS Setup (Optional)

For AI-powered test generation using AWS Bedrock with Claude models, follow these steps:

### Prerequisites
- AWS Account (create at https://aws.amazon.com if needed)
- AWS IAM user with Bedrock access
- AWS CLI installed (`aws --version`)

### Step 1: Create AWS Access Keys

1. Go to AWS Console: https://console.aws.amazon.com
2. Navigate to **IAM** > **Users** > Your username
3. Click **Security credentials** tab
4. Under **Access keys**, click **Create access key**
5. Choose **Command Line Interface (CLI)** use case
6. Copy the **Access Key ID** and **Secret Access Key**
   - ⚠️ **Save these securely** - you won't see the secret key again!

### Step 2: Configure AWS CLI

```bash
# Run configure command
aws configure

# Enter when prompted:
# AWS Access Key ID: [paste your Access Key ID]
# AWS Secret Access Key: [paste your Secret Access Key]
# Default region: us-east-1
# Default output format: json
```

This creates `~/.aws/credentials` and `~/.aws/config`

### Step 3: Enable Bedrock Model Access

1. Go to AWS Console: https://console.aws.amazon.com/bedrock/
2. Navigate to **Bedrock** > **Model Access** (left sidebar)
3. Click **Manage model access**
4. Find **Anthropic Claude** models:
   - ✅ **Claude 3 Haiku** (fastest, cheapest)
   - ✅ **Claude 3 Sonnet** (balanced)
   - ✅ **Claude 3.5 Sonnet** (most capable)
   - ✅ **Claude 3 Opus** (most powerful)
5. Check the boxes for models you want to use
6. Click **Save changes**
   - ⏳ Wait 1-2 minutes for access to be granted

### Step 4: Create `.env` File

Copy `.env.example` to `.env` and configure AWS settings:

```bash
cp .env.example .env
```

Edit `.env` with your AWS details:

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1

# AWS Bedrock Configuration
# Choose one of these models:
# - anthropic.claude-3-5-haiku-20241022-v1:0 (Fast, cheap)
# - anthropic.claude-3-5-sonnet-20241022-v1:0 (Balanced)
# - anthropic.claude-3-opus-20240229-v1:0 (Most powerful)
BEDROCK_MODEL_ID=anthropic.claude-3-5-haiku-20241022-v1:0

BEDROCK_MAX_TOKENS=2000
BEDROCK_ANTHROPIC_VERSION=bedrock-2024-06-04

# iOS Configuration (update with your device)
IOS_DEVICE_NAME=iPhone 16
IOS_BUNDLE_ID=com.example.testapp

# Android Configuration (update with your device)
ANDROID_DEVICE_ID=emulator-5554
ANDROID_APP_PACKAGE=com.example.testapp
```

### Step 5: Verify AWS Bedrock Access

```bash
# Check AWS credentials
aws sts get-caller-identity

# Expected output:
# {
#     "UserId": "AIDAI...",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-username"
# }

# Check Bedrock model access
aws bedrock list-foundation-models --region us-east-1 | grep Claude

# Should show available Claude models
```

### Step 6: Test Integration

Once installed, test the Bedrock integration:

```bash
# Activate virtual environment
source venv/bin/activate

# Test import
python -c "from bedrock_client import BedrockClient; print('✓ Bedrock client loaded')"

# Start chatbot to test
appium-mcp-chatbot
```

### Available Claude Models

| Model | ID | Speed | Cost | Best For |
|-------|--|----|------|----------|
| Claude 3.5 Haiku | `anthropic.claude-3-5-haiku-20241022-v1:0` | ⚡⚡⚡ Fast | 💰 Cheapest | Quick tests, MVP |
| Claude 3.5 Sonnet | `anthropic.claude-3-5-sonnet-20241022-v1:0` | ⚡⚡ Medium | 💰💰 Medium | Recommended |
| Claude 3 Opus | `anthropic.claude-3-opus-20240229-v1:0` | ⚡ Slow | 💰💰💰 Expensive | Complex tests |

### Cost Estimation

Example for 100 test automation runs:
- **Claude 3.5 Haiku**: ~$0.20-0.50
- **Claude 3.5 Sonnet**: ~$2-5
- **Claude 3 Opus**: ~$10-20

### Optional: AWS Inference Profile (Multi-Region)

For production, use Inference Profiles for automatic failover:

```bash
# Add to .env
BEDROCK_INFERENCE_PROFILE_ARN=arn:aws:bedrock:us-east-1:ACCOUNT_ID:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0
```

### Troubleshooting AWS Setup

**Error: "Model access not granted"**
```bash
# Wait 1-2 minutes after enabling model access in Bedrock console
# Then try again
```

**Error: "Invalid credentials"**
```bash
# Verify credentials
aws sts get-caller-identity

# Re-configure if needed
aws configure
```

**Error: "AccessDeniedException"**
```bash
# Your IAM user needs Bedrock permissions
# Add inline policy to your IAM user:
# 1. Go to IAM > Users > Your user
# 2. Click "Add permissions" > "Create inline policy"
# 3. Use this JSON:
```

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:GetFoundationModel",
        "bedrock:ListFoundationModels"
      ],
      "Resource": "*"
    }
  ]
}
```

**Error: "Region not available"**
```bash
# Bedrock is available in these regions:
# us-east-1, us-west-2, eu-west-1, ap-southeast-1

# Update .env:
AWS_REGION=us-east-1
```

## Verification

Verify installation successfully:

```bash
# Check package installation
python -c "import appium_mcp; print('✓ appium-mcp installed')"

# Check Appium server
appium --version

# Start interactive chatbot
appium-mcp-chatbot
```

## Troubleshooting

### Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall with verbose output
pip install -v appium-mcp
```

### Appium Connection Issues
```bash
# Check if Appium is running
curl http://localhost:4723/status

# Start Appium with debug output
appium --log-level debug
```

## Using as a Library

```python
from appium_mcp import MobileAutomationFramework
from appium.options.ios import XCUITestOptions

# Initialize framework
framework = MobileAutomationFramework()

# Or use with custom driver options
options = XCUITestOptions()
options.device_name = "iPhone 14"
options.platform_version = "16.0"

driver = framework.create_session(options)
```

## Next Steps

- [Quick Start Guide](README.md#quick-start-interactive-chatbot)
- [Page Object Model Guide](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/POM_GUIDE.md)
- [Chatbot Guide](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/CHATBOT_GUIDE.md)
- [API Documentation](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/README.md)
