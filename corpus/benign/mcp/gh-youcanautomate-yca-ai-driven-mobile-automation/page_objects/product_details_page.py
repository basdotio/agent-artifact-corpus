"""
Page Object: ProductDetailsPage

Locators and methods for interacting with the Product Details Page page.
Auto-generated from captured workflow execution.
"""
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from typing import Optional


class ProductDetailsPage:
    """Page Object for Product Details Page page."""
    
    def __init__(self, driver: webdriver.Remote):
        """Initialize page with driver instance."""
        self.driver = driver
    
    # Locators
    # =========
    # Size M button - search for button with M in name or label
    ELEMENT_2404_LOCATOR = (AppiumBy.XPATH, "//XCUIElementTypeButton[contains(@name, 'M')] | //XCUIElementTypeStaticText[contains(@name, 'M')]")
    # Add to Cart button
    ADD_TO_CART_BUTTON_LOCATOR = (AppiumBy.XPATH, "//XCUIElementTypeButton[@name='Add to Cart']")
    # OK button for confirmation
    OK_BUTTON_LOCATOR = (AppiumBy.XPATH, "//XCUIElementTypeButton[@name='OK']")

    # Helper methods
    # ===============
    def get_element_2404(self):
        """Get element_2404 element."""
        return self.driver.find_element(*self.ELEMENT_2404_LOCATOR)
    
    def click_add_to_cart_button(self) -> None:
        """Click add_to_cart_button."""
        element = self.driver.find_element(*self.ADD_TO_CART_BUTTON_LOCATOR)
        element.click()
    
    def click_ok_button(self) -> None:
        """Click ok_button."""
        element = self.driver.find_element(*self.OK_BUTTON_LOCATOR)
        element.click()
    
    def click_element_2754(self) -> None:
        """Click element_2754."""
        element = self.driver.find_element(*self.ELEMENT_2754_LOCATOR)
        element.click()
    
    def is_displayed(self) -> bool:
        """Verify page is displayed by checking first locator."""
        try:
            element = self.driver.find_element(*self.ELEMENT_2404_LOCATOR)
            return element.is_displayed()
        except:
            return False