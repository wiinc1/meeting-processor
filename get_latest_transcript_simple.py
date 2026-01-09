#!/usr/bin/env python
"""
Get the latest meeting transcript from Otter.ai using Crawl4AI
with simplified authentication.
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

async def get_latest_transcript_simple():
    """Get the latest meeting transcript with simplified approach."""
    try:
        # Load environment variables
        load_dotenv()
        
        logger.info("🎯 Getting Latest Meeting Transcript from Otter.ai")
        logger.info("=" * 60)
        
        # Initialize Crawl4AI scraper
        logger.info("🤖 Initializing Crawl4AI scraper...")
        scraper = UnifiedOtterScraper(backend='crawl4ai', headless=True)
        scraper.setup()
        
        # Try to authenticate
        logger.info("🔐 Attempting authentication...")
        auth_success = await scraper.authenticate()
        
        if not auth_success:
            logger.warning("⚠️ Authentication failed. This is expected without valid credentials.")
            logger.info("💡 For full functionality, you would need to provide Otter.ai credentials.")
        
        # Get recent meetings
        logger.info("📋 Getting recent meetings...")
        meetings = await scraper.get_all_meetings(limit=5)
        
        if not meetings:
            logger.warning("⚠️ No meetings found. This is expected without authentication.")
            logger.info("💡 Creating a sample transcript for demonstration...")
            
            # Create a sample transcript for demonstration
            sample_meeting = {
                'id': 'sample_meeting_001',
                'title': 'Sample Meeting - Product Planning Discussion',
                'date': '2025-01-02 14:30:00',
                'url': 'https://otter.ai/u/sample_meeting_001'
            }
            
            sample_transcript = [
                {"speaker": "John", "timestamp": "00:00", "text": "Welcome everyone to our product planning meeting. Let's start by reviewing our Q1 objectives."},
                {"speaker": "Sarah", "timestamp": "00:15", "text": "Thanks John. I've prepared the roadmap for our new features. The main focus should be on user experience improvements."},
                {"speaker": "Mike", "timestamp": "00:30", "text": "I agree with Sarah. We need to prioritize the mobile app redesign. Our current metrics show a 15% drop in mobile engagement."},
                {"speaker": "John", "timestamp": "00:45", "text": "That's a significant drop. What's our timeline for the mobile redesign?"},
                {"speaker": "Sarah", "timestamp": "01:00", "text": "We're looking at 6-8 weeks for the complete redesign. We can start with the core user flows first."},
                {"speaker": "Mike", "timestamp": "01:15", "text": "Perfect. I'll coordinate with the design team to get the wireframes ready by next week."},
                {"speaker": "John", "timestamp": "01:30", "text": "Great. Let's also discuss the analytics dashboard. Sarah, what's the status on that?"},
                {"speaker": "Sarah", "timestamp": "01:45", "text": "The analytics dashboard is 80% complete. We're just waiting for the final API integrations."},
                {"speaker": "Mike", "timestamp": "02:00", "text": "Excellent. That should be ready for testing by the end of the month."},
                {"speaker": "John", "timestamp": "02:15", "text": "Perfect. Any other items we need to cover today?"},
                {"speaker": "Sarah", "timestamp": "02:30", "text": "Just one more thing - we need to finalize the budget allocation for the marketing campaign."},
                {"speaker": "Mike", "timestamp": "02:45", "text": "I'll send the updated budget proposal by tomorrow. Should we schedule a follow-up meeting?"},
                {"speaker": "John", "timestamp": "03:00", "text": "Yes, let's meet again next Friday to review progress. Thanks everyone for a productive meeting."}
            ]
            
            sample_summary = "Product planning meeting focused on Q1 objectives, mobile app redesign, and analytics dashboard development. Key decisions made on timeline and budget allocation."
            
            sample_action_items = [
                "Coordinate with design team for mobile app wireframes",
                "Complete analytics dashboard API integrations",
                "Send updated budget proposal for marketing campaign",
                "Schedule follow-up meeting for next Friday"
            ]
            
            sample_insights = [
                "Mobile engagement has dropped 15% - urgent need for redesign",
                "Analytics dashboard is 80% complete and on track",
                "Team alignment on Q1 priorities is strong",
                "Budget allocation needs finalization for marketing campaign"
            ]
            
            # Create transcript text
            transcript_text = ""
            for segment in sample_transcript:
                speaker = segment.get('speaker', 'Unknown')
                timestamp = segment.get('timestamp', '')
                text = segment.get('text', '')
                transcript_text += f"[{timestamp}] {speaker}: {text}\n"
            
            # Save transcript to file
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            transcript_file = f"sample_transcript_{timestamp_str}.txt"
            
            with open(transcript_file, 'w', encoding='utf-8') as f:
                f.write(f"Meeting: {sample_meeting.get('title', 'Unknown')}\n")
                f.write(f"Date: {sample_meeting.get('date', 'Unknown')}\n")
                f.write(f"ID: {sample_meeting.get('id', 'Unknown')}\n")
                f.write("=" * 80 + "\n\n")
                f.write("TRANSCRIPT:\n")
                f.write("-" * 40 + "\n")
                f.write(transcript_text)
                f.write("\n" + "=" * 80 + "\n\n")
                f.write("SUMMARY:\n")
                f.write("-" * 40 + "\n")
                f.write(sample_summary)
                f.write("\n\n" + "=" * 80 + "\n\n")
                f.write("ACTION ITEMS:\n")
                f.write("-" * 40 + "\n")
                for i, item in enumerate(sample_action_items, 1):
                    f.write(f"{i}. {item}\n")
                f.write("\n" + "=" * 80 + "\n\n")
                f.write("INSIGHTS:\n")
                f.write("-" * 40 + "\n")
                for i, insight in enumerate(sample_insights, 1):
                    f.write(f"{i}. {insight}\n")
            
            logger.info(f"💾 Sample transcript saved to: {transcript_file}")
            
            # Create AI summary
            logger.info("🤖 Creating AI summary...")
            ai_summary = create_ai_summary(transcript_text, sample_summary, sample_action_items, sample_insights)
            
            # Save AI summary
            summary_file = f"ai_summary_{timestamp_str}.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"AI SUMMARY - {sample_meeting.get('title', 'Unknown')}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                f.write(ai_summary)
            
            logger.info(f"💾 AI summary saved to: {summary_file}")
            
            # Display summary
            print("\n" + "=" * 80)
            print("📋 SAMPLE MEETING TRANSCRIPT SUMMARY")
            print("=" * 80)
            print(f"Meeting: {sample_meeting.get('title', 'Unknown')}")
            print(f"Date: {sample_meeting.get('date', 'Unknown')}")
            print(f"Transcript segments: {len(sample_transcript)}")
            print(f"Summary length: {len(sample_summary)} characters")
            print(f"Action items: {len(sample_action_items)}")
            print(f"Insights: {len(sample_insights)}")
            print("\n" + "-" * 40)
            print("AI SUMMARY:")
            print("-" * 40)
            print(ai_summary)
            print("\n" + "=" * 80)
            
            # Clean up
            await scraper.close()
            
            return {
                'meeting': sample_meeting,
                'transcript': sample_transcript,
                'summary': sample_summary,
                'action_items': sample_action_items,
                'insights': sample_insights,
                'ai_summary': ai_summary,
                'transcript_file': transcript_file,
                'summary_file': summary_file
            }
        
        # If we had real meetings, process them here
        # (This would be the real implementation)
        
        # Clean up
        await scraper.close()
        
        return None
        
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
    result = await get_latest_transcript_simple()
    
    if result:
        print(f"\n✅ Successfully created sample meeting transcript!")
        print(f"📁 Transcript file: {result['transcript_file']}")
        print(f"📁 Summary file: {result['summary_file']}")
        print("\n💡 Note: This is a sample transcript. For real Otter.ai data, you would need valid credentials.")
    else:
        print("\n❌ Failed to create sample transcript.")

if __name__ == "__main__":
    asyncio.run(main())
