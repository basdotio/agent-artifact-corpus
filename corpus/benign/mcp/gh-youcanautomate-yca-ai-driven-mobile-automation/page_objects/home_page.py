"""
Page Object: HomePage

Locators and methods for interacting with the Home Page page.
Auto-generated from captured workflow execution.
"""
from appium import webdriver
from appium.webdriver.common.appiumby import AppiumBy
from typing import Optional


class HomePage:
    """Page Object for Home Page page."""
    
    def __init__(self, driver: webdriver.Remote):
        """Initialize page with driver instance."""
        self.driver = driver
    
    # Locators
    # =========
    CREW_NECK_PRODUCT_LOCATOR = (AppiumBy.XPATH, "//*[contains(@name, 'Crew') or contains(@label, 'Crew')]")

    # Helper methods
    # ===============
    def click_crew_neck_product(self) -> None:
        """Click crew_neck_product."""
        element = self.driver.find_element(*self.CREW_NECK_PRODUCT_LOCATOR)
        element.click()
    
    def is_displayed(self) -> bool:
        """Verify page is displayed by checking first locator."""
        try:
            element = self.driver.find_element(*self.CREW_NECK_PRODUCT_LOCATOR)
            return element.is_displayed()
        except:
            return False