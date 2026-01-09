#!/usr/bin/env python
import os
import webbrowser
import json
import time
from datetime import datetime, timedelta
import argparse
from dotenv import load_dotenv
from db_manager import ProcessedMeetingsDB

def main():
    """Simple script to help with manual Otter.ai data extraction with tracking of processed meetings"""
    parser = argparse.ArgumentParser(description='Manual Otter.ai login and data extraction helper')
    parser.add_argument('--output', default='data',
                      help='Directory to save the extracted data')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    
    # Initialize database to track processed meetings
    db_path = os.path.join(args.output, 'processed_meetings.db')
    db = ProcessedMeetingsDB(db_path)
    
    # Get total counts to show progress
    counts = db.get_total_counts()
    print(f"\nYou've processed {counts['total_meetings']} meetings and created {counts['total_actions']} tasks so far.")
    
    # Open Otter.ai login page
    print("\n=== Otter.ai to Notion Manual Authentication ===\n")
    print("1. Opening the Otter.ai login page in your default browser")
    print("2. Please click on 'Continue with Apple'")
    print("3. Complete the Apple authentication")
    
    # Open the login page
    webbrowser.open('https://otter.ai/signin')
    
    # Wait for the user to authenticate
    input("\nPress Enter after you've logged in to Otter.ai with your Apple ID...")
    
    # Guide the user to get meeting data
    print("\n=== Getting Meeting Data ===\n")
    print("Now you'll need to manually extract data from your meetings:")
    print("1. Navigate to 'https://otter.ai/home' to see your recent meetings")
    print("2. Start with your MOST RECENT meeting that hasn't been processed yet")
    webbrowser.open('https://otter.ai/home')
    
    input("\nPress Enter when you can see your meetings list...")
    
    # Prepare to start a sync session
    sync_id = db.start_sync_session()
    
    # Track statistics for this session
    meetings_processed = 0
    actions_created = 0
    errors_encountered = 0
    
    # Ask the user for meeting details
    meetings = []
    while True:
        print("\n=== Extracting Meeting Information ===")
        print("Please focus on your most recent unprocessed meeting.")
        
        meeting = {}
        meeting['url'] = input("Enter meeting URL (e.g., https://otter.ai/u/abc123) or leave empty to stop: ")
        if not meeting['url']:
            break
            
        meeting['id'] = meeting['url'].split('/')[-1]
        
        # Check if this meeting has already been processed
        if db.is_processed(meeting['id']):
            print(f"\nThis meeting has already been processed. Please select a different meeting.")
            continue
        
        meeting['title'] = input("Enter meeting title: ")
        meeting['date'] = input("Enter meeting date (YYYY-MM-DD): ")
        
        # Open the meeting page
        print(f"\nOpening meeting page: {meeting['url']}")
        webbrowser.open(meeting['url'])
        
        input("\nPress Enter after the meeting page has loaded...")
        
        # Guide the user to copy the transcript
        print("\n=== Extracting Transcript ===")
        print("1. Select all text in the transcript area (Ctrl/Cmd+A)")
        print("2. Copy it to clipboard (Ctrl/Cmd+C)")
        
        input("Press Enter after you've copied the transcript...")
        
        # Create directory for meeting data
        meeting_dir = os.path.join(args.output, meeting['id'])
        os.makedirs(meeting_dir, exist_ok=True)
        
        # Ask the user to save the transcript
        transcript_file = os.path.join(meeting_dir, 'transcript.txt')
        print(f"\nPlease paste the transcript into a text editor and save as: {transcript_file}")
        input("Press Enter after you've saved the transcript...")
        
        # Guide the user to check for summary
        print("\n=== Extracting Summary ===")
        print("1. Click on the 'Summary' tab (if available)")
        print("2. Copy the summary text")
        
        input("Press Enter after you've copied the summary (or if no summary is available)...")
        
        # Ask the user to save the summary
        summary_file = os.path.join(meeting_dir, 'summary.txt')
        print(f"\nIf summary is available, please paste it into a text editor and save as: {summary_file}")
        input("Press Enter after you've saved the summary (or if no summary is available)...")
        
        # Guide the user to check for action items
        print("\n=== Extracting Action Items ===")
        print("1. Click on the 'AI Highlights' or 'Action Items' tab (if available)")
        print("2. For each action item, note down:")
        print("   - The text of the action item")
        print("   - The person assigned (if any)")
        
        input("Press Enter after you've noted down action items (or if none are available)...")
        
        # Ask for action items
        action_items = []
        while True:
            action_text = input("\nEnter action item text (or leave empty to stop): ")
            if not action_text:
                break
                
            # Get owner but ensure Brian is assigned in the system
            original_owner = input("Enter person originally assigned (if known): ") or ""
            
            # Add original owner to text if provided
            if original_owner and original_owner.lower() != "brian":
                description = f"Originally assigned to: {original_owner}"
            else:
                description = ""
                
            action_items.append({
                'text': action_text,
                'owner': "Brian",  # Always assign to Brian as required
                'description': description,
                'due_date': (datetime.now() + timedelta(days=7)).isoformat()
            })
        
        # Save action items
        if action_items:
            action_items_file = os.path.join(meeting_dir, 'action_items.json')
            with open(action_items_file, 'w') as f:
                json.dump(action_items, f, indent=2)
            actions_created += len(action_items)
                
        # Add action items to meeting
        meeting['action_items'] = action_items
        
        # Add meeting to list
        meetings.append(meeting)
        
        # Mark meeting as processed in the database
        db.mark_processed(
            meeting_id=meeting['id'],
            meeting_title=meeting['title'],
            meeting_date=meeting['date'],
            action_count=len(action_items)
        )
        
        meetings_processed += 1
        print(f"\nSuccessfully extracted data for meeting: {meeting['title']}")
        print(f"This meeting has been marked as processed in the database.")
    
    # End the sync session
    if sync_id:
        db.end_sync_session(sync_id, meetings_processed, actions_created, errors_encountered)
    
    # Save all meetings data for this session
    if meetings:
        meetings_file = os.path.join(args.output, 'recent_meetings.json')
        with open(meetings_file, 'w') as f:
            json.dump(meetings, f, indent=2, default=str)
        
        print(f"\nSaved meeting data to: {meetings_file}")
        
        # Update total counts
        counts = db.get_total_counts()
        print(f"\nYou've now processed a total of {counts['total_meetings']} meetings and created {counts['total_actions']} tasks.")
        
        # Provide next steps
        print("\n=== Next Steps ===")
        print("To import this data into Notion:")
        print("1. Run the following command:")
        print("   python otter_to_notion_import.py --data-dir", args.output)
    else:
        print("\nNo new meetings were extracted. All meetings may already be processed.")

if __name__ == "__main__":
    main() 