"""Base Page Object class with common functionality."""
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class BasePage:
    """Base class for all page objects."""
    
    def __init__(self, driver):
        """Initialize page object with driver instance.
        
        Args:
            driver: Appium WebDriver instance
        """
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
    
    def find_element(self, locator):
        """Find element by locator.
        
        Args:
            locator: Tuple of (By, locator_string)
            
        Returns:
            WebElement
        """
        return self.driver.find_element(*locator)
    
    def find_elements(self, locator):
        """Find multiple elements by locator.
        
        Args:
            locator: Tuple of (By, locator_string)
            
        Returns:
            List of WebElements
        """
        return self.driver.find_elements(*locator)
    
    def click(self, locator):
        """Click element.
        
        Args:
            locator: Tuple of (By, locator_string)
        """
        element = self.wait.until(EC.element_to_be_clickable(locator))
        element.click()
    
    def send_keys(self, locator, text):
        """Send text to element.
        
        Args:
            locator: Tuple of (By, locator_string)
            text: Text to send
        """
        element = self.wait.until(EC.presence_of_element_located(locator))
        element.clear()
        element.send_keys(text)
    
    def is_element_present(self, locator):
        """Check if element is present.
        
        Args:
            locator: Tuple of (By, locator_string)
            
        Returns:
            Boolean
        """
        try:
            self.driver.find_element(*locator)
            return True
        except:
            return False
