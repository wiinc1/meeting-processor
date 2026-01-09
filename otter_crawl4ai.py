#!/usr/bin/env python
"""
Otter.ai scraper using Crawl4AI for enhanced web scraping capabilities.
Crawl4AI provides fast, efficient scraping with advanced JavaScript handling
and built-in content extraction features.
"""

import os
import time
import logging
import json
import re
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Any
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.extraction_strategy import LLMExtractionStrategy
import dateutil.parser
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OtterCrawl4AI:
    def __init__(self, headless: bool = True, browser_type: str = 'chromium'):
        """
        Initialize Crawl4AI scraper for Otter.ai.
        
        Args:
            headless: Whether to run browser in headless mode
            browser_type: Browser to use ('chromium', 'firefox', 'webkit')
        """
        # Load environment variables
        load_dotenv()
        
        self.headless = headless
        self.browser_type = browser_type
        self.crawler = None
        self.base_url = 'https://otter.ai'
        self.login_url = 'https://otter.ai/signin'
        self.home_url = 'https://otter.ai/home'
        
        logger.info(f"Initialized Crawl4AI scraper with {browser_type} browser (headless={headless})")
    
    async def _get_crawler(self):
        """Get or create crawler instance."""
        if self.crawler is None:
            self.crawler = AsyncWebCrawler(
                headless=self.headless,
                browser_type=self.browser_type,
                verbose=True
            )
        return self.crawler
    
    async def authenticate(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Authenticate with Otter.ai using Crawl4AI's session management.
        
        Args:
            username: Otter.ai username (optional, will use env var if not provided)
            password: Otter.ai password (optional, will use env var if not provided)
            
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            # Get credentials from parameters or environment
            username = username or os.getenv('OTTER_USERNAME')
            password = password or os.getenv('OTTER_PASSWORD')
            
            if not username or not password:
                logger.warning("No Otter.ai credentials provided. You may need to manually authenticate.")
                return True  # Allow proceeding without credentials for manual auth
            
            logger.info("Attempting to authenticate with Otter.ai using Crawl4AI")
            
            crawler = await self._get_crawler()
            
            # Navigate to login page
            result = await crawler.arun(
                url=self.login_url,
                wait_for="networkidle",
                delay_before_return_html=2.0
            )
            
            if not result.success:
                logger.error("Failed to load login page")
                return False
            
            # Look for Apple login button and click it
            apple_button_selector = "button:has-text('Continue with Apple'), button:has-text('Sign in with Apple'), [data-testid*='apple']"
            
            # Try to find and click Apple login button
            try:
                # Use JavaScript to find and click the Apple button
                js_script = """
                const appleButton = document.querySelector('button:has-text("Continue with Apple")') || 
                                 document.querySelector('button:has-text("Sign in with Apple")') ||
                                 document.querySelector('[data-testid*="apple"]') ||
                                 document.querySelector('button[class*="apple"]');
                if (appleButton) {
                    appleButton.click();
                    return true;
                }
                return false;
                """
                
                # Use JavaScript execution through arun
                result = await crawler.arun(
                    url=self.login_url,
                    js_code=js_script,
                    wait_for="networkidle",
                    delay_before_return_html=2.0
                )
                
                # Check if we're on Apple's login page
                if result.success and 'appleid.apple.com' in result.url:
                    logger.info("Successfully navigated to Apple login page")
                    # For now, we'll assume manual authentication is needed
                    logger.info("Please complete Apple authentication manually in the browser")
                    return True
                else:
                    logger.warning("Apple login button not found or not clicked")
                    return False
                    
            except Exception as e:
                logger.error(f"Error during Apple login: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    async def get_all_meetings(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Extract all available meetings from Otter.ai using Crawl4AI.
        
        Args:
            limit: Maximum number of meetings to retrieve
            
        Returns:
            List of meeting dictionaries with metadata
        """
        try:
            logger.info("Scraping meetings list from Otter.ai using Crawl4AI")
            
            crawler = await self._get_crawler()
            
            # Configure extraction strategy for meetings
            from crawl4ai.extraction_strategy import LLMExtractionStrategy
            
            extraction_strategy = LLMExtractionStrategy(
                provider="ollama/llama3.2",  # Use local LLM if available
                api_key="",  # Not needed for local LLM
                instruction="""
                Extract all meeting information from this page. For each meeting, provide:
                - title: The meeting title
                - url: The full URL to the meeting
                - date: The meeting date if available
                - id: Extract the meeting ID from the URL
                
                Return the data as a JSON array of meeting objects.
                """,
                schema={
                    "type": "object",
                    "properties": {
                        "meetings": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "url": {"type": "string"},
                                    "date": {"type": "string"},
                                    "id": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            )
            
            # Scrape the home page
            result = await crawler.arun(
                url=self.home_url,
                wait_for="networkidle",
                delay_before_return_html=3.0,
                extraction_strategy=extraction_strategy
            )
            
            if not result.success:
                logger.error("Failed to scrape meetings page")
                return []
            
            # Extract meetings from the result
            meetings = self._extract_meetings_from_result(result, limit)
            logger.info(f"Found {len(meetings)} meetings using Crawl4AI")
            return meetings
            
        except Exception as e:
            logger.error(f"Failed to get meetings: {e}")
            return []
    
    def _extract_meetings_from_result(self, result, limit: int) -> List[Dict[str, Any]]:
        """
        Extract meeting data from Crawl4AI result.
        
        Args:
            result: Crawl4AI scrape result
            limit: Maximum number of meetings to extract
            
        Returns:
            List of meeting dictionaries
        """
        meetings = []
        
        try:
            # Try to extract from LLM extraction first
            if hasattr(result, 'extracted_content') and result.extracted_content:
                try:
                    extracted_data = json.loads(result.extracted_content)
                    if 'meetings' in extracted_data:
                        for meeting in extracted_data['meetings'][:limit]:
                            meetings.append(self._parse_meeting_item(meeting))
                except json.JSONDecodeError:
                    pass
            
            # Fallback to HTML parsing
            if not meetings and hasattr(result, 'html') and result.html:
                meetings = self._parse_meetings_from_html(result.html, limit)
            
            # Fallback to markdown parsing
            if not meetings and hasattr(result, 'markdown') and result.markdown:
                meetings = self._parse_meetings_from_markdown(result.markdown, limit)
                
        except Exception as e:
            logger.error(f"Error extracting meetings from result: {e}")
        
        return meetings[:limit]
    
    def _parse_meeting_item(self, item: Dict) -> Dict[str, Any]:
        """Parse a single meeting item from extracted data."""
        try:
            meeting_id = item.get('id') or self._extract_meeting_id_from_url(item.get('url', ''))
            title = item.get('title', 'Untitled Meeting')
            url = item.get('url', f"https://otter.ai/u/{meeting_id}")
            date = item.get('date')
            
            if meeting_id:
                return {
                    'id': meeting_id,
                    'title': title,
                    'url': url,
                    'date': self._parse_date(date) if date else None
                }
        except Exception as e:
            logger.warning(f"Error parsing meeting item: {e}")
        return None
    
    def _parse_meetings_from_html(self, html_content: str, limit: int) -> List[Dict[str, Any]]:
        """Parse meetings from HTML content."""
        meetings = []
        try:
            # Use regex to find meeting links in HTML
            url_pattern = r'href="([^"]*otter\.ai/u/([^"]+))"[^>]*>([^<]+)</a>'
            matches = re.findall(url_pattern, html_content)
            
            for match in matches:
                url, meeting_id, title = match
                meetings.append({
                    'id': meeting_id,
                    'title': title.strip(),
                    'url': url,
                    'date': self._extract_date_from_title(title)
                })
        except Exception as e:
            logger.warning(f"Error parsing HTML meetings: {e}")
        return meetings[:limit]
    
    def _parse_meetings_from_markdown(self, markdown_content: str, limit: int) -> List[Dict[str, Any]]:
        """Parse meetings from markdown content."""
        meetings = []
        try:
            lines = markdown_content.split('\n')
            for line in lines:
                # Look for meeting links and titles
                if 'otter.ai/u/' in line:
                    # Extract URL and title from markdown links
                    url_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', line)
                    if url_match:
                        title = url_match.group(1)
                        url = url_match.group(2)
                        meeting_id = self._extract_meeting_id_from_url(url)
                        if meeting_id:
                            meetings.append({
                                'id': meeting_id,
                                'title': title,
                                'url': url,
                                'date': self._extract_date_from_title(title)
                            })
        except Exception as e:
            logger.warning(f"Error parsing markdown meetings: {e}")
        return meetings[:limit]
    
    def _extract_meeting_id_from_url(self, url: str) -> Optional[str]:
        """Extract meeting ID from Otter.ai URL."""
        match = re.search(r'/u/([^/?]+)', url)
        return match.group(1) if match else None
    
    def _extract_date_from_title(self, title: str) -> Optional[str]:
        """Extract date from meeting title."""
        try:
            # Look for date patterns in title
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
                r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
                r'([A-Za-z]{3,9} \d{1,2}, \d{4})',  # Month DD, YYYY
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, title)
                if match:
                    date_str = match.group(1)
                    try:
                        parsed_date = dateutil.parser.parse(date_str, fuzzy=True)
                        return parsed_date.strftime('%Y-%m-%d')
                    except:
                        continue
        except Exception:
            pass
        return None
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to standardized format."""
        try:
            if date_str:
                parsed_date = dateutil.parser.parse(date_str, fuzzy=True)
                return parsed_date.strftime('%Y-%m-%d')
        except Exception:
            pass
        return None
    
    async def get_meeting_details(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """
        Extract detailed information for a specific meeting using Crawl4AI.
        
        Args:
            meeting_id: The ID of the meeting to extract
            
        Returns:
            Dictionary containing transcript, summary, action items, and insights
        """
        try:
            meeting_url = f'https://otter.ai/u/{meeting_id}'
            logger.info(f"Scraping meeting details from: {meeting_url}")
            
            crawler = await self._get_crawler()
            
            # Configure extraction strategy for meeting details
            extraction_strategy = LLMExtractionStrategy(
                provider="ollama/llama3.2",  # Use local LLM if available
                api_token="",  # Not needed for local LLM
                instruction="""
                Extract detailed meeting information from this Otter.ai transcript page. Provide:
                - summary: The meeting summary/overview
                - action_items: List of action items mentioned
                - insights: List of key insights
                - transcript: The full transcript text
                
                Return the data as a JSON object with these fields.
                """,
                schema={
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "action_items": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "insights": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "transcript": {"type": "string"}
                    }
                }
            )
            
            # Scrape the meeting page
            result = await crawler.arun(
                url=meeting_url,
                wait_for="networkidle",
                delay_before_return_html=3.0,
                extraction_strategy=extraction_strategy
            )
            
            if not result.success:
                logger.error(f"Failed to scrape meeting {meeting_id}")
                return None
            
            # Extract structured data from the result
            details = self._extract_meeting_details_from_result(result)
            logger.info(f"Successfully extracted details for meeting {meeting_id}")
            return details
            
        except Exception as e:
            logger.error(f"Failed to get meeting details for {meeting_id}: {e}")
            return None
    
    def _extract_meeting_details_from_result(self, result) -> Dict[str, Any]:
        """
        Extract meeting details from Crawl4AI result.
        
        Args:
            result: Crawl4AI scrape result
            
        Returns:
            Dictionary with meeting details
        """
        details = {
            'summary': None,
            'action_items': [],
            'insights': [],
            'transcript': [],
            'date': None
        }
        
        try:
            # Try to extract from LLM extraction first
            if hasattr(result, 'extracted_content') and result.extracted_content:
                try:
                    extracted_data = json.loads(result.extracted_content)
                    details.update({
                        'summary': extracted_data.get('summary'),
                        'action_items': extracted_data.get('action_items', []),
                        'insights': extracted_data.get('insights', []),
                        'transcript': [{'text': extracted_data.get('transcript', '')}]
                    })
                except json.JSONDecodeError:
                    pass
            
            # Fallback to HTML parsing
            if not details['summary'] and hasattr(result, 'html') and result.html:
                details.update(self._parse_details_from_html(result.html))
            
            # Fallback to markdown parsing
            if not details['summary'] and hasattr(result, 'markdown') and result.markdown:
                details.update(self._parse_details_from_markdown(result.markdown))
                
        except Exception as e:
            logger.error(f"Error extracting meeting details: {e}")
        
        return details
    
    def _parse_details_from_html(self, html_content: str) -> Dict[str, Any]:
        """Parse meeting details from HTML content."""
        details = {}
        try:
            # Use regex to extract content from HTML
            # This is a simplified parser - you might need to adjust based on Otter.ai's HTML structure
            
            # Extract summary
            summary_match = re.search(r'<div[^>]*class="[^"]*summary[^"]*"[^>]*>(.*?)</div>', html_content, re.DOTALL)
            if summary_match:
                details['summary'] = re.sub(r'<[^>]+>', '', summary_match.group(1)).strip()
            
            # Extract action items
            action_items = []
            action_matches = re.findall(r'<li[^>]*class="[^"]*action[^"]*"[^>]*>(.*?)</li>', html_content, re.DOTALL)
            for match in action_matches:
                action_items.append(re.sub(r'<[^>]+>', '', match).strip())
            if action_items:
                details['action_items'] = action_items
            
            # Extract insights
            insights = []
            insight_matches = re.findall(r'<li[^>]*class="[^"]*insight[^"]*"[^>]*>(.*?)</li>', html_content, re.DOTALL)
            for match in insight_matches:
                insights.append(re.sub(r'<[^>]+>', '', match).strip())
            if insights:
                details['insights'] = insights
                
        except Exception as e:
            logger.warning(f"Error parsing HTML details: {e}")
        return details
    
    def _parse_details_from_markdown(self, markdown_content: str) -> Dict[str, Any]:
        """Parse meeting details from markdown content."""
        details = {}
        try:
            lines = markdown_content.split('\n')
            current_section = None
            transcript = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Detect sections
                if 'summary' in line.lower() or 'overview' in line.lower():
                    current_section = 'summary'
                    continue
                elif 'action' in line.lower() and 'item' in line.lower():
                    current_section = 'action_items'
                    continue
                elif 'insight' in line.lower():
                    current_section = 'insights'
                    continue
                elif 'transcript' in line.lower():
                    current_section = 'transcript'
                    continue
                
                # Extract content based on current section
                if current_section == 'summary' and not details.get('summary'):
                    details['summary'] = line
                elif current_section == 'action_items':
                    if line.startswith('-') or line.startswith('*'):
                        details.setdefault('action_items', []).append(line[1:].strip())
                elif current_section == 'insights':
                    if line.startswith('-') or line.startswith('*'):
                        details.setdefault('insights', []).append(line[1:].strip())
                elif current_section == 'transcript':
                    # Parse transcript lines
                    if ':' in line:
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            speaker = parts[0].strip()
                            text = parts[1].strip()
                            transcript.append({
                                'speaker': speaker,
                                'text': text,
                                'timestamp': None
                            })
            
            if transcript:
                details['transcript'] = transcript
                
        except Exception as e:
            logger.warning(f"Error parsing markdown details: {e}")
        return details
    
    async def export_meetings_data(self, meetings: List[Dict], output_dir: str = 'data') -> None:
        """
        Export meeting data to files using Crawl4AI's structured output.
        
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
                details = await self.get_meeting_details(meeting_id)
                if not details:
                    logger.error(f"No details returned for meeting {meeting_id}")
                    continue
                
                # Save as individual files
                meeting_dir = os.path.join(output_dir, meeting_id)
                os.makedirs(meeting_dir, exist_ok=True)
                
                # Save transcript
                if details.get('transcript'):
                    with open(os.path.join(meeting_dir, 'transcript.txt'), 'w') as f:
                        if isinstance(details['transcript'], list):
                            transcript_text = '\n'.join([
                                f"{item.get('speaker', 'Unknown')}: {item.get('text', '')}"
                                for item in details['transcript']
                            ])
                        else:
                            transcript_text = str(details['transcript'])
                        f.write(transcript_text)
                
                # Save summary
                if details.get('summary'):
                    with open(os.path.join(meeting_dir, 'summary.txt'), 'w') as f:
                        f.write(details['summary'])
                
                # Save action items
                if details.get('action_items'):
                    with open(os.path.join(meeting_dir, 'action_items.json'), 'w') as f:
                        json.dump(details['action_items'], f, indent=2)
                
                # Save all details as one JSON file
                with open(os.path.join(meeting_dir, 'details.json'), 'w') as f:
                    json.dump(details, f, indent=2, default=str)
                
                logger.info(f"Saved details for meeting: {meeting['title']}")
                
            except Exception as e:
                logger.error(f"Error saving details for meeting {meeting_id}: {e}")
    
    async def close(self):
        """Close the crawler."""
        if self.crawler:
            await self.crawler.close()
            self.crawler = None


async def main():
    """Main function for Otter.ai Crawl4AI automation."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Automate Otter.ai data extraction using Crawl4AI')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--browser', choices=['chromium', 'firefox', 'webkit'], 
                        default='chromium', help='Browser to use')
    parser.add_argument('--limit', type=int, default=5, help='Maximum number of meetings to extract')
    parser.add_argument('--output', default='data', help='Directory to save extracted data')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    scraper = None
    try:
        # Initialize Crawl4AI scraper
        scraper = OtterCrawl4AI(headless=args.headless, browser_type=args.browser)
        
        # Authenticate (optional - may work without credentials)
        if await scraper.authenticate():
            logger.info("Authentication successful")
        else:
            logger.warning("Authentication failed, but continuing...")
        
        # Get all meetings
        meetings = await scraper.get_all_meetings(limit=args.limit)
        if meetings:
            logger.info(f"Found {len(meetings)} meetings")
            print(f"Meetings found: {len(meetings)}")
            for m in meetings:
                print(f"- {m['title']} | {m.get('date', 'No date')} | {m['url']}")
            
            # Export meeting data
            await scraper.export_meetings_data(meetings, args.output)
            logger.info(f"Exported {len(meetings)} meetings to {args.output}")
        else:
            logger.warning("No meetings found")
            
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        if scraper:
            await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
