#!/usr/bin/env python
"""
Factory class for creating Otter.ai scrapers.
Supports both Selenium and Firecrawl backends with a unified interface.
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OtterScraperFactory:
    """Factory class for creating Otter.ai scrapers with different backends."""
    
    @staticmethod
    def create_scraper(backend: str = 'auto', **kwargs):
        """
        Create an Otter.ai scraper with the specified backend.
        
        Args:
            backend: Scraper backend ('selenium', 'firecrawl', 'crawl4ai', or 'auto')
            **kwargs: Additional arguments for the scraper
            
        Returns:
            Scraper instance
        """
        load_dotenv()
        
        if backend == 'auto':
            backend = OtterScraperFactory._detect_best_backend()
        
        if backend == 'firecrawl':
            return OtterScraperFactory._create_firecrawl_scraper(**kwargs)
        elif backend == 'crawl4ai':
            return OtterScraperFactory._create_crawl4ai_scraper(**kwargs)
        elif backend == 'selenium':
            return OtterScraperFactory._create_selenium_scraper(**kwargs)
        else:
            raise ValueError(f"Unknown backend: {backend}")
    
    @staticmethod
    def _detect_best_backend() -> str:
        """
        Automatically detect the best available backend.
        
        Returns:
            str: 'crawl4ai', 'firecrawl', or 'selenium'
        """
        # Check for Crawl4AI first (fastest and most capable)
        try:
            from crawl4ai import AsyncWebCrawler
            logger.info("Crawl4AI available, using Crawl4AI backend")
            return 'crawl4ai'
        except ImportError:
            pass
        
        # Check for Firecrawl API key
        firecrawl_key = os.getenv('FIRECRAWL_API_KEY')
        if firecrawl_key and firecrawl_key != 'your_firecrawl_api_key_here':
            logger.info("Firecrawl API key found, using Firecrawl backend")
            return 'firecrawl'
        
        # Check for Selenium dependencies
        try:
            from selenium import webdriver
            logger.info("Selenium available, using Selenium backend")
            return 'selenium'
        except ImportError:
            logger.warning("No suitable backend found, defaulting to Crawl4AI")
            return 'crawl4ai'
    
    @staticmethod
    def _create_firecrawl_scraper(**kwargs):
        """Create a Firecrawl-based scraper."""
        try:
            from otter_firecrawl import OtterFirecrawl
            api_key = kwargs.get('api_key') or os.getenv('FIRECRAWL_API_KEY')
            return OtterFirecrawl(api_key=api_key)
        except ImportError as e:
            logger.error(f"Failed to import Firecrawl scraper: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create Firecrawl scraper: {e}")
            raise
    
    @staticmethod
    def _create_crawl4ai_scraper(**kwargs):
        """Create a Crawl4AI-based scraper."""
        try:
            from otter_crawl4ai import OtterCrawl4AI
            headless = kwargs.get('headless', True)
            browser_type = kwargs.get('browser_type', 'chromium')
            return OtterCrawl4AI(headless=headless, browser_type=browser_type)
        except ImportError as e:
            logger.error(f"Failed to import Crawl4AI scraper: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create Crawl4AI scraper: {e}")
            raise
    
    @staticmethod
    def _create_selenium_scraper(**kwargs):
        """Create a Selenium-based scraper."""
        try:
            from otter_selenium import OtterSelenium
            browser = kwargs.get('browser', 'chrome')
            headless = kwargs.get('headless', False)
            profile_dir = kwargs.get('profile_dir')
            
            scraper = OtterSelenium(browser=browser, headless=headless)
            if profile_dir:
                scraper.profile_dir = profile_dir
            return scraper
        except ImportError as e:
            logger.error(f"Failed to import Selenium scraper: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to create Selenium scraper: {e}")
            raise


class UnifiedOtterScraper:
    """
    Unified interface for Otter.ai scraping that works with Selenium, Firecrawl, and Crawl4AI backends.
    """
    
    def __init__(self, backend: str = 'auto', **kwargs):
        """
        Initialize the unified scraper.
        
        Args:
            backend: Scraper backend ('selenium', 'firecrawl', 'crawl4ai', or 'auto')
            **kwargs: Additional arguments for the scraper
        """
        self.backend = backend
        self.scraper = OtterScraperFactory.create_scraper(backend, **kwargs)
        logger.info(f"Initialized Otter.ai scraper with {backend} backend")
    
    def setup(self):
        """Set up the scraper (only needed for Selenium)."""
        if hasattr(self.scraper, 'setup_driver'):
            self.scraper.setup_driver()
    
    async def authenticate(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Authenticate with Otter.ai.
        
        Args:
            username: Otter.ai username (optional)
            password: Otter.ai password (optional)
            
        Returns:
            bool: True if authentication successful
        """
        if hasattr(self.scraper, 'authenticate'):
            # Handle async authenticate (Crawl4AI)
            if asyncio.iscoroutinefunction(self.scraper.authenticate):
                return await self.scraper.authenticate(username, password)
            else:
                return self.scraper.authenticate(username, password)
        elif hasattr(self.scraper, 'login_with_apple'):
            return self.scraper.login_with_apple()
        else:
            logger.warning("No authentication method available")
            return True
    
    async def get_all_meetings(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all available meetings.
        
        Args:
            limit: Maximum number of meetings to retrieve
            
        Returns:
            List of meeting dictionaries
        """
        if hasattr(self.scraper, 'get_all_meetings'):
            # Handle async get_all_meetings (Crawl4AI)
            if asyncio.iscoroutinefunction(self.scraper.get_all_meetings):
                return await self.scraper.get_all_meetings(limit)
            else:
                return self.scraper.get_all_meetings(limit)
        else:
            logger.error("Scraper does not support get_all_meetings")
            return []
    
    async def get_meeting_details(self, meeting_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific meeting.
        
        Args:
            meeting_id: The ID of the meeting
            
        Returns:
            Dictionary with meeting details
        """
        if hasattr(self.scraper, 'get_meeting_details'):
            # Handle async get_meeting_details (Crawl4AI)
            if asyncio.iscoroutinefunction(self.scraper.get_meeting_details):
                return await self.scraper.get_meeting_details(meeting_id)
            else:
                return self.scraper.get_meeting_details(meeting_id)
        else:
            logger.error("Scraper does not support get_meeting_details")
            return None
    
    async def export_meetings_data(self, meetings: List[Dict], output_dir: str = 'data') -> None:
        """
        Export meeting data to files.
        
        Args:
            meetings: List of meeting metadata
            output_dir: Directory to save files
        """
        if hasattr(self.scraper, 'export_meetings_data'):
            # Handle async export_meetings_data (Crawl4AI)
            if asyncio.iscoroutinefunction(self.scraper.export_meetings_data):
                await self.scraper.export_meetings_data(meetings, output_dir)
            else:
                self.scraper.export_meetings_data(meetings, output_dir)
        else:
            logger.error("Scraper does not support export_meetings_data")
    
    async def close(self):
        """Close the scraper (needed for Selenium and Crawl4AI)."""
        if hasattr(self.scraper, 'close'):
            # Handle async close (Crawl4AI)
            if asyncio.iscoroutinefunction(self.scraper.close):
                await self.scraper.close()
            else:
                self.scraper.close()


async def main():
    """Main function demonstrating the unified scraper interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Unified Otter.ai scraper with multiple backends')
    parser.add_argument('--backend', choices=['selenium', 'firecrawl', 'crawl4ai', 'auto'], 
                        default='auto', help='Scraper backend to use')
    parser.add_argument('--browser', choices=['chrome', 'firefox', 'safari', 'chromium', 'webkit'], 
                        default='chrome', help='Browser for Selenium/Crawl4AI backend')
    parser.add_argument('--headless', action='store_true', 
                        help='Run browser in headless mode')
    parser.add_argument('--limit', type=int, default=5, 
                        help='Maximum number of meetings to extract')
    parser.add_argument('--output', default='data', 
                        help='Directory to save extracted data')
    parser.add_argument('--profile-dir', help='Chrome profile directory (Selenium only)')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    scraper = None
    try:
        # Create unified scraper
        scraper = UnifiedOtterScraper(
            backend=args.backend,
            browser=args.browser,
            headless=args.headless,
            profile_dir=args.profile_dir,
            browser_type=args.browser if args.backend == 'crawl4ai' else None
        )
        
        # Set up scraper (for Selenium)
        scraper.setup()
        
        # Authenticate
        if await scraper.authenticate():
            logger.info("Authentication successful")
        else:
            logger.warning("Authentication failed, but continuing...")
        
        # Get meetings
        meetings = await scraper.get_all_meetings(limit=args.limit)
        if meetings:
            logger.info(f"Found {len(meetings)} meetings")
            print(f"Meetings found: {len(meetings)}")
            for m in meetings:
                print(f"- {m['title']} | {m.get('date', 'No date')} | {m['url']}")
            
            # Export data
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
