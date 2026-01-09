#!/usr/bin/env python
"""
Test script for Firecrawl integration with Otter.ai scraping.
This script tests the Firecrawl scraper without requiring full authentication.
"""

import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_firecrawl_import():
    """Test if Firecrawl can be imported successfully."""
    try:
        from firecrawl import Firecrawl
        logger.info("✅ Firecrawl import successful")
        return True
    except ImportError as e:
        logger.error(f"❌ Firecrawl import failed: {e}")
        return False

def test_firecrawl_api_key():
    """Test if Firecrawl API key is configured."""
    load_dotenv()
    api_key = os.getenv('FIRECRAWL_API_KEY')
    
    if not api_key:
        logger.warning("⚠️ FIRECRAWL_API_KEY not found in environment")
        return False
    
    if api_key == 'your_firecrawl_api_key_here' or api_key == 'fc-your_api_key_here':
        logger.warning("⚠️ FIRECRAWL_API_KEY appears to be a placeholder")
        return False
    
    logger.info("✅ Firecrawl API key found")
    return True

def test_firecrawl_client():
    """Test if Firecrawl client can be initialized."""
    try:
        from firecrawl import Firecrawl
        load_dotenv()
        
        api_key = os.getenv('FIRECRAWL_API_KEY')
        if not api_key or api_key in ['your_firecrawl_api_key_here', 'fc-your_api_key_here']:
            logger.warning("⚠️ Skipping client test - no valid API key")
            return False
        
        app = Firecrawl(api_key=api_key)
        logger.info("✅ Firecrawl client initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Firecrawl client initialization failed: {e}")
        return False

def test_otter_firecrawl_import():
    """Test if our OtterFirecrawl class can be imported."""
    try:
        from otter_firecrawl import OtterFirecrawl
        logger.info("✅ OtterFirecrawl import successful")
        return True
    except ImportError as e:
        logger.error(f"❌ OtterFirecrawl import failed: {e}")
        return False

def test_scraper_factory_import():
    """Test if the scraper factory can be imported."""
    try:
        from otter_scraper_factory import UnifiedOtterScraper, OtterScraperFactory
        logger.info("✅ Scraper factory import successful")
        return True
    except ImportError as e:
        logger.error(f"❌ Scraper factory import failed: {e}")
        return False

def test_scraper_creation():
    """Test if scrapers can be created."""
    try:
        from otter_scraper_factory import OtterScraperFactory
        
        # Test auto-detection
        scraper = OtterScraperFactory.create_scraper(backend='auto')
        logger.info(f"✅ Auto-detected scraper: {type(scraper).__name__}")
        
        # Test Firecrawl creation (if API key available)
        if test_firecrawl_api_key():
            try:
                firecrawl_scraper = OtterScraperFactory.create_scraper(backend='firecrawl')
                logger.info("✅ Firecrawl scraper created successfully")
            except Exception as e:
                logger.warning(f"⚠️ Firecrawl scraper creation failed: {e}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Scraper creation failed: {e}")
        return False

def test_selenium_fallback():
    """Test if Selenium fallback works."""
    try:
        from otter_scraper_factory import OtterScraperFactory
        
        # Test Selenium creation
        selenium_scraper = OtterScraperFactory.create_scraper(backend='selenium')
        logger.info("✅ Selenium scraper created successfully")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Selenium scraper creation failed: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("🧪 Testing Firecrawl Integration")
    logger.info("=" * 50)
    
    tests = [
        ("Firecrawl Import", test_firecrawl_import),
        ("Firecrawl API Key", test_firecrawl_api_key),
        ("Firecrawl Client", test_firecrawl_client),
        ("OtterFirecrawl Import", test_otter_firecrawl_import),
        ("Scraper Factory Import", test_scraper_factory_import),
        ("Scraper Creation", test_scraper_creation),
        ("Selenium Fallback", test_selenium_fallback),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 Test Results Summary")
    logger.info("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} {test_name}")
    
    logger.info(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Firecrawl integration is ready.")
    elif passed >= total - 2:
        logger.info("⚠️ Most tests passed. Check warnings above.")
    else:
        logger.error("❌ Several tests failed. Check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
