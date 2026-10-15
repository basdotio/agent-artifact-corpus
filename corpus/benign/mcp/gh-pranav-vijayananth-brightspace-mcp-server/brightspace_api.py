"""
Brightspace MCP Server - Playwright-based web scraping for Purdue University
"""

from playwright.sync_api import sync_playwright, Browser, Page
import time
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class Course:
    """Data class for course information"""
    name: str
    code: str
    instructor: str
    url: str


@dataclass
class Assignment:
    """Data class for assignment information"""
    title: str
    due_date: str
    course: str
    status: str
    url: str


class BrightspaceScraper:
    """Main class for scraping Purdue Brightspace data"""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    def __enter__(self):
        """Context manager entry"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.page = self.browser.new_page()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()
    
    def login(self, username: str, password: str) -> bool:
        """
        Login to Purdue Brightspace with Duo Mobile 2FA
        
        Args:
            username: Purdue Career Account username
            password: Purdue Career Account password
            
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # Navigate to Purdue Brightspace login
            print("Navigating to Purdue Brightspace...")
            self.page.goto("https://purdue.brightspace.com")
            
            # Wait for page to load
            self.page.wait_for_load_state("networkidle")
            
            # Click on Purdue West Lafayette / Indianapolis button
            print("Looking for Purdue institution selector...")
            try:
                purdue_button = self.page.wait_for_selector("text=Purdue West Lafayette / Indianapolis", timeout=5000)
                if purdue_button:
                    print("Clicking Purdue West Lafayette button...")
                    purdue_button.click()
                    self.page.wait_for_load_state("networkidle")
            except Exception as e:
                print(f"Note: Institution selector not found or not needed: {e}")
            
            # Wait for login form to load
            print("Waiting for login form...")
            self.page.wait_for_selector("#username", timeout=10000)
            
            # Fill in credentials
            print("Entering credentials...")
            self.page.fill("#username", username)
            self.page.fill("#password", password)
            
            # Click login button
            print("Clicking login button...")
            self.page.click("button[type='submit']")
            
            # Wait for Duo Mobile prompt
            print("Waiting for Duo Mobile authentication...")
            print("Please approve the login request on your Duo Mobile app...")
            
            # Wait for successful authentication by checking for Brightspace homepage
            try:
                # Wait for navigation away from Duo page to Brightspace
                self.page.wait_for_function(
                    "() => window.location.href.includes('/d2l/home')",
                    timeout=60000
                )
                print("Duo Mobile authentication successful!")
                return True
            except Exception as e:
                print(f"Authentication failed or timed out: {e}")
                return False
                
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def get_courses(self) -> List[Course]:
        """
        Scrape list of enrolled courses
        
        Returns:
            List[Course]: List of course objects
        """
        try:
            # Navigate to home page
            print("Navigating to homepage...")
            self.page.goto("https://purdue.brightspace.com/d2l/home")
            
            # Wait for the My Courses widget to load (it's a web component)
            print("Waiting for My Courses widget to load...")
            self.page.wait_for_selector("d2l-my-courses", timeout=10000)
            
            # Wait a bit more for the courses to render inside the component
            time.sleep(3)
            
            # The courses are loaded dynamically, so we need to wait for them
            # Try multiple possible selectors based on the actual HTML structure
            course_selectors = [
                "d2l-enrollment-card .d2l-card-container",  # Main course containers
                ".d2l-card-container",  # Course card containers
                "d2l-enrollment-card a[href*='/d2l/home/']",  # Course links
                "a[href*='/d2l/home/']",  # Any course links
            ]
            
            courses = []
            for selector in course_selectors:
                print(f"Trying selector: {selector}")
                course_elements = self.page.query_selector_all(selector)
                
                if course_elements:
                    print(f"Found {len(course_elements)} course elements with {selector}")
                    
                    for element in course_elements:
                        try:
                            # If this is a link element, use it directly
                            if element.evaluate("el => el.tagName.toLowerCase()") == "a":
                                link_element = element
                            else:
                                # Otherwise, look for a link inside this element
                                link_element = element.query_selector("a[href*='/d2l/home/']")
                            
                            if not link_element:
                                continue
                            
                            # Get course URL
                            url = link_element.get_attribute("href")
                            if not url:
                                continue
                            
                            # Get course name from the span inside the link
                            name_span = link_element.query_selector(".d2l-card-link-text")
                            if name_span:
                                name = name_span.text_content().strip()
                            else:
                                # Fallback: get from link text or title
                                name = (
                                    link_element.get_attribute("title") or
                                    link_element.get_attribute("aria-label") or
                                    link_element.text_content()
                                )
                                if name:
                                    name = name.strip()
                            
                            # Extract course code from name
                            course_code = self._extract_course_code(name) if name else "Unknown"
                            
                            if name and name != "":
                                courses.append(Course(
                                    name=name,
                                    code=course_code,
                                    instructor="",
                                    url=url
                                ))
                                print(f"Found course: {name} ({course_code})")
                        except Exception as e:
                            print(f"Error extracting course from element: {e}")
                            continue
                    
                    # If we found courses, don't try other selectors
                    if courses:
                        break
            
            # If no courses found with any selector, take a screenshot for debugging
            if not courses:
                print("No courses found! Taking screenshot...")
                self.page.screenshot(path="homepage_debug.png")
                print("Screenshot saved as homepage_debug.png")
                print("Printing page HTML to debug...")
                # Get the inner HTML of the my-courses widget
                my_courses = self.page.query_selector("d2l-my-courses")
                if my_courses:
                    print(f"My Courses widget found, but no course elements inside")
                else:
                    print("My Courses widget not found!")
            
            return courses
            
        except Exception as e:
            print(f"Error getting courses: {e}")
            self.page.screenshot(path="error_getting_courses.png")
            return []
    
    def get_assignments(self, course_url: str) -> List[Assignment]:
        """
        Scrape assignments for a specific course
        
        Args:
            course_url: URL of the course
            
        Returns:
            List[Assignment]: List of assignment objects
        """
        try:
            # Ensure course_url is a full URL
            if not course_url.startswith("http"):
                course_url = f"https://purdue.brightspace.com{course_url}"
            self.page.goto(course_url)
            
            # Navigate to assignments (adjust selector as needed)
            assignments_link = self.page.query_selector("a[href*='assignments']")
            if assignments_link:
                assignments_link.click()
                self.page.wait_for_load_state("networkidle")
            
            assignments = []
            # Extract assignment information (selectors will need adjustment)
            assignment_elements = self.page.query_selector_all(".assignment-row")
            
            for element in assignment_elements:
                try:
                    title_element = element.query_selector(".assignment-title")
                    due_date_element = element.query_selector(".due-date")
                    status_element = element.query_selector(".status")
                    
                    title = title_element.text_content().strip() if title_element else "Unknown"
                    due_date = due_date_element.text_content().strip() if due_date_element else "No due date"
                    status = status_element.text_content().strip() if status_element else "Unknown"
                    
                    assignments.append(Assignment(
                        title=title,
                        due_date=due_date,
                        course=self._extract_course_from_url(course_url),
                        status=status,
                        url=title_element.get_attribute("href") if title_element else ""
                    ))
                except Exception as e:
                    print(f"Error extracting assignment: {e}")
                    continue
            
            return assignments
            
        except Exception as e:
            print(f"Error getting assignments: {e}")
            return []
    
    def _extract_course_code(self, course_name: str) -> str:
        """Extract course code from course name"""
        # Simple regex to extract course codes like "CS 18000" or "MATH 16500"
        import re
        match = re.search(r'([A-Z]{2,4})\s+(\d{5})', course_name)
        if match:
            return f"{match.group(1)} {match.group(2)}"
        return course_name.split(' - ')[0] if ' - ' in course_name else course_name
    
    def _extract_course_from_url(self, url: str) -> str:
        """Extract course name from URL"""
        # Extract course identifier from URL
        parts = url.split('/')
        for part in parts:
            if 'course' in part.lower():
                return part
        return "Unknown Course"
    
    def save_data(self, data: Dict, filename: str):
        """Save scraped data to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Data saved to {filename}")
        except Exception as e:
            print(f"Error saving data: {e}")


def main():
    """Example usage of the Brightspace scraper"""
    
    # Load credentials from environment variables
    USERNAME = os.getenv("PURDUE_USERNAME")
    PASSWORD = os.getenv("PURDUE_PASSWORD")
    
    if not USERNAME or not PASSWORD:
        print("❌ Error: PURDUE_USERNAME and PURDUE_PASSWORD must be set in .env file")
        print("Please create a .env file with:")
        print("PURDUE_USERNAME=your_username")
        print("PURDUE_PASSWORD=your_password")
        return
    
    print(f"Using username: {USERNAME}")
    
    # Use the scraper with context manager
    with BrightspaceScraper(headless=False) as scraper:
        # Login
        if scraper.login(USERNAME, PASSWORD):
            print("Login successful! Scraping data...")
            
            # Get courses
            courses = scraper.get_courses()
            print(f"Found {len(courses)} courses:")
            for course in courses:
                print(f"  - {course.name} ({course.code})")
            
            # Get assignments for first course (if any)
            if courses:
                first_course_url = courses[0].url
                if first_course_url:
                    assignments = scraper.get_assignments(first_course_url)
                    print(f"\nFound {len(assignments)} assignments in {courses[0].name}:")
                    for assignment in assignments:
                        print(f"  - {assignment.title} (Due: {assignment.due_date})")
            
            # Save data
            data = {
                "courses": [
                    {
                        "name": course.name,
                        "code": course.code,
                        "url": course.url
                    } for course in courses
                ],
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            scraper.save_data(data, "brightspace_data.json")
            
        else:
            print("Login failed!")


if __name__ == "__main__":
    main()
