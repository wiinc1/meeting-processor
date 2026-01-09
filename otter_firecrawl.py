#!/usr/bin/env python
"""
Otter.ai scraper using Firecrawl for enhanced web scraping capabilities.
This provides an alternative to Selenium-based scraping with better JavaScript handling
and structured data extraction.
"""

import os
import time
import logging
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Any
from firecrawl import Firecrawl
import dateutil.parser
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OtterFirecrawl:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Firecrawl scraper for Otter.ai.
        
        Args:
            api_key: Firecrawl API key. If not provided, will try to get from environment.
        """
        # Load environment variables
        load_dotenv()
        
        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv('FIRECRAWL_API_KEY')
        if not self.api_key:
            raise ValueError("Firecrawl API key is required. Set FIRECRAWL_API_KEY environment variable or pass api_key parameter.")
        
        # Initialize Firecrawl client
        try:
            self.app = Firecrawl(api_key=self.api_key)
            logger.info("Successfully initialized Firecrawl client")
        except Exception as e:
            logger.error(f"Failed to initialize Firecrawl client: {e}")
            raise
        
        self.base_url = 'https://otter.ai'
        self.login_url = 'https://otter.ai/signin'
        self.home_url = 'https://otter.ai/home'
        
    def authenticate(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Authenticate with Otter.ai using Firecrawl's session management.
        
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
            
            logger.info("Attempting to authenticate with Otter.ai using Firecrawl")
            
            # Use Firecrawl to handle the login process
            # This will handle JavaScript rendering and session management
            login_data = {
                'username': username,
                'password': password
            }
            
            # Firecrawl can handle form submissions and JavaScript
            result = self.app.scrape(
                url=self.login_url,
                formats=['markdown', 'json'],
                wait_for=3000,  # Wait 3 seconds for page to load
                actions=[
                    {
                        "type": "fill",
                        "selector": "input[name='username'], input[type='email']",
                        "value": username
                    },
                    {
                        "type": "fill", 
                        "selector": "input[name='password'], input[type='password']",
                        "value": password
                    },
                    {
                        "type": "click",
                        "selector": "button[type='submit'], input[type='submit']"
                    }
                ]
            )
            
            if result and result.get('success'):
                logger.info("Successfully authenticated with Otter.ai")
                return True
            else:
                logger.error("Authentication failed")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def get_all_meetings(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Extract all available meetings from Otter.ai using Firecrawl.
        
        Args:
            limit: Maximum number of meetings to retrieve
            
        Returns:
            List of meeting dictionaries with metadata
        """
        try:
            logger.info("Scraping meetings list from Otter.ai using Firecrawl")
            
            # Use Firecrawl to scrape the home page with JavaScript rendering
            result = self.app.scrape(
                url=self.home_url,
                formats=['markdown', 'json'],
                wait_for=5000,  # Wait 5 seconds for dynamic content to load
                only_main_content=True,  # Focus on main content
                remove_base64_images=True,  # Remove base64 images to reduce payload
            )
            
            if not result or not result.get('success'):
                logger.error("Failed to scrape meetings page")
                return []
            
            # Extract meetings from the scraped content
            meetings = self._extract_meetings_from_content(result, limit)
            logger.info(f"Found {len(meetings)} meetings using Firecrawl")
            return meetings
            
        except Exception as e:
            logger.error(f"Failed to get meetings: {e}")
            return []
    
    def _extract_meetings_from_content(self, result: Dict, limit: int) -> List[Dict[str, Any]]:
        """
        Extract meeting data from Firecrawl result.
        
        Args:
            result: Firecrawl scrape result
            limit: Maximum number of meetings to extract
            
        Returns:
            List of meeting dictionaries
        """
        meetings = []
        
        try:
            # Try to extract from JSON format first
            if 'data' in result and 'json' in result['data']:
                json_data = result['data']['json']
                meetings = self._parse_meetings_from_json(json_data, limit)
            
            # Fallback to markdown parsing if JSON doesn't work
            if not meetings and 'data' in result and 'markdown' in result['data']:
                markdown_content = result['data']['markdown']
                meetings = self._parse_meetings_from_markdown(markdown_content, limit)
            
            # Fallback to HTML parsing if markdown doesn't work
            if not meetings and 'data' in result and 'html' in result['data']:
                html_content = result['data']['html']
                meetings = self._parse_meetings_from_html(html_content, limit)
                
        except Exception as e:
            logger.error(f"Error extracting meetings from content: {e}")
        
        return meetings[:limit]  # Limit results
    
    def _parse_meetings_from_json(self, json_data: Dict, limit: int) -> List[Dict[str, Any]]:
        """Parse meetings from JSON data."""
        meetings = []
        try:
            # Look for common patterns in Otter.ai's JSON structure
            if isinstance(json_data, dict):
                # Try different possible keys for meetings data
                for key in ['meetings', 'conversations', 'speeches', 'data']:
                    if key in json_data and isinstance(json_data[key], list):
                        for item in json_data[key][:limit]:
                            meeting = self._parse_meeting_item(item)
                            if meeting:
                                meetings.append(meeting)
                        break
        except Exception as e:
            logger.warning(f"Error parsing JSON meetings: {e}")
        return meetings
    
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
    
    def _parse_meeting_item(self, item: Dict) -> Optional[Dict[str, Any]]:
        """Parse a single meeting item from JSON data."""
        try:
            meeting_id = item.get('id') or item.get('speech_id') or item.get('conversation_id')
            title = item.get('title') or item.get('name') or 'Untitled Meeting'
            url = item.get('url') or f"https://otter.ai/u/{meeting_id}"
            date = item.get('created_at') or item.get('date') or item.get('timestamp')
            
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
    
    def get_meeting_details(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """
        Extract detailed information for a specific meeting using Firecrawl.
        
        Args:
            meeting_id: The ID of the meeting to extract
            
        Returns:
            Dictionary containing transcript, summary, action items, and insights
        """
        try:
            meeting_url = f'https://otter.ai/u/{meeting_id}'
            logger.info(f"Scraping meeting details from: {meeting_url}")
            
            # Use Firecrawl to scrape the meeting page
            result = self.app.scrape(
                url=meeting_url,
                formats=['markdown', 'json'],
                wait_for=5000,  # Wait for dynamic content to load
                only_main_content=True,
                remove_base64_images=True,
            )
            
            if not result or not result.get('success'):
                logger.error(f"Failed to scrape meeting {meeting_id}")
                return None
            
            # Extract structured data from the result
            details = self._extract_meeting_details_from_content(result)
            logger.info(f"Successfully extracted details for meeting {meeting_id}")
            return details
            
        except Exception as e:
            logger.error(f"Failed to get meeting details for {meeting_id}: {e}")
            return None
    
    def _extract_meeting_details_from_content(self, result: Dict) -> Dict[str, Any]:
        """
        Extract meeting details from Firecrawl result.
        
        Args:
            result: Firecrawl scrape result
            
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
            # Try to extract from JSON format first
            if 'data' in result and 'json' in result['data']:
                json_data = result['data']['json']
                details.update(self._parse_details_from_json(json_data))
            
            # Fallback to markdown parsing
            if 'data' in result and 'markdown' in result['data']:
                markdown_content = result['data']['markdown']
                details.update(self._parse_details_from_markdown(markdown_content))
            
            # Fallback to HTML parsing
            if 'data' in result and 'html' in result['data']:
                html_content = result['data']['html']
                details.update(self._parse_details_from_html(html_content))
                
        except Exception as e:
            logger.error(f"Error extracting meeting details: {e}")
        
        return details
    
    def _parse_details_from_json(self, json_data: Dict) -> Dict[str, Any]:
        """Parse meeting details from JSON data."""
        details = {}
        try:
            # Look for common patterns in Otter.ai's JSON structure
            if 'summary' in json_data:
                details['summary'] = json_data['summary']
            if 'action_items' in json_data:
                details['action_items'] = json_data['action_items']
            if 'insights' in json_data:
                details['insights'] = json_data['insights']
            if 'transcript' in json_data:
                details['transcript'] = json_data['transcript']
        except Exception as e:
            logger.warning(f"Error parsing JSON details: {e}")
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
    
    def export_meetings_data(self, meetings: List[Dict], output_dir: str = 'data') -> None:
        """
        Export meeting data to files using Firecrawl's structured output.
        
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


def main():
    """Main function for Otter.ai Firecrawl automation."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Automate Otter.ai data extraction using Firecrawl')
    parser.add_argument('--limit', type=int, default=5, help='Maximum number of meetings to extract')
    parser.add_argument('--output', default='data', help='Directory to save extracted data')
    parser.add_argument('--api-key', help='Firecrawl API key (optional, can use env var)')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Initialize Firecrawl scraper
        otter = OtterFirecrawl(api_key=args.api_key)
        
        # Authenticate (optional - may work without credentials)
        if otter.authenticate():
            logger.info("Authentication successful")
        else:
            logger.warning("Authentication failed, but continuing...")
        
        # Get all meetings
        meetings = otter.get_all_meetings(limit=args.limit)
        if meetings:
            logger.info(f"Found {len(meetings)} meetings")
            print(f"Meetings found: {len(meetings)}")
            for m in meetings:
                print(f"- {m['title']} | {m.get('date', 'No date')} | {m['url']}")
            
            # Export meeting data
            otter.export_meetings_data(meetings, args.output)
            logger.info(f"Exported {len(meetings)} meetings to {args.output}")
        else:
            logger.warning("No meetings found")
            
    except Exception as e:
        logger.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()




