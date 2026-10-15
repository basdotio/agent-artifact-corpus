# YAML Testing - Quick Start

## What You Got

You can now run complete test scenarios from YAML files instead of entering prompts manually!

### New Files

```
ai-driven-mobile-automation/
├── yaml_loader.py          ✨ NEW - YAML loader utility
├── run_yaml.py             ✨ NEW - Main entry point for YAML tests
├── YAML_GUIDE.md           ✨ NEW - Complete YAML documentation
├── prompts/                ✨ NEW - Test scenario directory
│   ├── 01-screenshot.yml
│   ├── 02-login-workflow.yml
│   ├── 03-ecommerce-shopping.yml
│   └── 04-profile-update.yml
```

---

## Quickest Start (30 seconds)

### 1. Run an existing test

```bash
cd /Users/pavankumars/Documents/YouCanAutomate/repository/appium-mcp-demo/ai-driven-mobile-automation

python run_yaml.py prompts/01-screenshot.yml
```

That's it! The test will start executing immediately and show results.

---

## Create Your Own Test (5 minutes)

### 1. Create a YAML file

```bash
touch prompts/my-test.yml
```

### 2. Add your test scenario

**Option A: Simple single prompt**

```yaml
name: "My Test"
description: "What it does"
platform: ios
prompt: "Take a screenshot"
```

**Option B: Multi-step workflow**

```yaml
name: "Login Test"
description: "Complete login steps"
platform: ios

prompts:
  - "Take a screenshot"
  - "Find the email field and enter 'test@example.com'"
  - "Find the password field and enter 'password123'"
  - "Tap the login button"

timeout: 60
stop_on_error: true
```

### 3. Run it

```bash
python run_yaml.py prompts/my-test.yml
```

---

## Available Test Examples

| File | Type | Steps | Purpose |
|------|------|-------|---------|
| `01-screenshot.yml` | Single | 1 | Simple screenshot capture |
| `02-login-workflow.yml` | Workflow | 6 | Complete login flow |
| `03-ecommerce-shopping.yml` | Workflow | 13 | Full shopping experience |
| `04-profile-update.yml` | Workflow | 13 | Update user profile |

### Try them all:

```bash
python run_yaml.py prompts/01-screenshot.yml
python run_yaml.py prompts/02-login-workflow.yml
python run_yaml.py prompts/03-ecommerce-shopping.yml
python run_yaml.py prompts/04-profile-update.yml
```

---

## Key Features

✅ **Read entire prompt from file** - No manual entry needed  
✅ **Execute at one shot** - All steps run sequentially  
✅ **Single or multi-step** - Support both simple and complex flows  
✅ **Full configuration** - Platform, timeout, error handling  
✅ **Easy to version control** - YAML files in git  
✅ **Perfect for CI/CD** - Automated testing pipelines  

---

## YAML File Structure

### Required Fields

```yaml
name: "Test Name"          # What to call this test
platform: ios              # or "android"
prompt: "Your prompt"      # or use "prompts:" for multiple
```

### Optional Fields

```yaml
description: "Details"     # What the test does
timeout: 60                # Seconds (default: 30)
stop_on_error: true        # Stop if step fails (default: true)
tags:                      # For organizing tests
  - "critical"
  - "login"
device:                    # Device-specific config
  device_name: "iPhone 16"
  bundle_id: "com.app.id"
```

---

## Common Test Patterns

### Screenshot
```yaml
name: "Take Screenshot"
platform: ios
prompt: "Take a screenshot"
```

### Login
```yaml
name: "Login"
platform: ios
prompts:
  - "Take a screenshot"
  - "Enter email address"
  - "Enter password"
  - "Tap login button"
  - "Verify login successful"
```

### Form Submission
```yaml
name: "Submit Form"
platform: ios
prompts:
  - "Find the form"
  - "Fill in name field"
  - "Fill in email field"
  - "Check agreement checkbox"
  - "Tap submit button"
  - "Verify confirmation"
```

### Navigation
```yaml
name: "Navigate Features"
platform: ios
prompts:
  - "Navigate to settings"
  - "Find language preference"
  - "Change to Spanish"
  - "Save changes"
  - "Restart app"
```

---

## Tips & Tricks

### 1. Continue on Error (Non-Critical Tests)
```yaml
stop_on_error: false  # Workflow continues even if steps fail
```

### 2. Longer Timeouts for Complex Tests
```yaml
timeout: 120  # 2 minutes for slow operations
```

### 3. Tag Your Tests for Organization
```yaml
tags:
  - "regression"
  - "critical"
  - "daily-run"
```

### 4. Add Device Configuration
```yaml
device:
  platform: ios
  device_name: "iPhone 16"
  bundle_id: "com.app.id"
```

---

## Running Multiple Tests at Once

### Create a batch script (run_all.sh)

```bash
#!/bin/bash

echo "Running all tests..."

tests=(
  "prompts/01-screenshot.yml"
  "prompts/02-login-workflow.yml"
  "prompts/03-ecommerce-shopping.yml"
  "prompts/04-profile-update.yml"
)

for test in "${tests[@]}"; do
  echo ""
  echo "Running: $test"
  python run_yaml.py "$test"
done

echo ""
echo "All tests completed!"
```

### Run it
```bash
bash run_all.sh
```

---

## How It Works

```
┌─────────────────────────────┐
│   Your YAML Test File       │
│  prompts/my-test.yml        │
└──────────────┬──────────────┘
               │ python run_yaml.py
               ▼
┌─────────────────────────────┐
│   yaml_loader.py            │
│ - Parse YAML                │
│ - Validate config           │
│ - Extract settings          │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   MobileAutomationOrchestrator
│ - Initialize connection     │
│ - Send prompts to Bedrock   │
│ - Execute tools             │
└──────────────┬──────────────┘
               │
               ▼
         ┌─────────────┐
         │   Results   │
         │ - Status    │
         │ - Logs      │
         │ - Actions   │
         └─────────────┘
```

---

## Command Reference

### Run a single test
```bash
python run_yaml.py prompts/01-screenshot.yml
```

### Run a custom test
```bash
python run_yaml.py prompts/my-custom-test.yml
```

### Run with different platform
Create `prompts/android-test.yml`:
```yaml
name: "Android Test"
platform: android
prompt: "Take a screenshot"
```

Then run:
```bash
python run_yaml.py prompts/android-test.yml
```

---

## Troubleshooting

### "File not found"
Make sure the YAML file exists:
```bash
ls prompts/your-file.yml
```

### "YAML parsing error"
Check syntax - common issues:
- Wrong indentation (use spaces, not tabs)
- Missing colons after field names
- Check quotes around strings with special characters

### "AWS credentials not configured"
Set environment variables:
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

---

## Next Steps

1. ✅ Run an example test
   ```bash
   python run_yaml.py prompts/01-screenshot.yml
   ```

2. ✅ Create your first test file

3. ✅ Run your custom test

4. ✅ Read [YAML_GUIDE.md](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/YAML_GUIDE.md) for advanced features

---

## Files Reference

| File | Purpose |
|------|---------|
| [run_yaml.py](run_yaml.py) | Execute tests from YAML files |
| [yaml_loader.py](yaml_loader.py) | Parse and validate YAML |
| [YAML_GUIDE.md](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/YAML_GUIDE.md) | Complete YAML documentation |
| [prompts/](prompts) | Test scenario directory |

---

## Example Output

When you run a test, you'll see:

```
====================================================
CONFIGURATION SUMMARY
====================================================
Name: Complete Login Workflow
Description: Full login test
Platform: ios
Type: Workflow (6 steps)
Timeout: 60s
Stop on error: true
====================================================

✓ Loaded YAML configuration
✓ Bedrock client initialized
Processing 6 workflow steps...

Step 1: Take a screenshot - SUCCESS
Step 2: Find email field - SUCCESS
Step 3: Enter credentials - SUCCESS
Step 4: Tap login - SUCCESS
Step 5: Wait for screen - SUCCESS
Step 6: Final screenshot - SUCCESS

====================================================
WORKFLOW RESULTS
====================================================
Status: success
Steps completed: 6/6
====================================================
✓ Done
```

---

## Summary

**Before:** Enter prompts one by one interactively  
**After:** Define complete test scenarios in YAML, run all at once  

**Benefits:**
- Faster test execution
- Easier to version control
- Better for CI/CD pipelines
- Repeatable and consistent
- Professional test documentation

**Get started:** `python run_yaml.py prompts/01-screenshot.yml`

Ready? Start testing! 🚀
