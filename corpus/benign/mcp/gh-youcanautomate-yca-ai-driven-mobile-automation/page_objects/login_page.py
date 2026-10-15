"""
Page Object: LoginPage

Locators and methods for interacting with the Login Page page.
Auto-generated from captured workflow execution.
"""
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from typing import Optional


class LoginPage:
    """Page Object for Login Page page."""
    
    def __init__(self, driver: webdriver.Remote):
        """Initialize page with driver instance."""
        self.driver = driver
    
    # Locators
    # =========
    # Email field: First TextField (value="Email" and placeholderValue="Email")
    EMAIL_FIELD_LOCATOR = (AppiumBy.XPATH, "//XCUIElementTypeTextField[contains(@value, 'Email')]")
    # Password field: SecureTextField
    PASSWORD_FIELD_LOCATOR = (AppiumBy.XPATH, "//XCUIElementTypeSecureTextField")
    # Sign In button has name attribute and label "Sign In"
    SIGNIN_BUTTON_LOCATOR = (AppiumBy.XPATH, "//XCUIElementTypeButton[@name='Sign In']")

    # Helper methods
    # ===============
    def enter_email_field(self, text: Optional[str] = None) -> None:
        """Enter text into email_field."""
        element = self.driver.find_element(*self.EMAIL_FIELD_LOCATOR)
        element.clear()
        element.send_keys(text or "youcanautomate@gmail.com")
    
    def enter_password_field(self, text: Optional[str] = None) -> None:
        """Enter text into password_field."""
        element = self.driver.find_element(*self.PASSWORD_FIELD_LOCATOR)
        element.clear()
        element.send_keys(text or "Test123")
    
    def click_signin_button(self) -> None:
        """Click signin_button."""
        element = self.driver.find_element(*self.SIGNIN_BUTTON_LOCATOR)
        element.click()
    
    def is_displayed(self) -> bool:
        """Verify page is displayed by checking first locator."""
        try:
            element = self.driver.find_element(*self.EMAIL_FIELD_LOCATOR)
            return element.is_displayed()
        except:
            return False