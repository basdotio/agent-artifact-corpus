# Interactive Chatbot Guide

The `appium-mcp` chatbot is an interactive tool for mobile app testing automation. It guides you through two phases:

## Features

### Phase 1: App Exploration & Page Object Generation

**What it does:**
- Guides you to explore your mobile app interactively
- Captures all interactions (clicks, text inputs, scrolling, etc.)
- Automatically generates Page Object Model (POM) classes
- Organizes elements by screen/page

**Workflow:**
1. Connect to your app (iOS or Android)
2. Provide natural language prompts
3. Watch as the chatbot executes each prompt on the device
4. Prompts are captured and analyzed
5. Page objects are auto-generated

**Example Prompts:**
```
Take a screenshot
Tap on the email field
Type user@example.com into the email field
Tap on the password field
Type password123
Tap on the Sign In button
Wait for the home screen to load
Tap on the first product
Scroll down to find the Add to Cart button
```

### Phase 2: Test Generation

**What it does:**
- Generates automated pytest tests from your exploration
- Uses the generated page objects for clean, maintainable code
- Creates regression tests capturing the exact workflow

**Options:**
1. **Regression Test**: Automatically creates test from your exploration workflow
2. **Custom Test**: Create additional test scenarios (coming soon)

## Example Workflow

```
📱 Mobile App Testing Chatbot
================================

🔧 Setting up app connection...
Select platform: ios
Device name: iPhone 16
Bundle ID: com.example.ecommerce

PHASE 1: APP EXPLORATION & PAGE OBJECT GENERATION
===============================================

Prompt #1: Take a screenshot
✓ Step completed (1 action)

Prompt #2: Tap on the email field and type user@example.com  
✓ Step completed (3 actions)

Prompt #3: Tap the Sign In button
✓ Step completed (2 actions)

Prompt #4: Tap first product
✓ Step completed (2 actions)

Prompt #5: done

📄 Generating Page Objects...
✓ Generated 3 page objects (LoginPage, HomePage, ProductDetailsPage)
✓ Captured 8 elements

PHASE 2: AUTOMATED TEST GENERATION
===================================

Select test type: 1 (Regression Test)

Generating Regression Test...
✓ Test generated: generated_tests/test_workflow.py

Generated files ready for use with pytest:
  pytest generated_tests/test_workflow.py -v
```

## Generated Artifacts

### Page Objects
Located in `page_objects/` directory:

```python
# Example: loginscreen_page.py
class LoginscreenPage:
    """Page Object for Login Screen."""
    
    def __init__(self, driver):
        self.driver = driver
    
    # Auto-discovered locators
    EMAIL_FIELD_LOCATOR = (AppiumBy.XPATH, "...")
    PASSWORD_FIELD_LOCATOR = (AppiumBy.XPATH, "...")
    SIGNIN_BUTTON_LOCATOR = (AppiumBy.XPATH, "...")
    
    # Auto-generated action methods
    def enter_email(self, text):
        element = self.driver.find_element(*self.EMAIL_FIELD_LOCATOR)
        element.send_keys(text)
    
    def click_signin(self):
        element = self.driver.find_element(*self.SIGNIN_BUTTON_LOCATOR)
        element.click()
```

### Tests
Located in `generated_tests/` directory:

```python
# Example: test_workflow.py
class TestWorkflow:
    """Regression test from chatbot exploration."""
    
    def test_login_and_purchase(self, driver):
        login_page = LoginscreenPage(driver)
        home_page = HomescreenPage(driver)
        
        # Auto-captured steps
        login_page.enter_email("user@example.com")
        login_page.click_signin()
        
        home_page.click_first_product()
        # ... more steps
```

## Running Generated Tests

```bash
# Run all tests
pytest generated_tests/ -v

# Run specific test
pytest generated_tests/test_workflow.py::TestWorkflow::test_login_and_purchase -v

# With coverage
pytest generated_tests/ --cov=page_objects --cov-report=html
```

## Tips & Best Practices

### Prompt Guidelines
- **Be specific**: "Tap the email field" works better than "Enter email"
- **One action per prompt**: Each prompt should do one logical task
- **Use clear language**: The AI understands natural language best
- **Include wait times**: "Wait 2 seconds for the next screen" if needed

### Avoiding Common Pitfalls
- ❌ Too long prompts: "Type email and password and click login" 
- ✅ Shorter steps: Separate into 3 prompts instead
- ❌ Vague descriptions: "Click button"
- ✅ Specific references: "Click Sign In button on the login screen"
- ❌ Assuming UI knowledge: "Click navbar"
- ✅ Describe what you see: "Scroll down to find the submit button"

### Debugging Failed Steps
1. Check the error message in the chatbot output
2. The AI tries multiple fallback strategies:
   - Accessibility ID
   - iOS predicate strings
   - XPath expressions
3. If a step fails, rephrase it more specifically
4. Take intermediate screenshots to verify app state

## Advanced Usage

### Using Page Objects in Custom Tests

```python
from page_objects.loginscreen_page import LoginscreenPage
from appium import webdriver

def test_custom_scenario(driver):
    """Custom test using generated page objects."""
    login = LoginscreenPage(driver)
    
    login.enter_email("test@example.com")
    login.enter_password("Test123")
    login.click_signin()
    
    # Assert page transition or element visibility
    assert login.is_displayed() == False
```

### Combining Multiple Workflows

Generate page objects from multiple workflows:
1. Run chatbot for login flow → creates `LoginscreenPage`
2. Run chatbot for purchasing flow → creates `ProductDetailsPage`, `CartPage`
3. Create master test combining all flows

## Requirements

- Appium Server running: `appium`
- Real device or simulator connected
- iOS: Xcode Command Line Tools
- Android: Android SDK
- AWS Bedrock credentials (.env file)

## Troubleshooting

### "Failed to connect to app"
- Verify Appium server is running: `appium`
- Check device is connected: `appium-flutter-driver` or `adb devices`
- Verify bundle ID/package name is correct

### "No element found"
- Element might not exist on current screen
- Check app has loaded completely
- Try rephrasing the prompt
- Take a screenshot first to verify app state

### "Bedrock API errors"
- Verify AWS credentials in `.env` file
- Check Bedrock model availability in your region
- Ensure boto3 is properly configured

## See Also

- [Main README](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/README.md)
- [YAML Workflow Guide](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/YAML_QUICK_START.md)
- [Architecture](https://github.com/youcanautomate-yca/ai-driven-mobile-automation/blob/main/ARCHITECTURE_REFACTORED.md)
