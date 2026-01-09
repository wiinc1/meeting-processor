#!/usr/bin/env python
import os
import time
import logging
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.safari.service import Service as SafariService
import argparse
from dotenv import load_dotenv
import re
import dateutil.parser
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OtterSelenium:
    def __init__(self, browser='chrome', headless=False):
        """
        Initialize Selenium WebDriver for Otter.ai automation.
        
        Args:
            browser: Browser to use ('chrome')
            headless: Whether to run browser in headless mode
        """
        if browser.lower() != 'chrome':
            raise ValueError("Only Chrome is supported in this version.")
        self.browser_type = 'chrome'
        self.headless = headless
        self.driver = None
        self.apple_id = os.getenv('APPLE_ID')
        self.apple_password = os.getenv('APPLE_PASSWORD')
        self.profile_dir = None  # Will be set from main if provided
        
        if not self.apple_id or not self.apple_password:
            logger.warning("Apple ID or password not found in environment. You'll need to manually log in.")
        
        self.base_url = 'https://otter.ai'
        self.login_url = 'https://otter.ai/signin'
    
    def setup_driver(self):
        """Set up and return the WebDriver."""
        from selenium.webdriver.chrome.options import Options
        options = Options()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')
        
        # Adding user-agent to make it look more like a real browser
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36')
        
        if self.profile_dir:
            logger.info(f"Using Chrome profile directory: {self.profile_dir}")
            options.add_argument(f'--user-data-dir={self.profile_dir}')
        
        service = ChromeService(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        
        # Set implicit wait time
        self.driver.implicitly_wait(10)
        
        return self.driver
    
    def login_with_apple(self):
        """
        Navigate to Otter.ai and log in using Apple authentication.
        If already logged in, skip login.
        """
        try:
            logger.info("Navigating to Otter.ai login page")
            self.driver.get(self.login_url)
            wait = WebDriverWait(self.driver, 20)

            # Check if already logged in (meeting list or home page visible)
            try:
                # Wait for up to 5 seconds for the meeting list to appear
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'a[data-testid="conversation-title-link"]'))
                )
                logger.info("Already logged in to Otter.ai, skipping login.")
                # Always navigate to home after login
                self.driver.get('https://otter.ai/home')
                return True
            except Exception:
                pass  # Not logged in, continue with login flow

            logger.info("Looking for 'Continue with Apple' button")
            apple_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Continue with Apple')]"))
            )
            logger.info("Clicking 'Continue with Apple' button")
            apple_btn.click()
            logger.info("Waiting for Apple sign-in page")
            print("\n====================== ATTENTION REQUIRED ======================")
            print("Please complete the Apple ID authentication in the browser window")
            print("The script will wait up to 60 seconds for you to complete this step")
            print("==============================================================\n")
            try:
                wait = WebDriverWait(self.driver, 180)
                wait.until(EC.url_contains('otter.ai/home'))
                logger.info("Successfully logged in to Otter.ai")
                # Always navigate to home after login
                self.driver.get('https://otter.ai/home')
                return True
            except TimeoutException:
                current_url = self.driver.current_url
                if 'otter.ai' in current_url and 'signin' not in current_url:
                    logger.info(f"Detected successful login at URL: {current_url}")
                    # Always navigate to home after login
                    self.driver.get('https://otter.ai/home')
                    return True
                logger.error("Login failed or timed out")
                print("\nLogin failed or timed out. Please try again.")
                return False
        except Exception as e:
            logger.error(f"An error occurred during login: {e}")
            return False
    
    def get_all_meetings(self, limit=50):
        """
        Extract all available meetings data from the Otter.ai interface by scrolling to the bottom until all meetings are loaded.
        Returns:
            List of meetings with metadata
        """
        try:
            logger.info("Navigating to Otter.ai home page (meetings list)")
            self.driver.get('https://otter.ai/home')
            wait = WebDriverWait(self.driver, 30)
            logger.info("Waiting for meetings list to load")
            
            # Wait for page to load
            time.sleep(3)
            
            # Try multiple selectors that might work for Otter.ai
            selectors_to_try = [
                'a[data-testid="conversation-title-Link"]',
                'a[data-testid="conversation-title-link"]', 
                '[data-testid*="conversation"]',
                'a[href*="/u/"]',
                '.conversation-item',
                '[class*="conversation"]'
            ]
            
            meeting_links = []
            for selector in selectors_to_try:
                try:
                    meeting_links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if meeting_links:
                        logger.info(f"Found {len(meeting_links)} meetings using selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not meeting_links:
                logger.error("No meeting links found with any selector")
                # Save screenshot and HTML for debugging
                os.makedirs('logs', exist_ok=True)
                screenshot_path = os.path.join('logs', 'meetings_wait_timeout.png')
                html_path = os.path.join('logs', 'meetings_wait_timeout.html')
                self.driver.save_screenshot(screenshot_path)
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                logger.info(f"Saved screenshot to {screenshot_path} and HTML to {html_path}")
                return []
            else:
                logger.info(f"Found {len(meeting_links)} meeting links on the page")
            
            # Handle infinite scroll to load all meetings
            logger.info("Scrolling to load all meetings (Otter.ai uses infinite scroll)")
            last_count = len(meeting_links)
            no_new_count = 0
            max_no_new = 3  # Stop if no new meetings found after 3 scrolls
            scroll_attempts = 0
            max_scrolls = 20  # Maximum scroll attempts
            
            while scroll_attempts < max_scrolls:
                # Scroll to the bottom of the page
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)  # Wait for content to load
                
                # Get updated meeting count
                current_meeting_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/u/"]')
                current_count = len(current_meeting_links)
                logger.info(f"Scroll attempt {scroll_attempts + 1}: Found {current_count} meetings so far")
                
                # Check if we found new meetings
                if current_count == last_count:
                    no_new_count += 1
                    if no_new_count >= max_no_new:
                        logger.info("No new meetings loaded after several scrolls. Stopping scroll loop.")
                        break
                else:
                    no_new_count = 0
                
                last_count = current_count
                scroll_attempts += 1
                
                # Check if we've reached the limit
                if current_count >= limit:
                    logger.info(f"Reached limit of {limit} meetings")
                    break
            
            logger.info(f"Finished scrolling. Total meetings found: {last_count}")
            
            # Now extract meeting data from all loaded meetings
            meeting_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/u/"]')
            meetings = []
            
            for link in meeting_links:
                try:
                    url = link.get_attribute('href')
                    title = link.text.strip()
                    
                    if url and title:
                        # Extract meeting ID from URL
                        import re
                        match = re.search(r'/u/([\w\-]+)', url)
                        meeting_id = match.group(1) if match else None
                        
                        # Try to extract date from title or other elements
                        date = None
                        try:
                            # Look for date in the title
                            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', title)
                            if date_match:
                                date = date_match.group(1)
                        except Exception:
                            pass
                        
                        meetings.append({
                            'id': meeting_id,
                            'url': url,
                            'title': title,
                            'date': date
                        })
                        
                        if len(meetings) >= limit:
                            break
                            
                except Exception as e:
                    logger.warning(f"Error extracting meeting data: {e}")
                    continue
            
            logger.info(f"Successfully extracted {len(meetings)} meetings")
            return meetings
                
        except Exception as e:
            logger.error(f"Error getting meetings: {e}")
            # Save screenshot and HTML for debugging
            os.makedirs('logs', exist_ok=True)
            screenshot_path = os.path.join('logs', 'meetings_error.png')
            html_path = os.path.join('logs', 'meetings_error.html')
            self.driver.save_screenshot(screenshot_path)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info(f"Saved screenshot to {screenshot_path} and HTML to {html_path}")
            return []

            # Step 0: Inspect for iframes and shadow roots
            # Log all iframes
            iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
            logger.info(f"Found {len(iframes)} iframes on the page.")
            for idx, iframe in enumerate(iframes):
                try:
                    src = iframe.get_attribute('src')
                    logger.info(f"Iframe #{idx}: src={src}")
                except Exception as e:
                    logger.warning(f"Could not get src for iframe #{idx}: {e}")
            # Log shadow roots (best effort, Selenium can't pierce them directly)
            containers = self.driver.find_elements(By.CSS_SELECTOR, 'div')
            for idx, div in enumerate(containers):
                try:
                    shadow_root = self.driver.execute_script('return arguments[0].shadowRoot', div)
                    if shadow_root:
                        logger.info(f"Div #{idx} has a shadow root.")
                except Exception as e:
                    pass
            # Step 0.5: Search for and click any 'Load more' or similar button
            load_more_selectors = [
                "button", "a"
            ]
            load_more_texts = [
                "load more", "show more", "see more", "more meetings", "next"
            ]
            found_and_clicked = False
            for selector in load_more_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    try:
                        text = el.text.strip().lower()
                        if any(t in text for t in load_more_texts):
                            logger.info(f"Clicking '{text}' button/link.")
                            el.click()
                            found_and_clicked = True
                            time.sleep(2)
                    except Exception as e:
                        logger.warning(f"Could not click candidate load more element: {e}")
            if not found_and_clicked:
                logger.info("No 'Load more' or similar button found.")
            # Step 0.75: Log instructions for user to inspect network tab for meetings API
            logger.info("To find the meetings API endpoint, open Chrome DevTools (F12), go to the Network tab, filter by XHR/fetch, and scroll the meetings list manually. Look for requests that return meeting data (likely JSON). The endpoint and payload can be used for direct API extraction if needed.")

            # Step 1: Log all possible scrollable containers
            containers = self.driver.find_elements(By.CSS_SELECTOR, 'div')
            scrollable_candidates = []
            for idx, div in enumerate(containers):
                try:
                    scroll_height = self.driver.execute_script('return arguments[0].scrollHeight', div)
                    client_height = self.driver.execute_script('return arguments[0].clientHeight', div)
                    overflow = self.driver.execute_script('return window.getComputedStyle(arguments[0]).overflow', div)
                    if scroll_height > client_height and overflow in ['auto', 'scroll']:
                        logger.info(f"Candidate scrollable div #{idx}: scrollHeight={scroll_height}, clientHeight={client_height}, overflow={overflow}")
                        scrollable_candidates.append(div)
                except Exception as e:
                    logger.warning(f"Error checking div #{idx}: {e}")
            if not scrollable_candidates:
                logger.warning("No scrollable divs found. Will fallback to window scrolling.")

            # Step 2: Incremental scrolling with simulated mouse wheel events
            last_count = 0
            scroll_attempt = 0
            no_new_count = 0
            max_no_new = 3
            step_size = 300
            while True:
                meeting_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[data-testid="conversation-title-Link"]')
                logger.info(f"Scroll attempt {scroll_attempt+1}: Found {len(meeting_links)} meetings so far.")
                scrolled = False
                for idx, container in enumerate(scrollable_candidates):
                    try:
                        # Simulate mouse wheel event using ActionChains
                        actions = ActionChains(self.driver)
                        actions.move_to_element(container).click().perform()
                        for _ in range(3):
                            actions.send_keys(Keys.PAGE_DOWN).perform()
                            logger.info(f"Simulated PAGE_DOWN on candidate container #{idx}")
                            time.sleep(0.2)
                        scrolled = True
                    except Exception as e:
                        logger.warning(f"Could not simulate mouse wheel on candidate container #{idx}: {e}")
                if not scrolled:
                    # Fallback: send PAGE_DOWN to body
                    try:
                        body = self.driver.find_element(By.TAG_NAME, 'body')
                        actions = ActionChains(self.driver)
                        actions.move_to_element(body).click().perform()
                        for _ in range(3):
                            actions.send_keys(Keys.PAGE_DOWN).perform()
                            logger.info("Simulated PAGE_DOWN on window/body")
                            time.sleep(0.2)
                    except Exception as e:
                        logger.warning(f"Could not simulate mouse wheel on window/body: {e}")
                time.sleep(2)
                # Step 3: Scroll last meeting link into view
                meeting_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[data-testid="conversation-title-Link"]')
                if meeting_links:
                    try:
                        self.driver.execute_script('arguments[0].scrollIntoView({behavior: "smooth", block: "end"});', meeting_links[-1])
                        logger.info("Scrolled last meeting link into view.")
                    except Exception as e:
                        logger.warning(f"Could not scroll last meeting link into view: {e}")
                new_count = len(meeting_links)
                logger.info(f"After scroll {scroll_attempt+1}: Meetings loaded so far: {new_count}")
                if new_count == last_count:
                    no_new_count += 1
                    logger.info(f"No new meetings loaded. no_new_count={no_new_count}")
                else:
                    no_new_count = 0
                if no_new_count >= max_no_new:
                    logger.info("No new meetings loaded after several scrolls. Stopping scroll loop.")
                    break
                last_count = new_count
                scroll_attempt += 1

            # Now extract all meeting links
            meeting_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[data-testid="conversation-title-Link"]')
            print(f"All meetings loaded: {len(meeting_links)} meetings found.")
            meetings = []
            for link in meeting_links:
                url = link.get_attribute('href')
                title = link.text.strip()
                # Extract meeting ID from the URL (after /u/)
                match = re.search(r'/u/([\w\-]+)', url)
                meeting_id = match.group(1) if match else None
                # Extract the date from the title using regex
                date = None
                try:
                    # Example: '2025-05-16 at 13.00.36'
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2}) at (\d{2}\.\d{2}\.\d{2})', title)
                    if date_match:
                        date_str = f"{date_match.group(1)} {date_match.group(2).replace('.', ':')}"
                        try:
                            date = str(dateutil.parser.parse(date_str, fuzzy=True))
                        except Exception:
                            date = date_str
                except Exception:
                    pass
                meetings.append({'id': meeting_id, 'url': url, 'title': title, 'date': date})
            logger.info(f"Found {len(meetings)} meetings.")
            return meetings
        except Exception as e:
            logger.error(f"Failed to extract meetings: {e}")
            # Save screenshot and HTML for debugging
            os.makedirs('logs', exist_ok=True)
            screenshot_path = os.path.join('logs', 'meetings_page.png')
            html_path = os.path.join('logs', 'meetings_page.html')
            self.driver.save_screenshot(screenshot_path)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info(f"Saved screenshot to {screenshot_path} and HTML to {html_path}")
            return []
    
    def get_meeting_details(self, meeting_id):
        """
        Extract transcript, summary, action items, and insights for a specific meeting.
        
        Args:
            meeting_id: The ID of the meeting to extract data for
            
        Returns:
            Dictionary containing transcript, summary, action items, and insights
        """
        try:
            meeting_url = f'https://otter.ai/u/{meeting_id}'
            logger.info(f"Navigating to meeting: {meeting_url}")
            self.driver.get(meeting_url)
            wait = WebDriverWait(self.driver, 40)

            # Click the 'Summary' tab if present
            try:
                summary_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Summary')]")))
                summary_tab.click()
                logger.info("Clicked 'Summary' tab")
            except Exception as e:
                logger.warning(f"Could not click 'Summary' tab: {e}")

            # Wait for summary/overview to load
            time.sleep(2)  # Let the DOM update

            # Extract Overview (Summary) using data-testid
            summary_text = None
            try:
                summary_el = self.driver.find_element(By.CSS_SELECTOR, 'div[data-testid="abstract-summary-edit-container"]')
                summary_text = summary_el.text.strip()
            except Exception as e:
                logger.warning(f"Could not extract summary/overview: {e}")

            # Extract Action Items using robust selector
            action_items = []
            try:
                for li in self.driver.find_elements(By.CSS_SELECTOR, 'ul[data-testid="action-items-list"] > li'):
                    action_items.append(li.text.strip())
            except Exception as e:
                logger.warning(f"Could not extract action items: {e}")

            # Extract Insights using robust selector
            insights = []
            try:
                for li in self.driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="insights-container"] li'):
                    insights.append(li.text.strip())
            except Exception as e:
                logger.warning(f"Could not extract insights: {e}")

            # Extract transcript using provided structure
            transcript = []
            try:
                transcript_tab = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Transcript')]")))
                transcript_tab.click()
                logger.info("Clicked 'Transcript' tab")
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".conversation-transcript-snippet-container")))

                # --- SCROLL TO LOAD FULL TRANSCRIPT ---
                # Find the scrollable transcript container
                try:
                    transcript_container = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="conversation-transcript-container"]')
                except Exception:
                    # Fallback: try to find the parent of a snippet
                    try:
                        first_snippet = self.driver.find_element(By.CSS_SELECTOR, ".conversation-transcript-snippet-container")
                        transcript_container = first_snippet.find_element(By.XPATH, "..")
                    except Exception:
                        transcript_container = None
                if transcript_container:
                    last_count = -1
                    no_new_count = 0
                    max_no_new = 3
                    while True:
                        snippets = self.driver.find_elements(By.CSS_SELECTOR, ".conversation-transcript-snippet-container")
                        count = len(snippets)
                        if count == last_count:
                            no_new_count += 1
                        else:
                            no_new_count = 0
                        if no_new_count >= max_no_new:
                            break
                        last_count = count
                        # Scroll to bottom
                        self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", transcript_container)
                        time.sleep(1)
                    logger.info(f"Loaded all transcript snippets: {last_count}")
                else:
                    logger.warning("Could not find transcript container for scrolling. Proceeding without scroll.")
                # --- END SCROLL LOGIC ---

                for snippet in self.driver.find_elements(By.CSS_SELECTOR, ".conversation-transcript-snippet-container"):
                    try:
                        speaker = snippet.find_element(By.CSS_SELECTOR, ".transcript-snippet__content__head__speaker-name").text.strip()
                    except Exception:
                        speaker = None
                    try:
                        timestamp = snippet.find_element(By.CSS_SELECTOR, ".transcript-snippet__content__head__timestamp-meta").text.strip()
                    except Exception:
                        timestamp = None
                    try:
                        words = [w.text for w in snippet.find_elements(By.CSS_SELECTOR, ".transcript-snippet__content__body__word")]
                        text = " ".join(words).strip()
                    except Exception:
                        text = snippet.text
                    transcript.append({"speaker": speaker, "timestamp": timestamp, "text": text})
            except Exception as e:
                logger.warning(f"Could not extract transcript: {e}")

            # Extract meeting date from header with class 'head-bar --conversation-opened'
            meeting_date = None
            try:
                header = self.driver.find_element(By.CSS_SELECTOR, 'header.head-bar.--conversation-opened')
                header_text = header.text
                # Example: 'May 16 at 2:17 pm'
                date_match = re.search(r'([A-Za-z]{3,9} \d{1,2} at \d{1,2}:\d{2} (am|pm))', header_text)
                if date_match:
                    date_str = date_match.group(1)
                    try:
                        meeting_date = str(dateutil.parser.parse(date_str, fuzzy=True))
                    except Exception:
                        meeting_date = date_str
            except Exception as e:
                logger.warning(f"Could not extract meeting date: {e}")

            return {
                "summary": summary_text,
                "action_items": action_items,
                "insights": insights,
                "transcript": transcript,
                "date": meeting_date
            }
        except Exception as e:
            logger.error(f"Failed to extract meeting details: {e}")
            return None
    
    def export_meetings_data(self, meetings, output_dir='data'):
        """
        Export meeting data to files.
        
        Args:
            meetings: List of meeting metadata
            output_dir: Directory to save the files
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Save the list of meetings as JSON
        with open(os.path.join(output_dir, 'meetings.json'), 'w') as f:
            json.dump(meetings, f, indent=2, default=str)
            
        # Extract and save details for each meeting
        for meeting in meetings:
            meeting_id = meeting['id']
            try:
                logger.info(f"Extracting details for meeting: {meeting['title']}")
                details = self.get_meeting_details(meeting_id)
                if not details:
                    logger.error(f"No details returned for meeting {meeting_id} ({meeting.get('title')}, {meeting.get('url')}, {meeting.get('date')})")
                    # Save debug artifacts
                    error_dir = os.path.join('logs', 'errors', meeting_id)
                    os.makedirs(error_dir, exist_ok=True)
                    screenshot_path = os.path.join(error_dir, 'error_screenshot.png')
                    html_path = os.path.join(error_dir, 'error_page.html')
                    try:
                        self.driver.save_screenshot(screenshot_path)
                        with open(html_path, 'w', encoding='utf-8') as f:
                            f.write(self.driver.page_source)
                        logger.info(f"Saved error screenshot to {screenshot_path} and HTML to {html_path}")
                    except Exception as artifact_e:
                        logger.error(f"Failed to save error artifacts for meeting {meeting_id}: {artifact_e}")
                    continue
                # Save as individual files
                meeting_dir = os.path.join(output_dir, meeting_id)
                os.makedirs(meeting_dir, exist_ok=True)
                # Save transcript
                with open(os.path.join(meeting_dir, 'transcript.txt'), 'w') as f:
                    f.write("\n".join([f"{item['speaker']} - {item['timestamp']}: {item['text']}" for item in details['transcript']]))
                # Save summary
                if details['summary']:
                    with open(os.path.join(meeting_dir, 'summary.txt'), 'w') as f:
                        f.write(details['summary'])
                # Save action items
                if details['action_items']:
                    with open(os.path.join(meeting_dir, 'action_items.json'), 'w') as f:
                        json.dump(details['action_items'], f, indent=2)
                # Save all details as one JSON file
                with open(os.path.join(meeting_dir, 'details.json'), 'w') as f:
                    json.dump(details, f, indent=2, default=str)
                logger.info(f"Saved details for meeting: {meeting['title']}")
            except Exception as e:
                import traceback
                logger.error(f"Error saving details for meeting {meeting_id} ({meeting.get('title')}, {meeting.get('url')}, {meeting.get('date')}): {e}")
                logger.error(traceback.format_exc())
                # Save debug artifacts
                error_dir = os.path.join('logs', 'errors', meeting_id)
                os.makedirs(error_dir, exist_ok=True)
                screenshot_path = os.path.join(error_dir, 'error_screenshot.png')
                html_path = os.path.join(error_dir, 'error_page.html')
                try:
                    self.driver.save_screenshot(screenshot_path)
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    logger.info(f"Saved error screenshot to {screenshot_path} and HTML to {html_path}")
                except Exception as artifact_e:
                    logger.error(f"Failed to save error artifacts for meeting {meeting_id}: {artifact_e}")
    
    def close(self):
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()

def main():
    """Main function for Otter.ai Selenium automation."""
    parser = argparse.ArgumentParser(description='Automate Otter.ai login and data extraction')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--limit', type=int, default=5, help='Maximum number of meetings to extract')
    parser.add_argument('--output', default='data', help='Directory to save extracted data')
    parser.add_argument('--profile-dir', default=None, help='Path to Chrome user profile directory for session reuse')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    otter = OtterSelenium(browser='chrome', headless=args.headless)
    otter.profile_dir = args.profile_dir
    
    try:
        # Set up the WebDriver
        otter.setup_driver()
        
        # Login with Apple
        if otter.login_with_apple():
            logger.info("Successfully logged in to Otter.ai")
            
            # Get all meetings
            meetings = otter.get_all_meetings()
            if meetings:
                logger.info(f"Found {len(meetings)} meetings")
                print(f"Meetings found: {len(meetings)}")
                for m in meetings:
                    print(f"- {m['title']} | {m['date']} | {m['url']}")
            else:
                logger.warning("No meetings found")
                
        else:
            logger.error("Failed to log in to Otter.ai")
            
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        
    finally:
        # Always close the browser
        otter.close()

if __name__ == "__main__":
    main() 