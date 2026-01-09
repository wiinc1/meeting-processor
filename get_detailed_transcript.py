#!/usr/bin/env python
"""
Get the DETAILED transcript from your Otter.ai meeting
with improved transcript extraction.
"""

import os
import asyncio
import logging
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from otter_scraper_factory import UnifiedOtterScraper
import dateutil.parser

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def get_detailed_transcript():
    """Get the detailed transcript with improved extraction."""
    try:
        # Load environment variables
        load_dotenv()
        
        logger.info("🎯 Getting DETAILED Transcript from Your Otter.ai Meeting")
        logger.info("=" * 70)
        
        # Initialize Selenium scraper
        logger.info("🤖 Initializing Selenium scraper...")
        scraper = UnifiedOtterScraper(backend='selenium', headless=False)
        scraper.setup()
        
        # Authenticate with Selenium
        logger.info("🔐 A browser window will open for you to log in to Otter.ai")
        logger.info("💡 Please complete the authentication process in the browser")
        logger.info("⏳ The script will wait for you to complete authentication...")
        
        # Wait a moment for user to see the message
        await asyncio.sleep(2)
        
        auth_success = await scraper.authenticate()
        
        if not auth_success:
            logger.warning("⚠️ Authentication may have failed. Please try again.")
            return None
        
        logger.info("✅ Authentication successful!")
        
        # Navigate directly to the specific meeting
        meeting_id = "u8vlsJ4NOUqE0lfvYD1huK6ZZ88"  # Your meeting ID
        meeting_url = f"https://otter.ai/u/{meeting_id}"
        
        logger.info(f"🔍 Navigating directly to your meeting: {meeting_url}")
        
        # Use the scraper's driver directly for more control
        scraper.scraper.driver.get(meeting_url)
        
        # Wait for page to load
        import time
        time.sleep(5)
        
        logger.info("📋 Looking for transcript elements...")
        
        # Try multiple approaches to find transcript
        transcript_data = []
        
        # Method 1: Look for transcript container
        try:
            transcript_container = scraper.scraper.driver.find_element("css selector", "[data-testid='conversation-transcript-container']")
            logger.info("✅ Found transcript container")
            
            # Look for transcript snippets
            snippets = transcript_container.find_elements("css selector", ".conversation-transcript-snippet-container")
            logger.info(f"Found {len(snippets)} transcript snippets")
            
            for snippet in snippets:
                try:
                    # Extract speaker
                    speaker_el = snippet.find_element("css selector", ".transcript-snippet__content__head__speaker-name")
                    speaker = speaker_el.text.strip()
                except:
                    speaker = "Unknown"
                
                try:
                    # Extract timestamp
                    timestamp_el = snippet.find_element("css selector", ".transcript-snippet__content__head__timestamp-meta")
                    timestamp = timestamp_el.text.strip()
                except:
                    timestamp = ""
                
                try:
                    # Extract text
                    text_el = snippet.find_element("css selector", ".transcript-snippet__content__body")
                    text = text_el.text.strip()
                except:
                    text = snippet.text.strip()
                
                if text:
                    transcript_data.append({
                        "speaker": speaker,
                        "timestamp": timestamp,
                        "text": text
                    })
            
            logger.info(f"✅ Extracted {len(transcript_data)} transcript segments")
            
        except Exception as e:
            logger.warning(f"Method 1 failed: {e}")
            
            # Method 2: Look for any transcript-related elements
            try:
                # Try different selectors
                selectors = [
                    ".transcript-snippet",
                    ".conversation-transcript-snippet",
                    "[class*='transcript']",
                    "[class*='snippet']"
                ]
                
                for selector in selectors:
                    try:
                        elements = scraper.scraper.driver.find_elements("css selector", selector)
                        if elements:
                            logger.info(f"Found {len(elements)} elements with selector: {selector}")
                            
                            for element in elements:
                                try:
                                    text = element.text.strip()
                                    if text and len(text) > 10:  # Filter out short/empty text
                                        transcript_data.append({
                                            "speaker": "Unknown",
                                            "timestamp": "",
                                            "text": text
                                        })
                                except:
                                    continue
                            break
                    except:
                        continue
                        
            except Exception as e2:
                logger.warning(f"Method 2 failed: {e2}")
        
        # If we still don't have transcript data, try to get the page source and extract manually
        if not transcript_data:
            logger.info("🔍 Trying to extract from page source...")
            page_source = scraper.scraper.driver.page_source
            
            # Look for transcript patterns in the HTML
            import re
            transcript_patterns = [
                r'<div[^>]*class="[^"]*transcript[^"]*"[^>]*>(.*?)</div>',
                r'<span[^>]*class="[^"]*transcript[^"]*"[^>]*>(.*?)</span>',
                r'<p[^>]*class="[^"]*transcript[^"]*"[^>]*>(.*?)</p>'
            ]
            
            for pattern in transcript_patterns:
                matches = re.findall(pattern, page_source, re.DOTALL | re.IGNORECASE)
                if matches:
                    logger.info(f"Found {len(matches)} matches with pattern")
                    for match in matches:
                        # Clean up HTML tags
                        clean_text = re.sub(r'<[^>]+>', '', match).strip()
                        if clean_text and len(clean_text) > 10:
                            transcript_data.append({
                                "speaker": "Unknown",
                                "timestamp": "",
                                "text": clean_text
                            })
        
        # Create detailed transcript text
        transcript_text = ""
        for segment in transcript_data:
            speaker = segment.get('speaker', 'Unknown')
            timestamp = segment.get('timestamp', '')
            text = segment.get('text', '')
            transcript_text += f"[{timestamp}] {speaker}: {text}\n"
        
        # Save transcript to file
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        transcript_file = f"detailed_transcript_{timestamp_str}.txt"
        
        with open(transcript_file, 'w', encoding='utf-8') as f:
            f.write(f"Meeting: Mohawk - Questionnaire Review - Prechecker installed 2025-10-02 at 14.30.08\n")
            f.write(f"Date: 2025-10-02\n")
            f.write(f"ID: {meeting_id}\n")
            f.write(f"Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            f.write("DETAILED TRANSCRIPT:\n")
            f.write("-" * 40 + "\n")
            f.write(transcript_text)
        
        logger.info(f"💾 Detailed transcript saved to: {transcript_file}")
        
        # Display results
        print("\n" + "=" * 80)
        print("📋 DETAILED TRANSCRIPT EXTRACTION RESULTS")
        print("=" * 80)
        print(f"Transcript segments found: {len(transcript_data)}")
        print(f"Total characters: {len(transcript_text)}")
        print(f"File saved: {transcript_file}")
        
        if transcript_data:
            print("\nFirst few segments:")
            for i, segment in enumerate(transcript_data[:3]):
                print(f"{i+1}. [{segment.get('timestamp', '')}] {segment.get('speaker', 'Unknown')}: {segment.get('text', '')[:100]}...")
        else:
            print("\n⚠️ No transcript segments found. The page structure may have changed.")
        
        print("\n" + "=" * 80)
        
        # Clean up
        await scraper.close()
        
        return {
            'transcript_data': transcript_data,
            'transcript_text': transcript_text,
            'transcript_file': transcript_file
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting detailed transcript: {e}")
        return None

async def main():
    """Main function to get detailed transcript."""
    print("🎯 DETAILED Otter.ai Transcript Extractor")
    print("=" * 60)
    print("This script will:")
    print("1. Navigate directly to your meeting page")
    print("2. Try multiple methods to extract the detailed transcript")
    print("3. Save the complete transcript with speaker names and timestamps")
    print("\n🚀 Starting in 3 seconds...")
    await asyncio.sleep(3)
    
    result = await get_detailed_transcript()
    
    if result and result['transcript_data']:
        print(f"\n✅ Successfully extracted detailed transcript!")
        print(f"📁 Transcript file: {result['transcript_file']}")
        print(f"📊 Segments found: {len(result['transcript_data'])}")
    else:
        print("\n❌ Failed to extract detailed transcript.")
        print("💡 The page structure may have changed or transcript may not be available.")

if __name__ == "__main__":
    asyncio.run(main())
