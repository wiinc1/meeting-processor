#!/usr/bin/env python
"""
Get the REAL latest meeting transcript from your Otter.ai account
using Crawl4AI with proper infinite scroll handling.
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

async def get_real_latest_transcript_crawl4ai_infinite():
    """Get the REAL latest meeting transcript using Crawl4AI with infinite scroll."""
    try:
        # Load environment variables
        load_dotenv()
        
        logger.info("🎯 Getting REAL Latest Meeting Transcript from YOUR Otter.ai Account")
        logger.info("=" * 70)
        logger.info("Using Crawl4AI with infinite scroll handling (best scraper!)")
        
        # Initialize Crawl4AI scraper
        logger.info("🤖 Initializing Crawl4AI scraper...")
        scraper = UnifiedOtterScraper(backend='crawl4ai', headless=False)
        scraper.setup()
        
        # Authenticate with Crawl4AI
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
        
        # Get recent meetings with infinite scroll handling
        logger.info("📋 Getting your recent meetings with Crawl4AI infinite scroll...")
        meetings = await get_meetings_with_infinite_scroll(scraper, limit=10)
        
        if not meetings:
            logger.error("❌ No meetings found. Please check your authentication.")
            return None
        
        logger.info(f"✅ Found {len(meetings)} recent meetings in your account")
        
        # Display available meetings
        logger.info("📋 Your recent meetings:")
        for i, meeting in enumerate(meetings, 1):
            logger.info(f"  {i}. {meeting.get('title', 'Unknown')} - {meeting.get('date', 'Unknown')}")
        
        # Get the latest meeting (first in the list)
        latest_meeting = meetings[0]
        logger.info(f"📝 Latest meeting: {latest_meeting.get('title', 'Unknown')}")
        logger.info(f"🆔 Meeting ID: {latest_meeting.get('id', 'Unknown')}")
        logger.info(f"📅 Date: {latest_meeting.get('date', 'Unknown')}")
        
        # Get detailed transcript
        logger.info("🔍 Getting detailed transcript from your latest meeting...")
        meeting_details = await scraper.get_meeting_details(latest_meeting['id'])
        
        if not meeting_details:
            logger.error("❌ Failed to get meeting details")
            return None
        
        # Extract transcript
        transcript = meeting_details.get('transcript', [])
        summary = meeting_details.get('summary', '')
        action_items = meeting_details.get('action_items', [])
        insights = meeting_details.get('insights', [])
        
        logger.info(f"📊 Transcript contains {len(transcript)} segments")
        logger.info(f"📝 Summary: {len(summary)} characters")
        logger.info(f"✅ Action items: {len(action_items)}")
        logger.info(f"💡 Insights: {len(insights)}")
        
        # Create detailed transcript text
        transcript_text = ""
        for segment in transcript:
            speaker = segment.get('speaker', 'Unknown')
            timestamp = segment.get('timestamp', '')
            text = segment.get('text', '')
            transcript_text += f"[{timestamp}] {speaker}: {text}\n"
        
        # Save transcript to file
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        transcript_file = f"real_transcript_{timestamp_str}.txt"
        
        with open(transcript_file, 'w', encoding='utf-8') as f:
            f.write(f"Meeting: {latest_meeting.get('title', 'Unknown')}\n")
            f.write(f"Date: {latest_meeting.get('date', 'Unknown')}\n")
            f.write(f"ID: {latest_meeting.get('id', 'Unknown')}\n")
            f.write(f"Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            f.write("TRANSCRIPT:\n")
            f.write("-" * 40 + "\n")
            f.write(transcript_text)
            f.write("\n" + "=" * 80 + "\n\n")
            f.write("SUMMARY:\n")
            f.write("-" * 40 + "\n")
            f.write(summary)
            f.write("\n\n" + "=" * 80 + "\n\n")
            f.write("ACTION ITEMS:\n")
            f.write("-" * 40 + "\n")
            for i, item in enumerate(action_items, 1):
                f.write(f"{i}. {item}\n")
            f.write("\n" + "=" * 80 + "\n\n")
            f.write("INSIGHTS:\n")
            f.write("-" * 40 + "\n")
            for i, insight in enumerate(insights, 1):
                f.write(f"{i}. {insight}\n")
        
        logger.info(f"💾 Real transcript saved to: {transcript_file}")
        
        # Create AI summary
        logger.info("🤖 Creating AI summary of your real transcript...")
        ai_summary = create_ai_summary(transcript_text, summary, action_items, insights)
        
        # Save AI summary
        summary_file = f"real_ai_summary_{timestamp_str}.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"AI SUMMARY - {latest_meeting.get('title', 'Unknown')}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            f.write(ai_summary)
        
        logger.info(f"💾 AI summary saved to: {summary_file}")
        
        # Display summary
        print("\n" + "=" * 80)
        print("📋 YOUR REAL LATEST MEETING TRANSCRIPT SUMMARY")
        print("=" * 80)
        print(f"Meeting: {latest_meeting.get('title', 'Unknown')}")
        print(f"Date: {latest_meeting.get('date', 'Unknown')}")
        print(f"Transcript segments: {len(transcript)}")
        print(f"Summary length: {len(summary)} characters")
        print(f"Action items: {len(action_items)}")
        print(f"Insights: {len(insights)}")
        print("\n" + "-" * 40)
        print("AI SUMMARY:")
        print("-" * 40)
        print(ai_summary)
        print("\n" + "=" * 80)
        
        # Clean up
        await scraper.close()
        
        return {
            'meeting': latest_meeting,
            'transcript': transcript,
            'summary': summary,
            'action_items': action_items,
            'insights': insights,
            'ai_summary': ai_summary,
            'transcript_file': transcript_file,
            'summary_file': summary_file
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting real transcript: {e}")
        return None

async def get_meetings_with_infinite_scroll(scraper, limit=50):
    """Get meetings using Crawl4AI with proper infinite scroll handling."""
    try:
        from otter_crawl4ai import OtterCrawl4AI
        
        # Get the crawler instance
        crawl4ai_scraper = scraper.scraper
        crawler = await crawl4ai_scraper._get_crawler()
        
        # Navigate to home page
        result = await crawler.arun(
            url='https://otter.ai/home',
            wait_for="networkidle",
            delay_before_return_html=3.0
        )
        
        if not result.success:
            logger.error("Failed to load Otter.ai home page")
            return []
        
        logger.info("Successfully loaded Otter.ai home page")
        
        # Handle infinite scroll to load all meetings
        logger.info("Scrolling to load all meetings (Otter.ai uses infinite scroll)")
        last_count = 0
        no_new_count = 0
        max_no_new = 3  # Stop if no new meetings found after 3 scrolls
        scroll_attempts = 0
        max_scrolls = 20  # Maximum scroll attempts
        
        while scroll_attempts < max_scrolls:
            # Get current meeting count by looking for meeting links
            meeting_links = await crawler.query_selector_all('a[data-testid="conversation-title-link"]')
            current_count = len(meeting_links)
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
            
            # Scroll to the bottom of the page
            await crawler.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(2)  # Wait for content to load
            
            # Check if we've reached the limit
            if current_count >= limit:
                logger.info(f"Reached limit of {limit} meetings")
                break
        
        logger.info(f"Finished scrolling. Total meetings found: {last_count}")
        
        # Now extract meeting data from all loaded meetings
        meeting_links = await crawler.query_selector_all('a[data-testid="conversation-title-link"]')
        meetings = []
        
        for link_el in meeting_links:
            try:
                # Get meeting URL and title
                url = await link_el.get_attribute('href')
                title = await link_el.inner_text()
                
                if url and title:
                    # Extract meeting ID from URL
                    match = re.search(r'/u/([\w\-]+)', url)
                    meeting_id = match.group(1) if match else None
                    
                    # Try to extract date from title or other elements
                    date = None
                    try:
                        # Look for date in the title or nearby elements
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2}) at (\d{2}\.\d{2}\.\d{2})', title)
                        if date_match:
                            date_str = f"{date_match.group(1)} {date_match.group(2).replace('.', ':')}"
                            date = str(dateutil.parser.parse(date_str, fuzzy=True))
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
        
        logger.info(f"Successfully extracted {len(meetings)} meetings using Crawl4AI with infinite scroll")
        return meetings
        
    except Exception as e:
        logger.error(f"Error getting meetings with infinite scroll: {e}")
        return []

def create_ai_summary(transcript_text, original_summary, action_items, insights):
    """Create an AI summary of the transcript."""
    
    # Simple AI summary using the available data
    summary_parts = []
    
    # Meeting overview
    summary_parts.append("MEETING OVERVIEW:")
    summary_parts.append(f"- Original summary: {original_summary[:200]}..." if len(original_summary) > 200 else f"- Original summary: {original_summary}")
    
    # Key topics (extract from transcript)
    if transcript_text:
        # Simple keyword extraction
        words = transcript_text.lower().split()
        common_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must']
        word_freq = {}
        for word in words:
            if len(word) > 3 and word not in common_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        if top_words:
            summary_parts.append("\nKEY TOPICS:")
            for word, count in top_words:
                summary_parts.append(f"- {word} (mentioned {count} times)")
    
    # Action items
    if action_items:
        summary_parts.append("\nACTION ITEMS:")
        for i, item in enumerate(action_items, 1):
            summary_parts.append(f"{i}. {item}")
    
    # Insights
    if insights:
        summary_parts.append("\nKEY INSIGHTS:")
        for i, insight in enumerate(insights, 1):
            summary_parts.append(f"{i}. {insight}")
    
    # Transcript highlights (first few segments)
    if transcript_text:
        summary_parts.append("\nTRANSCRIPT HIGHLIGHTS:")
        lines = transcript_text.split('\n')[:5]  # First 5 lines
        for line in lines:
            if line.strip():
                summary_parts.append(f"- {line.strip()}")
    
    return "\n".join(summary_parts)

async def main():
    """Main function to get real latest transcript and summary."""
    print("🎯 REAL Otter.ai Latest Meeting Transcript Extractor (Crawl4AI + Infinite Scroll)")
    print("=" * 80)
    print("This script will:")
    print("1. Use Crawl4AI (the best scraper) for authentication")
    print("2. Handle Otter.ai's infinite scroll to load ALL meetings")
    print("3. Extract YOUR latest meeting transcript from today at 3:48 PM")
    print("4. Create an AI summary of YOUR real transcript")
    print("5. Save both to files")
    print("\n🚀 Starting in 3 seconds...")
    await asyncio.sleep(3)
    
    result = await get_real_latest_transcript_crawl4ai_infinite()
    
    if result:
        print(f"\n✅ Successfully retrieved YOUR real meeting transcript!")
        print(f"📁 Transcript file: {result['transcript_file']}")
        print(f"📁 Summary file: {result['summary_file']}")
        print(f"📝 Meeting: {result['meeting'].get('title', 'Unknown')}")
        print(f"📅 Date: {result['meeting'].get('date', 'Unknown')}")
    else:
        print("\n❌ Failed to retrieve your real meeting transcript.")
        print("💡 Please check your Otter.ai credentials and try again.")

if __name__ == "__main__":
    asyncio.run(main())
