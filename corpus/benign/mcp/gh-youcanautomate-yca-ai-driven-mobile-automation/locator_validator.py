"""
LOCATOR VALIDATOR

Validates candidate locators against the real app.
Only locators that PASS validation should be added to page objects.

Usage:
    python locator_validator.py
    
Output format:
    LOCATOR: 'candidate value'
    STATUS: ✓ PASS or ✗ FAIL
    REASON: Element found | Element not found | Multiple elements | etc.
"""
import time
from appium import webdriver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class LocatorValidator:
    """Validates locators against real app."""
    
    def __init__(self):
        self.driver = None
        self.results = []
    
    def connect_to_app(self):
        """Connect to Appium server and app."""
        options = XCUITestOptions()
        options.device_name = "iPhone 16 - youcanautomate"
        options.platform_version = "18.5"
        options.bundle_id = "com.Imen.ecommerceApp"
        options.automation_name = "XCUITest"
        
        self.driver = webdriver.Remote(
            "http://localhost:4723/wd/hub",
            options=options
        )
        time.sleep(2)  # Wait for app to load
    
    def validate_locator(self, name, by, value, should_be_displayed=True):
        """
        Validate a single locator.
        
        Args:
            name: Locator name (e.g., "EMAIL_FIELD")
            by: Locator strategy (AppiumBy.XPATH, etc.)
            value: Locator value
            should_be_displayed: Whether element must be visible
            
        Returns:
            dict with validation result
        """
        result = {
            "name": name,
            "locator": value,
            "by": by,
            "status": None,
            "reason": None,
            "count": 0
        }
        
        try:
            elements = self.driver.find_elements(by, value)
            result["count"] = len(elements)
            
            if len(elements) == 0:
                result["status"] = "FAIL"
                result["reason"] = "Element not found"
            elif len(elements) == 1:
                elem = elements[0]
                if should_be_displayed:
                    if elem.is_displayed():
                        result["status"] = "PASS"
                        result["reason"] = "Element found and displayed"
                    else:
                        result["status"] = "FAIL"
                        result["reason"] = "Element found but NOT displayed"
                else:
                    result["status"] = "PASS"
                    result["reason"] = "Element found"
            else:
                # Multiple elements found - check if first one works
                elem = elements[0]
                if should_be_displayed and elem.is_displayed():
                    result["status"] = "WARN"
                    result["reason"] = f"Found {len(elements)} elements (using first)"
                else:
                    result["status"] = "FAIL"
                    result["reason"] = f"Multiple elements found ({len(elements)})"
                    
        except Exception as e:
            result["status"] = "FAIL"
            result["reason"] = f"Exception: {str(e)}"
        
        self.results.append(result)
        return result
    
    def print_result(self, result):
        """Pretty print validation result."""
        symbol = "✓" if result["status"] == "PASS" else "⚠" if result["status"] == "WARN" else "✗"
        print(f"\n{symbol} {result['name']}")
        print(f"   Locator: {result['locator']}")
        print(f"   Status:  {result['status']}")
        print(f"   Reason:  {result['reason']}")
        print(f"   Elements found: {result['count']}")
    
    def validate_login_page(self):
        """Validate LoginPage locators."""
        print("\n" + "="*80)
        print("VALIDATING LOGIN PAGE LOCATORS")
        print("="*80)
        
        candidates = [
            ("EMAIL_FIELD_1", AppiumBy.XPATH, "//XCUIElementTypeTextField[1]"),
            ("EMAIL_FIELD_2", AppiumBy.XPATH, "//XCUIElementTypeTextField[contains(@name, 'email') or contains(@label, 'email')]"),
            ("EMAIL_FIELD_3", AppiumBy.XPATH, "//XCUIElementTypeTextField"),
            ("PASSWORD_FIELD_1", AppiumBy.XPATH, "//XCUIElementTypeSecureTextField[1]"),
            ("PASSWORD_FIELD_2", AppiumBy.XPATH, "//XCUIElementTypeSecureTextField[1] | //XCUIElementTypeTextField[2]"),
            ("PASSWORD_FIELD_3", AppiumBy.XPATH, "//XCUIElementTypeTextField[2]"),
            ("SIGNIN_BUTTON_1", AppiumBy.ACCESSIBILITY_ID, "Sign In"),
            ("SIGNIN_BUTTON_2", AppiumBy.XPATH, "//XCUIElementTypeButton[@name='Sign In']"),
        ]
        
        print("\nValidating candidate locators...\n")
        for name, by, value in candidates:
            result = self.validate_locator(name, by, value)
            self.print_result(result)
    
    def validate_home_page(self):
        """Validate HomePage locators after login."""
        print("\n" + "="*80)
        print("VALIDATING HOME PAGE LOCATORS")
        print("="*80)
        
        # First, try to login
        print("\nLogging in to access home page...")
        try:
            email = self.driver.find_element(AppiumBy.XPATH, "//XCUIElementTypeTextField[1]")
            email.clear()
            email.send_keys("youcanautomate@gmail.com")
            
            pwd = self.driver.find_element(AppiumBy.XPATH, "//XCUIElementTypeSecureTextField[1]")
            pwd.clear()
            pwd.send_keys("Test123")
            
            signin = self.driver.find_element(AppiumBy.ACCESSIBILITY_ID, "Sign In")
            signin.click()
            
            time.sleep(3)  # Wait for home page
            print("✓ Login successful, now on home page\n")
            
            candidates = [
                ("CREW_NECK_1", AppiumBy.XPATH, "//*[contains(@name, 'Crew') or contains(@label, 'Crew')]"),
                ("CREW_NECK_2", AppiumBy.XPATH, "//XCUIElementTypeStaticText[contains(@label, 'Crew Neck')]"),
                ("CREW_NECK_3", AppiumBy.XPATH, "//XCUIElementTypeButton[contains(@name, 'Crew')]"),
                ("CREW_NECK_4", AppiumBy.XPATH, "//XCUIElementTypeImage[contains(@name, 'Crew')]"),
            ]
            
            print("Validating product locators...\n")
            for name, by, value in candidates:
                result = self.validate_locator(name, by, value)
                self.print_result(result)
                
        except Exception as e:
            print(f"✗ Login failed: {e}")
    
    def validate_product_details_page(self):
        """Validate ProductDetailsPage locators."""
        print("\n" + "="*80)
        print("VALIDATING PRODUCT DETAILS PAGE LOCATORS")
        print("="*80)
        
        try:
            # Click on product if not already there
            print("\nNavigating to product details page...\n")
            
            candidates = [
                ("SIZE_M_1", AppiumBy.XPATH, "//XCUIElementTypeButton[contains(@name, 'M')]"),
                ("SIZE_M_2", AppiumBy.XPATH, "//XCUIElementTypeStaticText[contains(@label, 'M')]"),
                ("SIZE_M_3", AppiumBy.XPATH, "//XCUIElementTypeButton[contains(@label, 'M')]"),
                ("ADD_TO_CART_1", AppiumBy.ACCESSIBILITY_ID, "Add to Cart"),
                ("ADD_TO_CART_2", AppiumBy.XPATH, "//XCUIElementTypeButton[@name='Add to Cart']"),
                ("OK_BUTTON_1", AppiumBy.ACCESSIBILITY_ID, "OK"),
                ("OK_BUTTON_2", AppiumBy.XPATH, "//XCUIElementTypeButton[@name='OK']"),
            ]
            
            print("Validating product details locators...\n")
            for name, by, value in candidates:
                result = self.validate_locator(name, by, value, should_be_displayed=False)
                self.print_result(result)
                
        except Exception as e:
            print(f"Exception during validation: {e}")
    
    def print_summary(self):
        """Print validation summary."""
        print("\n" + "="*80)
        print("VALIDATION SUMMARY")
        print("="*80)
        
        passed = [r for r in self.results if r["status"] == "PASS"]
        warned = [r for r in self.results if r["status"] == "WARN"]
        failed = [r for r in self.results if r["status"] == "FAIL"]
        
        print(f"\n✓ PASSED: {len(passed)}")
        for r in passed:
            print(f"  - {r['name']}: {r['locator'][:60]}...")
        
        if warned:
            print(f"\n⚠ WARNED: {len(warned)}")
            for r in warned:
                print(f"  - {r['name']}: {r['reason']}")
        
        print(f"\n✗ FAILED: {len(failed)}")
        for r in failed:
            print(f"  - {r['name']}: {r['reason']}")
        
        print(f"\n📊 TOTAL: {len(self.results)} locators tested")
        print(f"✓ Success Rate: {len(passed) + len(warned)}/{len(self.results)} ({100*(len(passed) + len(warned))//len(self.results)}%)")
        
        print("\n" + "="*80)
        print("RECOMMENDATIONS FOR PAGE OBJECTS")
        print("="*80)
        
        print("\nAdd ONLY the following PASSED locators to page objects:\n")
        for r in passed:
            print(f"  {r['name']} = (AppiumBy.{r['by'].split('.')[-1]}, \"{r['locator']}\")")
        
        if failed:
            print("\n⚠ DO NOT add these FAILED locators:")
            for r in failed:
                print(f"  ✗ {r['name']} - {r['reason']}")
    
    def run(self):
        """Run all validations."""
        print("\n🚀 LOCATOR VALIDATOR")
        print("Testing candidate locators against real app\n")
        
        try:
            self.connect_to_app()
            self.validate_login_page()
            
            # Try to validate other pages if login worked
            if any(r['status'] in ['PASS', 'WARN'] and r['name'].startswith('SIGNIN') 
                   for r in self.results):
                self.validate_home_page()
                self.validate_product_details_page()
            
            self.print_summary()
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
        finally:
            if self.driver:
                self.driver.quit()


if __name__ == "__main__":
    validator = LocatorValidator()
    validator.run()
