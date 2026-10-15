# Running Tests from YAML Files

## Overview

Instead of entering prompts interactively, you can define complete test scenarios in YAML files and execute them all at once. This is perfect for:

- **Batch testing** - Run multiple test scenarios automatically
- **CI/CD integration** - Execute tests in pipelines
- **Test documentation** - Keep test cases as version-controlled files
- **Repeatability** - Run the same tests consistently
- **Complex workflows** - Multi-step test scenarios defined clearly

## YAML Format

### Single Prompt (Simple Test)

Use when you only need to execute one action:

```yaml
name: "Take Screenshot"
description: "Simple screenshot capture"
platform: ios

# The main prompt
prompt: "Take a screenshot"

# Optional settings
timeout: 30
stop_on_error: true
```

### Workflow (Multi-Step Test)

Use when you need to execute multiple prompts sequentially:

```yaml
name: "Login Test"
description: "Test user login flow"
platform: ios

# List of prompts executed in order
prompts:
  - "Take a screenshot of the login screen"
  - "Find the email field and enter 'user@example.com'"
  - "Find the password field and enter 'password123'"
  - "Tap the login button"
  - "Take a screenshot to verify login was successful"

# Optional settings
timeout: 60
stop_on_error: true
```

---

## Configuration Options

### Required Fields

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `name` | string | "Login Test" | Descriptive name for the test |
| `prompt` OR `prompts` | string or list | "Take screenshot" | Test action(s) to execute |

### Optional Fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `platform` | string | "ios" | "ios" or "android" |
| `description` | string | "" | Detailed description of what the test does |
| `timeout` | integer | 30 | Seconds to wait for test completion |
| `stop_on_error` | boolean | true | Stop workflow if any step fails |
| `tags` | list | [] | Tags for organizing tests |
| `device` | object | {} | Device-specific configuration |

---

## Complete Examples

### Example 1: Simple Screenshot

File: `prompts/01-screenshot.yml`

```yaml
name: "Simple Screenshot"
description: "Capture the current screen"
platform: ios
prompt: "Take a screenshot"
```

Run:
```bash
python run_yaml.py prompts/01-screenshot.yml
```

---

### Example 2: Full Login Workflow

File: `prompts/login-test.yml`

```yaml
name: "Complete Login"
description: "Full login flow with verification"
platform: ios

prompts:
  - "Take a screenshot of the login screen"
  - "Find the email input field"
  - "Type 'testuser@example.com' in the email field"
  - "Find the password input field"
  - "Type 'SecurePassword123!' in the password field"
  - "Find and tap the 'Sign In' button"
  - "Wait for navigation to complete"
  - "Take a screenshot to verify successful login"

timeout: 60
stop_on_error: true

tags:
  - "authentication"
  - "login"
  - "critical"

device:
  platform: ios
  device_name: "iPhone 16"
  bundle_id: "com.Imen.ecommerceApp"
```

Run:
```bash
python run_yaml.py prompts/login-test.yml
```

---

### Example 3: E-Commerce Shopping Flow

File: `prompts/shopping-flow.yml`

```yaml
name: "Complete Shopping Flow"
description: "Browse products, add to cart, complete checkout"
platform: ios

prompts:
  - "Navigate to the products page"
  - "Scroll down to see available products"
  - "Take a screenshot showing all products"
  - "Tap on the first product to view details"
  - "Take a screenshot of the product details"
  - "Tap 'Add to Cart' button"
  - "Verify the item was added (check cart count)"
  - "Navigate to the shopping cart"
  - "Take a screenshot of the cart"
  - "Tap 'Proceed to Checkout'"
  - "Fill in shipping address with default address"
  - "Select standard shipping option"
  - "Take a screenshot showing order summary"
  - "Tap 'Place Order' button"
  - "Wait for order confirmation"
  - "Take a screenshot of the confirmation page"

timeout: 120
stop_on_error: false  # Try to complete even if some steps fail

tags:
  - "e-commerce"
  - "shopping"
  - "checkout"
```

Run:
```bash
python run_yaml.py prompts/shopping-flow.yml
```

---

### Example 4: Android Test

File: `prompts/android-login.yml`

```yaml
name: "Android Login Test"
description: "Login test for Android platform"
platform: android

prompts:
  - "Take a screenshot"
  - "Find the email field using accessibility ID"
  - "Enter email address"
  - "Find the password field"
  - "Enter password"
  - "Tap login button"
  - "Verify navigation to home screen"

timeout: 45
stop_on_error: true

device:
  platform: android
  device_id: "emulator-5554"
  app_package: "com.example.app"
  app_activity: ".MainActivity"
```

Run:
```bash
python run_yaml.py prompts/android-login.yml
```

---

## Advanced Features

### Continue on Error (Non-Critical Tests)

If you want the workflow to continue even if a step fails:

```yaml
name: "Exploratory Test"
description: "Test that can handle some failures"
platform: ios

prompts:
  - "Take a screenshot"
  - "Try to find optional feature (might not exist)"
  - "Take another screenshot"
  - "Verify main functionality"

stop_on_error: false  # Keep going even if optional feature not found
timeout: 90
```

### Organize Tests with Tags

```yaml
name: "Critical User Flow"
description: "Essential test for daily runs"
platform: ios

prompts:
  - "Login to app"
  - "Navigate to main feature"
  - "Verify core functionality"

tags:
  - "regression"
  - "critical"
  - "daily-run"
```

### Device-Specific Configuration

```yaml
name: "Device-Specific Test"
platform: ios

prompts:
  - "Test on specific device"

device:
  platform: ios
  device_name: "iPhone 16 Pro"
  bundle_id: "com.app.specific"
  udid: "A9F8F99F-F18B-4991-9FC4-017504210C94"
```

---

## Running Multiple Tests

### Run one test at a time:

```bash
python run_yaml.py prompts/login-test.yml
python run_yaml.py prompts/shopping-flow.yml
python run_yaml.py prompts/profile-update.yml
```

### Create a Bash script to run all tests:

File: `run_all_tests.sh`

```bash
#!/bin/bash

echo "Running all YAML test scenarios..."

python run_yaml.py prompts/01-screenshot.yml
python run_yaml.py prompts/02-login-workflow.yml
python run_yaml.py prompts/03-ecommerce-shopping.yml
python run_yaml.py prompts/04-profile-update.yml

echo "All tests completed!"
```

Run:
```bash
bash run_all_tests.sh
```

---

## Output and Logging

When you run a YAML test, you'll see:

```
====================================================
CONFIGURATION SUMMARY
====================================================
Name: Complete Login Challenge
Description: Full login flow
Platform: ios
Type: Workflow (6 steps)
Tags: authentication, login
Timeout: 60s
Stop on error: true
====================================================

2026-03-22 10:15:30 - INFO - Loading yaml_loader
2026-03-22 10:15:30 - INFO - ✓ Loaded YAML configuration
2026-03-22 10:15:32 - INFO - Calling Bedrock for prompt interpretation
2026-03-22 10:15:35 - INFO - Processing 6 workflow steps...

Step 1: screenshot (SUCCESS)
Step 2: find_element (SUCCESS)
Step 3: set_value (SUCCESS)
Step 4: find_element (SUCCESS)
Step 5: set_value (SUCCESS)
Step 6: click_element (SUCCESS)

====================================================
WORKFLOW RESULTS
====================================================
Status: success
Steps completed: 6/6
  Step 1: success
  Step 2: success
  Step 3: success
  Step 4: success
  Step 5: success
  Step 6: success
====================================================
```

---

## Creating Your Own Test File

### Step-by-Step Guide

#### 1. Create the file
```bash
mkdir -p prompts
touch prompts/my-custom-test.yml
```

#### 2. Add basic structure
```yaml
name: "My Custom Test"
description: "Test description"
platform: ios
```

#### 3. Add prompts (single or multiple)

**For single action:**
```yaml
prompt: "Take a screenshot"
```

**For workflow:**
```yaml
prompts:
  - "First step"
  - "Second step"
  - "Third step"
```

#### 4. Add optional settings
```yaml
timeout: 60
stop_on_error: true
tags:
  - "custom"
  - "my-test"
```

#### 5. Run it
```bash
python run_yaml.py prompts/my-custom-test.yml
```

---

## Useful Prompts

Here are some common prompt patterns:

### Navigation
- "Navigate to the profile page"
- "Go back to the home screen"
- "Open the settings menu"
- "Tap on the help button"

### Form Filling
- "Enter '2024-12-25' in the date field"
- "Select 'Male' from the gender dropdown"
- "Check the 'I agree' checkbox"
- "Type 'Smith' in the last name field"

### Verification
- "Check if the success message is displayed"
- "Verify the page title is 'Dashboard'"
- "Confirm the total price is $99.99"
- "Look for the loading spinner"

### Screenshots
- "Take a screenshot of the current page"
- "Capture a screenshot showing all options"

### Wait/Pause
- "Wait 2 seconds for the data to load"
- "Wait for the confirmation page"

---

## Troubleshooting

### File not found error
```
Error: File not found: prompts/my-test.yml
```
**Solution:** Check the file path and make sure it exists relative to where you're running the command.

### YAML Syntax error
```
YAML parsing error: ...
```
**Solution:** Check your YAML syntax. Common issues:
- Make sure indentation is correct (use spaces, not tabs)
- Check for missing colons after field names
- Ensure strings are properly quoted if they contain special characters

### Missing required fields
```
ValueError: Missing required field: prompt
```
**Solution:** Ensure you have either `prompt` (single) or `prompts` (list) defined.

### AWS credentials error
```
AWS credentials not configured
```
**Solution:** Set environment variables:
```bash
export AWS_ACCESS_KEY_ID=your_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

---

## Best Practices

1. **Use descriptive names** - Make it clear what each test does
2. **Add descriptions** - Document the purpose of each test
3. **Organize by feature** - Group related tests together
4. **Use tags** - For categorizing (e.g., "critical", "regression")
5. **Version control** - Keep YAML files in git for traceability
6. **Start simple** - Begin with single-prompt tests before complex workflows
7. **Set appropriate timeouts** - Longer workflows may need more time
8. **Test locally first** - Run tests manually before automating

---

## Files Included

- `run_yaml.py` - Main script to execute YAML tests
- `yaml_loader.py` - YAML parsing and validation
- `prompts/01-screenshot.yml` - Simple screenshot example
- `prompts/02-login-workflow.yml` - Full login workflow
- `prompts/03-ecommerce-shopping.yml` - E-commerce flow
- `prompts/04-profile-update.yml` - Profile update flow

---

## Next Steps

1. **Try an example:** `python run_yaml.py prompts/01-screenshot.yml`
2. **Create your test:** Edit or create a YAML file in `prompts/`
3. **Run it:** `python run_yaml.py prompts/your-test.yml`
4. **Integrate:** Add to your CI/CD pipeline for automated testing
