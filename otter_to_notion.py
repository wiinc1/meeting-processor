#!/usr/bin/env python
import os
import logging
import yaml
import json
from datetime import datetime, timedelta
import argparse
from dotenv import load_dotenv
from otter_selenium import OtterSelenium
from notion_api import NotionAPI
from db_manager import ProcessedMeetingsDB
from nlp_processor import ActionItemDetector

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

def parse_action_items(transcript, meeting_details=None):
    """Parse action items from the transcript and meeting details."""
    # Initialize action item detector
    action_detector = ActionItemDetector()
    
    # Detect action items from transcript
    detected_actions = action_detector.detect_actions(transcript)
    
    # Combine with any action items from Otter.ai
    all_actions = []
    seen_texts = set()
    
    # Add detected action items first
    for action in detected_actions:
        action_text = action.get('text', '').strip().lower()
        if action_text and action_text not in seen_texts:
            seen_texts.add(action_text)
            all_actions.append(action)
            
    # If we have meeting details, add any action items from Otter.ai
    if meeting_details and 'action_items' in meeting_details:
        for action in meeting_details['action_items']:
            action_text = action.get('text', '').strip().lower()
            if action_text and action_text not in seen_texts:
                seen_texts.add(action_text)
                all_actions.append(action)
    
    logger.info(f"Found {len(all_actions)} unique action items")
    return all_actions

def create_notion_page(notion, meeting, transcript, summary, action_items, config):
    """Create a new page in Notion with meeting details."""
    # Prepare transcript chunks
    max_chunk_size = 2000
    transcript_chunks = []
    
    # Simple chunking by paragraphs
    paragraphs = transcript.split('\n\n')
    current_chunk = ""
    
    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 2 <= max_chunk_size:
            current_chunk += paragraph + "\n\n"
        else:
            if current_chunk:
                transcript_chunks.append(current_chunk.strip())
            current_chunk = paragraph + "\n\n"
    
    if current_chunk:
        transcript_chunks.append(current_chunk.strip())
        
    logger.info(f"Split transcript into {len(transcript_chunks)} chunks")
    
    # Create page in Notion
    page_id = notion.create_meeting_page(
        database_id=config['notion_activities_db'],
        title=f"{meeting['title']} - {meeting['date']} {meeting.get('time', '')}",
        summary=summary or "No summary available",
        insights="",  # No insights available from Selenium scraper
        transcript_chunks=transcript_chunks,
        actions=action_items
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
        task_id = notion.create_task(
            database_id=config['notion_tasks_db'],
            meeting_name=meeting['title'],
            meeting_datetime=meeting.get('datetime', datetime.now()),
            action_name=action['text'],
            owner=action.get('owner', 'Brian'),
            due_date=action.get('due_date', datetime.now() + timedelta(days=7)),
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
        transcript = meeting_details.get('transcript', '')
        summary = meeting_details.get('summary', '')
        
        # Parse action items
        action_items = parse_action_items(transcript, meeting_details)
        
        # Create Notion page
        page_id = create_notion_page(notion, meeting, transcript, summary, action_items, config)
        
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
    """Main function to orchestrate Otter.ai Selenium to Notion sync."""
    parser = argparse.ArgumentParser(description='Sync Otter.ai meetings to Notion using Selenium')
    parser.add_argument('--browser', choices=['chrome', 'firefox', 'safari'], default='safari',
                      help='Browser to use for automation')
    parser.add_argument('--headless', action='store_true', 
                      help='Run browser in headless mode')
    parser.add_argument('--data-dir', default='data',
                      help='Directory to store extracted data')
    parser.add_argument('--profile-dir', default=None, help='(Chrome only) Path to Chrome user profile directory for session reuse')
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
    
    # Initialize Otter.ai Selenium scraper
    otter = OtterSelenium(browser=args.browser, headless=args.headless)
    otter.profile_dir = args.profile_dir if args.browser == 'chrome' else None
    
    try:
        # Set up the WebDriver
        otter.setup_driver()
        
        # Login to Otter.ai with Apple
        if otter.login_with_apple():
            logger.info("Successfully logged in to Otter.ai")
            
            # Get all meetings
            meetings = otter.get_all_meetings()
            logger.info(f"Found {len(meetings)} meetings (all meetings loaded)")
            
            if not meetings:
                logger.warning("No meetings found. Exiting.")
                return
            
            # Filter for unprocessed meetings
            unprocessed = [m for m in meetings if not db.is_processed(m['id'])]
            logger.info(f"Found {len(unprocessed)} unprocessed meetings")
            
            if not unprocessed:
                logger.info("No unprocessed meetings found. Exiting.")
                return
            
            processed_count = 0
            total_meetings = len(unprocessed)
            
            # Process each unprocessed meeting
            for idx, meeting in enumerate(unprocessed, 1):
                try:
                    progress_msg = f"Processing meeting {idx} of {total_meetings}: {meeting['title']}"
                    logger.info(progress_msg)
                    print(progress_msg)
                    
                    # Get meeting details
                    meeting_details = otter.get_meeting_details(meeting['id'])
                    
                    # Save details to files
                    meeting_dir = os.path.join(args.data_dir, meeting['id'])
                    os.makedirs(meeting_dir, exist_ok=True)
                    
                    with open(os.path.join(meeting_dir, 'details.json'), 'w') as f:
                        json.dump(meeting_details, f, indent=2, default=str)
                    
                    # Process the meeting (create Notion pages and tasks)
                    success = process_meeting(meeting, meeting_details, notion, db, config)
                    
                    if success:
                        processed_count += 1
                        logger.info(f"Successfully processed meeting: {meeting['title']}")
                        print(f"Successfully processed meeting: {meeting['title']}")
                    else:
                        logger.warning(f"Failed to process meeting: {meeting['title']}")
                        print(f"Failed to process meeting: {meeting['title']}")
                        
                except Exception as e:
                    logger.error(f"Error processing meeting {meeting['id']}: {e}")
                    print(f"Error processing meeting {meeting['id']}: {e}")
            
            logger.info(f"Processed {processed_count} out of {len(unprocessed)} meetings successfully")
            
        else:
            logger.error("Failed to log in to Otter.ai")
            
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        
    finally:
        # Always close the browser
        otter.close()

if __name__ == "__main__":
    main() 