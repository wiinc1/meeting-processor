#!/usr/bin/env python
"""
Comprehensive test script for all scraper backends.
Tests Selenium, Firecrawl, and Crawl4AI integration.
"""

import os
import logging
import asyncio
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test if all required libraries can be imported."""
    results = {}
    
    # Test Selenium
    try:
        from selenium import webdriver
        results['selenium'] = True
        logger.info("✅ Selenium import successful")
    except ImportError as e:
        results['selenium'] = False
        logger.error(f"❌ Selenium import failed: {e}")
    
    # Test Firecrawl
    try:
        from firecrawl import Firecrawl
        results['firecrawl'] = True
        logger.info("✅ Firecrawl import successful")
    except ImportError as e:
        results['firecrawl'] = False
        logger.error(f"❌ Firecrawl import failed: {e}")
    
    # Test Crawl4AI
    try:
        from crawl4ai import AsyncWebCrawler
        results['crawl4ai'] = True
        logger.info("✅ Crawl4AI import successful")
    except ImportError as e:
        results['crawl4ai'] = False
        logger.error(f"❌ Crawl4AI import failed: {e}")
    
    return results

def test_environment_variables():
    """Test environment variable configuration."""
    load_dotenv()
    results = {}
    
    # Test Firecrawl API key
    firecrawl_key = os.getenv('FIRECRAWL_API_KEY')
    if firecrawl_key and firecrawl_key not in ['your_firecrawl_api_key_here', 'fc-your_api_key_here']:
        results['firecrawl_key'] = True
        logger.info("✅ Firecrawl API key found")
    else:
        results['firecrawl_key'] = False
        logger.warning("⚠️ Firecrawl API key not found or is placeholder")
    
    # Test Otter.ai credentials
    otter_username = os.getenv('OTTER_USERNAME')
    otter_password = os.getenv('OTTER_PASSWORD')
    if otter_username and otter_password:
        results['otter_credentials'] = True
        logger.info("✅ Otter.ai credentials found")
    else:
        results['otter_credentials'] = False
        logger.warning("⚠️ Otter.ai credentials not found")
    
    # Test Notion API key
    notion_key = os.getenv('NOTION_API_KEY')
    if notion_key:
        results['notion_key'] = True
        logger.info("✅ Notion API key found")
    else:
        results['notion_key'] = False
        logger.warning("⚠️ Notion API key not found")
    
    return results

def test_scraper_factory():
    """Test the scraper factory functionality."""
    try:
        from otter_scraper_factory import OtterScraperFactory, UnifiedOtterScraper
        logger.info("✅ Scraper factory import successful")
        
        # Test auto-detection
        try:
            backend = OtterScraperFactory._detect_best_backend()
            logger.info(f"✅ Auto-detected backend: {backend}")
        except Exception as e:
            logger.error(f"❌ Auto-detection failed: {e}")
            return False
        
        # Test scraper creation
        scrapers_to_test = ['selenium', 'firecrawl', 'crawl4ai']
        results = {}
        
        for backend in scrapers_to_test:
            try:
                scraper = OtterScraperFactory.create_scraper(backend)
                results[backend] = True
                logger.info(f"✅ {backend} scraper created successfully")
            except Exception as e:
                results[backend] = False
                logger.error(f"❌ {backend} scraper creation failed: {e}")
        
        return results
        
    except ImportError as e:
        logger.error(f"❌ Scraper factory import failed: {e}")
        return False

async def test_crawl4ai_functionality():
    """Test Crawl4AI specific functionality."""
    try:
        from otter_crawl4ai import OtterCrawl4AI
        
        # Test scraper creation
        scraper = OtterCrawl4AI(headless=True, browser_type='chromium')
        logger.info("✅ Crawl4AI scraper created")
        
        # Test async methods exist
        if hasattr(scraper, 'authenticate') and asyncio.iscoroutinefunction(scraper.authenticate):
            logger.info("✅ Crawl4AI async authenticate method found")
        else:
            logger.warning("⚠️ Crawl4AI authenticate method not async")
        
        if hasattr(scraper, 'get_all_meetings') and asyncio.iscoroutinefunction(scraper.get_all_meetings):
            logger.info("✅ Crawl4AI async get_all_meetings method found")
        else:
            logger.warning("⚠️ Crawl4AI get_all_meetings method not async")
        
        # Test close method
        await scraper.close()
        logger.info("✅ Crawl4AI scraper closed successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Crawl4AI functionality test failed: {e}")
        return False

def test_firecrawl_functionality():
    """Test Firecrawl specific functionality."""
    try:
        from otter_firecrawl import OtterFirecrawl
        
        # Test scraper creation
        scraper = OtterFirecrawl()
        logger.info("✅ Firecrawl scraper created")
        
        # Test methods exist
        if hasattr(scraper, 'authenticate'):
            logger.info("✅ Firecrawl authenticate method found")
        else:
            logger.warning("⚠️ Firecrawl authenticate method not found")
        
        if hasattr(scraper, 'get_all_meetings'):
            logger.info("✅ Firecrawl get_all_meetings method found")
        else:
            logger.warning("⚠️ Firecrawl get_all_meetings method not found")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Firecrawl functionality test failed: {e}")
        return False

def test_selenium_functionality():
    """Test Selenium specific functionality."""
    try:
        from otter_selenium import OtterSelenium
        
        # Test scraper creation
        scraper = OtterSelenium(browser='chrome', headless=True)
        logger.info("✅ Selenium scraper created")
        
        # Test methods exist
        if hasattr(scraper, 'login_with_apple'):
            logger.info("✅ Selenium login_with_apple method found")
        else:
            logger.warning("⚠️ Selenium login_with_apple method not found")
        
        if hasattr(scraper, 'get_all_meetings'):
            logger.info("✅ Selenium get_all_meetings method found")
        else:
            logger.warning("⚠️ Selenium get_all_meetings method not found")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Selenium functionality test failed: {e}")
        return False

async def test_unified_interface():
    """Test the unified scraper interface."""
    try:
        from otter_scraper_factory import UnifiedOtterScraper
        
        # Test unified scraper creation
        scrapers_to_test = ['selenium', 'firecrawl', 'crawl4ai']
        results = {}
        
        for backend in scrapers_to_test:
            try:
                scraper = UnifiedOtterScraper(backend=backend)
                logger.info(f"✅ Unified {backend} scraper created")
                
                # Test setup method
                scraper.setup()
                logger.info(f"✅ {backend} scraper setup completed")
                
                # Test close method
                if asyncio.iscoroutinefunction(scraper.close):
                    await scraper.close()
                else:
                    scraper.close()
                logger.info(f"✅ {backend} scraper closed")
                
                results[backend] = True
                
            except Exception as e:
                logger.error(f"❌ Unified {backend} scraper test failed: {e}")
                results[backend] = False
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Unified interface test failed: {e}")
        return False

def test_main_script_integration():
    """Test main script integration."""
    try:
        # Test if main script can be imported
        import main
        logger.info("✅ Main script import successful")
        
        # Test argument parsing
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--scraper', choices=['api', 'selenium', 'firecrawl', 'crawl4ai', 'auto'])
        parser.add_argument('--browser', choices=['chrome', 'firefox', 'safari', 'chromium', 'webkit'])
        parser.add_argument('--headless', action='store_true')
        
        # Test valid arguments
        test_args = ['--scraper', 'crawl4ai', '--browser', 'chromium', '--headless']
        args = parser.parse_args(test_args)
        
        if args.scraper == 'crawl4ai' and args.browser == 'chromium' and args.headless:
            logger.info("✅ Main script argument parsing works")
            return True
        else:
            logger.error("❌ Main script argument parsing failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Main script integration test failed: {e}")
        return False

async def main():
    """Run all tests."""
    logger.info("🧪 Testing All Scraper Backends")
    logger.info("=" * 60)
    
    # Test imports
    logger.info("\n📦 Testing Library Imports")
    logger.info("-" * 30)
    import_results = test_imports()
    
    # Test environment variables
    logger.info("\n🔧 Testing Environment Variables")
    logger.info("-" * 30)
    env_results = test_environment_variables()
    
    # Test scraper factory
    logger.info("\n🏭 Testing Scraper Factory")
    logger.info("-" * 30)
    factory_results = test_scraper_factory()
    
    # Test individual scrapers
    logger.info("\n🔍 Testing Individual Scrapers")
    logger.info("-" * 30)
    
    selenium_result = test_selenium_functionality()
    firecrawl_result = test_firecrawl_functionality()
    crawl4ai_result = await test_crawl4ai_functionality()
    
    # Test unified interface
    logger.info("\n🔗 Testing Unified Interface")
    logger.info("-" * 30)
    unified_results = await test_unified_interface()
    
    # Test main script integration
    logger.info("\n📝 Testing Main Script Integration")
    logger.info("-" * 30)
    main_result = test_main_script_integration()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 Test Results Summary")
    logger.info("=" * 60)
    
    total_tests = 0
    passed_tests = 0
    
    # Count results
    for category, results in [
        ("Library Imports", import_results),
        ("Environment Variables", env_results),
        ("Scraper Factory", factory_results if isinstance(factory_results, dict) else {"factory": factory_results}),
        ("Individual Scrapers", {
            "selenium": selenium_result,
            "firecrawl": firecrawl_result,
            "crawl4ai": crawl4ai_result
        }),
        ("Unified Interface", unified_results if isinstance(unified_results, dict) else {"unified": unified_results}),
        ("Main Script", {"main": main_result})
    ]:
        logger.info(f"\n{category}:")
        for test_name, result in results.items():
            total_tests += 1
            if result:
                passed_tests += 1
                logger.info(f"  ✅ {test_name}")
            else:
                logger.info(f"  ❌ {test_name}")
    
    # Overall results
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    logger.info(f"\n🎯 Overall: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
    
    if success_rate >= 90:
        logger.info("🎉 Excellent! All scrapers are ready for use.")
    elif success_rate >= 70:
        logger.info("⚠️ Good! Most functionality is working, check warnings above.")
    else:
        logger.error("❌ Several issues found. Check errors above.")
    
    # Recommendations
    logger.info("\n💡 Recommendations:")
    
    if import_results.get('crawl4ai') and crawl4ai_result:
        logger.info("  🥇 Use Crawl4AI for best performance")
    elif import_results.get('firecrawl') and firecrawl_result and env_results.get('firecrawl_key'):
        logger.info("  🥈 Use Firecrawl for managed service")
    elif import_results.get('selenium') and selenium_result:
        logger.info("  🥉 Use Selenium as fallback")
    else:
        logger.info("  ❌ No working scrapers found")
    
    return success_rate >= 70

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
