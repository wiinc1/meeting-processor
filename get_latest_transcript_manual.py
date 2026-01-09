#!/usr/bin/env python
"""
Get the latest meeting transcript from Otter.ai using Crawl4AI
with manual authentication support.
"""

import os
import asyncio
import logging
import json
from datetime import datetime
from dotenv import load_dotenv
from otter_scraper_factory import UnifiedOtterScraper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def get_latest_transcript_manual():
    """Get the latest meeting transcript with manual authentication."""
    try:
        # Load environment variables
        load_dotenv()
        
        logger.info("🎯 Getting Latest Meeting Transcript from Otter.ai")
        logger.info("=" * 60)
        
        # Initialize Crawl4AI scraper in non-headless mode for manual auth
        logger.info("🤖 Initializing Crawl4AI scraper (non-headless for manual auth)...")
        scraper = UnifiedOtterScraper(backend='crawl4ai', headless=False)
        scraper.setup()
        
        # Authenticate manually
        logger.info("🔐 Please complete authentication manually in the browser window...")
        logger.info("💡 The browser will open - please log in to Otter.ai")
        logger.info("⏳ Waiting for you to complete authentication...")
        
        auth_success = await scraper.authenticate()
        
        if not auth_success:
            logger.warning("⚠️ Authentication may have failed. Continuing anyway...")
        
        # Get recent meetings
        logger.info("📋 Getting recent meetings...")
        meetings = await scraper.get_all_meetings(limit=5)
        
        if not meetings:
            logger.error("❌ No meetings found. Please check your authentication.")
            return None
        
        logger.info(f"✅ Found {len(meetings)} recent meetings")
        
        # Get the latest meeting
        latest_meeting = meetings[0]
        logger.info(f"📝 Latest meeting: {latest_meeting.get('title', 'Unknown')}")
        logger.info(f"🆔 Meeting ID: {latest_meeting.get('id', 'Unknown')}")
        logger.info(f"📅 Date: {latest_meeting.get('date', 'Unknown')}")
        
        # Get detailed transcript
        logger.info("🔍 Getting detailed transcript...")
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
        transcript_file = f"latest_transcript_{timestamp_str}.txt"
        
        with open(transcript_file, 'w', encoding='utf-8') as f:
            f.write(f"Meeting: {latest_meeting.get('title', 'Unknown')}\n")
            f.write(f"Date: {latest_meeting.get('date', 'Unknown')}\n")
            f.write(f"ID: {latest_meeting.get('id', 'Unknown')}\n")
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
        
        logger.info(f"💾 Transcript saved to: {transcript_file}")
        
        # Create AI summary
        logger.info("🤖 Creating AI summary...")
        ai_summary = create_ai_summary(transcript_text, summary, action_items, insights)
        
        # Save AI summary
        summary_file = f"ai_summary_{timestamp_str}.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"AI SUMMARY - {latest_meeting.get('title', 'Unknown')}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            f.write(ai_summary)
        
        logger.info(f"💾 AI summary saved to: {summary_file}")
        
        # Display summary
        print("\n" + "=" * 80)
        print("📋 LATEST MEETING TRANSCRIPT SUMMARY")
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
        logger.error(f"❌ Error getting latest transcript: {e}")
        return None

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
    """Main function to get latest transcript and summary."""
    print("🎯 Otter.ai Latest Meeting Transcript Extractor")
    print("=" * 60)
    print("This script will:")
    print("1. Open a browser window for you to log in to Otter.ai")
    print("2. Extract your latest meeting transcript")
    print("3. Create an AI summary of the transcript")
    print("4. Save both to files")
    print("\nPress Enter to continue...")
    input()
    
    result = await get_latest_transcript_manual()
    
    if result:
        print(f"\n✅ Successfully retrieved latest meeting transcript!")
        print(f"📁 Transcript file: {result['transcript_file']}")
        print(f"📁 Summary file: {result['summary_file']}")
    else:
        print("\n❌ Failed to retrieve latest meeting transcript.")
        print("💡 Please check your Otter.ai credentials and try again.")

if __name__ == "__main__":
    asyncio.run(main())
