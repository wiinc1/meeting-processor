#!/usr/bin/env python
import os
import logging
import yaml
import json
from datetime import datetime, timedelta
import argparse
from dotenv import load_dotenv
from notion_api import NotionAPI
from db_manager import ProcessedMeetingsDB
from dateutil import parser
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from config.yaml."""
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Validate required configuration settings
        required_keys = ['notion_activities_db', 'notion_tasks_db', 'max_meetings']
        missing_keys = [key for key in required_keys if key not in config]
        
        if missing_keys:
            logging.error(f"Missing required configuration keys: {', '.join(missing_keys)}")
            return None
            
        return config
    except FileNotFoundError:
        logging.error("Configuration file 'config.yaml' not found")
        return None
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        return None

def load_meetings(data_dir):
    """Load meetings data from the specified directory."""
    # Try loading from recent_meetings.json first, then fall back to meetings.json
    meetings_file = os.path.join(data_dir, 'recent_meetings.json')
    if not os.path.exists(meetings_file):
        meetings_file = os.path.join(data_dir, 'meetings.json')
    
    if not os.path.exists(meetings_file):
        logger.error(f"Meetings file not found: either recent_meetings.json or meetings.json")
        return []
    
    try:
        with open(meetings_file, 'r') as f:
            meetings = json.load(f)
        
        # Sort meetings by date, newest first, to ensure we process most recent first
        if meetings and 'date' in meetings[0]:
            meetings.sort(key=lambda m: m.get('date', ''), reverse=True)
        
        logger.info(f"Loaded {len(meetings)} meetings from {meetings_file}")
        return meetings
    except Exception as e:
        logger.error(f"Error loading meetings data: {e}")
        return []

def load_meeting_details(data_dir, meeting_id):
    """Load meeting details from the specified directory."""
    meeting_dir = os.path.join(data_dir, meeting_id)
    
    if not os.path.exists(meeting_dir):
        logger.error(f"Meeting directory not found: {meeting_dir}")
        return {}
    
    details = {
        'meeting_id': meeting_id,
        'transcript': '',
        'summary': '',
        'action_items': []
    }
    
    # Load transcript
    transcript_file = os.path.join(meeting_dir, 'transcript.txt')
    if os.path.exists(transcript_file):
        try:
            with open(transcript_file, 'r') as f:
                details['transcript'] = f.read()
            logger.info(f"Loaded transcript: {len(details['transcript'])} characters")
        except Exception as e:
            logger.error(f"Error loading transcript: {e}")
    
    # Load summary
    summary_file = os.path.join(meeting_dir, 'summary.txt')
    if os.path.exists(summary_file):
        try:
            with open(summary_file, 'r') as f:
                details['summary'] = f.read()
            logger.info(f"Loaded summary: {len(details['summary'])} characters")
        except Exception as e:
            logger.error(f"Error loading summary: {e}")
    
    # Load action items
    action_items_file = os.path.join(meeting_dir, 'action_items.json')
    if os.path.exists(action_items_file):
        try:
            with open(action_items_file, 'r') as f:
                details['action_items'] = json.load(f)
            logger.info(f"Loaded {len(details['action_items'])} action items")
        except Exception as e:
            logger.error(f"Error loading action items: {e}")

    # Merge in details.json if it exists
    details_json_file = os.path.join(meeting_dir, 'details.json')
    if os.path.exists(details_json_file):
        try:
            with open(details_json_file, 'r') as f:
                details_json = json.load(f)
            details.update(details_json)
            logger.info(f"Merged details.json for meeting {meeting_id}")
        except Exception as e:
            logger.error(f"Error loading details.json: {e}")

    return details

def create_notion_page(notion, meeting, transcript, summary, insights, action_items, config, meeting_date_iso):
    """Create a new page in Notion with meeting details."""
    # Prepare transcript chunks
    max_chunk_size = 2000
    transcript_chunks = []

    # Split transcript into chunks of at most 2000 characters, by paragraphs
    paragraphs = transcript.split('\n\n')
    current_chunk = ''
    for paragraph in paragraphs:
        # If the paragraph itself is too long, split it
        while len(paragraph) > max_chunk_size:
            if current_chunk:
                transcript_chunks.append(current_chunk.strip())
                current_chunk = ''
            transcript_chunks.append(paragraph[:max_chunk_size])
            paragraph = paragraph[max_chunk_size:]
        if len(current_chunk) + len(paragraph) + 2 <= max_chunk_size:
            current_chunk += paragraph + '\n\n'
        else:
            if current_chunk:
                transcript_chunks.append(current_chunk.strip())
            current_chunk = paragraph + '\n\n'
    if current_chunk:
        transcript_chunks.append(current_chunk.strip())

    logger.info(f"Split transcript into {len(transcript_chunks)} chunks (max {max_chunk_size} chars each)")
    
    # Create page in Notion
    page_id = notion.create_meeting_page(
        database_id=config['notion_activities_db'],
        title=f"{meeting['title']} - {meeting['date']}",
        summary=summary or "No summary available",
        insights=insights or "No insights available",
        transcript_chunks=transcript_chunks,
        actions=action_items,
        activity_date=meeting_date_iso
    )
    
    if page_id:
        logger.info(f"Created Notion page with ID: {page_id}")
        return page_id
    else:
        logger.error("Failed to create Notion page")
        return None

def create_notion_tasks(notion, meeting, action_items, config):
    """Create tasks in Notion for each action item."""
    task_count = 0
    
    for action in action_items:
        # Parse the date if it's a string
        due_date = action.get('due_date')
        if isinstance(due_date, str):
            try:
                due_date = datetime.fromisoformat(due_date)
            except:
                due_date = datetime.now() + timedelta(days=7)
        
        task_id = notion.create_task(
            database_id=config['notion_tasks_db'],
            meeting_name=meeting['title'],
            meeting_datetime=datetime.now(),  # Approximation
            action_name=action['text'],
            owner=action.get('owner', 'Brian'),
            due_date=due_date,
            status='Not Started'
        )
        
        if task_id:
            task_count += 1
            logger.info(f"Created task: {action['text'][:50]}...")
        else:
            logger.error(f"Failed to create task: {action['text'][:50]}...")
    
    logger.info(f"Created {task_count} tasks out of {len(action_items)} action items")
    return task_count

def process_meeting(meeting, meeting_details, notion, db, config):
    """Process a single meeting and create Notion pages and tasks."""
    meeting_id = meeting['id']
    
    # Check if meeting has already been processed
    if db.is_processed(meeting_id):
        logger.info(f"Meeting {meeting_id} already processed, skipping")
        return False
    
    try:
        # Extract relevant data
        print("MEETING DETAILS DEBUG:", meeting_details)
        insights = meeting_details.get('insights', '')
        print("RAW INSIGHTS DEBUG:", repr(insights))
        if isinstance(insights, list):
            insights = '\n'.join(insights)
        print("INSIGHTS DEBUG:", repr(insights))
        transcript = meeting_details.get('transcript', '')
        # If transcript is a list of dicts, join all 'text' fields
        if isinstance(transcript, list):
            transcript = '\n\n'.join([seg.get('text', '') for seg in transcript])
        summary = meeting_details.get('summary', '')
        action_items = meeting_details.get('action_items', [])
        # Normalize action items: ensure each is a dict
        normalized = []
        for item in action_items:
            if isinstance(item, str):
                normalized.append({'text': item, 'owner': 'Brian', 'due_date': None})
            else:
                normalized.append(item)
        action_items = normalized
        # Parse meeting date for Notion
        meeting_date = meeting.get('date', '')
        # If time is missing, try to extract from title
        if meeting_date and len(meeting_date) <= 10:
            # Try to extract time from title
            title = meeting.get('title', '')
            match = re.search(r'(\d{4}-\d{2}-\d{2}) at (\d{2}\.\d{2}\.\d{2})', title)
            if match:
                date_part = match.group(1)
                time_part = match.group(2).replace('.', ':')
                meeting_date = f"{date_part} {time_part}"
        try:
            meeting_date_iso = parser.parse(meeting_date).isoformat()
        except Exception:
            meeting_date_iso = datetime.now().isoformat()
        print("MEETING DATE ISO DEBUG:", meeting_date_iso)
        # Create Notion page
        page_id = create_notion_page(notion, meeting, transcript, summary, insights, action_items, config, meeting_date_iso)
        
        # Create Notion tasks
        task_count = 0
        if page_id:
            task_count = create_notion_tasks(notion, meeting, action_items, config)
        
        # Mark meeting as processed
        db.mark_processed(
            meeting_id=meeting_id,
            meeting_title=meeting['title'],
            meeting_date=meeting['date'],
            notion_page_id=page_id,
            action_count=task_count
        )
        
        logger.info(f"Successfully processed meeting: {meeting['title']}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing meeting {meeting_id}: {e}")
        return False

def main():
    """Main function to import manually extracted Otter.ai data into Notion."""
    parser = argparse.ArgumentParser(description='Import manually extracted Otter.ai data into Notion')
    parser.add_argument('--data-dir', default='data',
                      help='Directory containing extracted data')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Check for required environment variables
    required_env_vars = ['NOTION_API_KEY']
    missing_env_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_env_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_env_vars)}")
        return
    
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration. Exiting.")
        return
    
    # Initialize database
    os.makedirs('data', exist_ok=True)
    db_path = os.path.join('data', 'processed_meetings.db')
    db = ProcessedMeetingsDB(db_path)
    
    # Initialize Notion API
    notion = NotionAPI(os.getenv('NOTION_API_KEY'))
    
    # Load meetings data
    meetings = load_meetings(args.data_dir)
    if not meetings:
        logger.error("No meetings found. Exiting.")
        return
    
    # Filter for unprocessed meetings
    unprocessed = [m for m in meetings if not db.is_processed(m['id'])]
    logger.info(f"Found {len(unprocessed)} unprocessed meetings")
    
    if not unprocessed:
        logger.info("No unprocessed meetings found. Exiting.")
        return
    
    processed_count = 0
    
    # Process each unprocessed meeting
    for meeting in unprocessed:
        try:
            logger.info(f"Processing meeting: {meeting['title']}")
            
            # Load meeting details
            meeting_details = load_meeting_details(args.data_dir, meeting['id'])
            
            # Process the meeting (create Notion pages and tasks)
            success = process_meeting(meeting, meeting_details, notion, db, config)
            
            if success:
                processed_count += 1
                logger.info(f"Successfully processed meeting: {meeting['title']}")
            else:
                logger.warning(f"Failed to process meeting: {meeting['title']}")
                
        except Exception as e:
            logger.error(f"Error processing meeting {meeting['id']}: {e}")
    
    logger.info(f"Processed {processed_count} out of {len(unprocessed)} meetings successfully")

if __name__ == "__main__":
    main() 