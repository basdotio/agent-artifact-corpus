"""
Simple Playwright test script for Purdue Brightspace
"""

from playwright.sync_api import sync_playwright
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_brightspace_access():
    """Test basic access to Purdue Brightspace"""
    
    # Get credentials from environment variables
    username = os.getenv("PURDUE_USERNAME")
    password = os.getenv("PURDUE_PASSWORD")
    
    if not username or not password:
        print("❌ Error: PURDUE_USERNAME and PURDUE_PASSWORD must be set in .env file")
        return
    
    print(f"Using username: {username}")
    
    with sync_playwright() as p:
        # Launch browser (keep visible for manual interaction)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        try:
            # Navigate to Purdue Brightspace
            print("Navigating to Purdue Brightspace...")
            page.goto("https://purdue.brightspace.com")
            
            # Wait for page to load
            page.wait_for_load_state("networkidle")
            
            # Take screenshot of initial page
            page.screenshot(path="brightspace_initial.png")
            print("Screenshot saved as brightspace_initial.png")
            
            # Click on Purdue West Lafayette / Indianapolis button
            print("Looking for Purdue West Lafayette/Indianapolis button...")
            
            # Try different selectors to find the button
            purdue_button = page.query_selector("text=Purdue West Lafayette")
            if purdue_button:
                print("✓ Found Purdue West Lafayette button, clicking...")
                purdue_button.click()
                page.wait_for_load_state("networkidle")
            else:
                print("✗ Purdue button not found, trying alternative selectors...")
                # Try other possible selectors
                purdue_button = page.query_selector("a:has-text('Purdue')")
                if purdue_button:
                    print("✓ Found Purdue button with alternative selector, clicking...")
                    purdue_button.click()
                    page.wait_for_load_state("networkidle")
            
            # Now check if we can see the login form
            print("Checking for login form...")
            
            # Wait for username field
            try:
                page.wait_for_selector("#username", timeout=10000)
                print("✓ Found login form")
                
                # Fill in username
                print("Entering username...")
                page.fill("#username", username)
                
                # Fill in password
                print("Entering password...")
                page.fill("#password", password)
                
                # Take screenshot before submitting
                page.screenshot(path="brightspace_before_submit.png")
                print("Screenshot saved as brightspace_before_submit.png")
                
                # Click submit button
                print("Clicking login button...")
                page.click("button[type='submit']")
                
                # Wait for navigation/Duo Mobile prompt
                print("Waiting for Duo Mobile authentication...")
                print("⏳ Please approve the login request on your Duo Mobile app...")
                
                # Wait longer to allow for Duo Mobile approval
                time.sleep(30)
                
                # Take screenshot after submission
                page.screenshot(path="brightspace_after_submit.png")
                print("Screenshot saved as brightspace_after_submit.png")
                
            except Exception as e:
                print(f"✗ Error during login: {e}")
                page.screenshot(path="brightspace_error.png")
                print("Screenshot saved as brightspace_error.png")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()


if __name__ == "__main__":
    test_brightspace_access()
