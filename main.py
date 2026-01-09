import logging
import os
import asyncio
from datetime import datetime, timedelta
import schedule
import time
import sys
from dotenv import load_dotenv
import yaml
from ratelimit import limits, sleep_and_retry
from tenacity import retry, stop_after_attempt, wait_exponential
from otter_api import OtterAPI
from notion_api import NotionAPI
from nlp_processor import ActionItemDetector
from db_manager import ProcessedMeetingsDB
from otter_scraper_factory import UnifiedOtterScraper
import argparse
import traceback

def setup_logging(config):
    """Configure logging with file and console handlers."""
    log_file = config.get('log_file_path', 'otter_notion_sync.log')
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join('logs', log_file)),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Rate limit: ~3 requests/second
@sleep_and_retry
@limits(calls=3, period=1)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def rate_limited_call(func, *args, **kwargs):
    """Execute a function with rate limiting and retries."""
    logger = logging.getLogger(__name__)
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error in rate_limited_call to {func.__name__}: {e}")
        raise

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
    except yaml.YAMLError as e:
        logging.error(f"Error parsing 'config.yaml': {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error loading configuration: {e}")
        return None

def split_transcript(transcript, max_length=2000):
    """Split transcript into chunks under max_length characters."""
    try:
        import spacy
        nlp = spacy.load('en_core_web_sm')
        doc = nlp(transcript)
        chunks = []
        current_chunk = ""
        
        for sent in doc.sents:
            sent_text = sent.text.strip()
            if len(current_chunk) + len(sent_text) + 1 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sent_text
            else:
                current_chunk += " " + sent_text
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    except Exception as e:
        # Fallback to simple chunking if spaCy fails
        logging.warning(f"Error using spaCy for transcript splitting: {e}. Using fallback method.")
        chunks = []
        words = transcript.split()
        current_chunk = ""
        
        for word in words:
            if len(current_chunk) + len(word) + 1 > max_length:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = word
            else:
                if current_chunk:
                    current_chunk += " " + word
                else:
                    current_chunk = word
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks

def _extract_transcript_text(transcript_data):
    """Extract transcript text from scraper data."""
    if isinstance(transcript_data, str):
        return transcript_data
    elif isinstance(transcript_data, list):
        return '\n'.join([item.get('text', '') for item in transcript_data if isinstance(item, dict)])
    return ''

def _extract_insights_text(insights_data):
    """Extract insights text from scraper data."""
    if isinstance(insights_data, str):
        return insights_data
    elif isinstance(insights_data, list):
        return '\n'.join(insights_data)
    return ''

def _process_action_items(action_items_data):
    """Process action items from scraper data."""
    if isinstance(action_items_data, list):
        return [{'text': item, 'owner': 'Brian', 'due_date': None} for item in action_items_data]
    return []

async def process_meeting_async(meeting, otter, notion, action_detector, config, logger, db, sync_id, scraper_type='api'):
    """Process a single meeting with enhanced tracking (async version for Crawl4AI)."""
    try:
        logger.info(f"Processing meeting: {meeting['title']}")
        
        # Extract data based on scraper type
        if scraper_type == 'api':
            # Use API methods with rate limiting
            transcript = rate_limited_call(otter.get_transcript, meeting['id']) or "Not provided"
            summary = rate_limited_call(otter.get_summary, meeting['id']) or "Not provided"
            insights = rate_limited_call(otter.get_insights, meeting['id']) or "Not provided"
            otter_actions = rate_limited_call(otter.get_action_items, meeting['id']) or []
        else:
            # Use scraper methods (Selenium, Firecrawl, or Crawl4AI)
            if asyncio.iscoroutinefunction(otter.get_meeting_details):
                meeting_details = await otter.get_meeting_details(meeting['id'])
            else:
                meeting_details = otter.get_meeting_details(meeting['id'])
            
            if meeting_details:
                transcript = _extract_transcript_text(meeting_details.get('transcript', []))
                summary = meeting_details.get('summary', 'Not provided')
                insights = _extract_insights_text(meeting_details.get('insights', []))
                otter_actions = _process_action_items(meeting_details.get('action_items', []))
            else:
                transcript = "Not provided"
                summary = "Not provided"
                insights = "Not provided"
                otter_actions = []
        
        logger.info(f"Retrieved transcript: {len(transcript)} characters")
        logger.info(f"Retrieved summary: {len(summary)} characters")
        logger.info(f"Retrieved insights: {len(insights)} characters")
        logger.info(f"Retrieved {len(otter_actions)} action items from Otter")
        
        # Detect additional action items
        custom_actions = action_detector.detect_actions(transcript)
        logger.info(f"Detected {len(custom_actions)} custom action items")
        
        # Combine and deduplicate actions
        actions = []
        seen_texts = set()
        
        # First add Otter actions (they take precedence)
        for action in otter_actions:
            action_text = action.get('text', '').strip().lower()
            if action_text and action_text not in seen_texts:
                seen_texts.add(action_text)
                actions.append(action)
        
        # Then add custom actions that aren't duplicates
        for action in custom_actions:
            action_text = action.get('text', '').strip().lower()
            if action_text and action_text not in seen_texts:
                seen_texts.add(action_text)
                actions.append(action)
                
        logger.info(f"Total unique action items: {len(actions)}")
        
        # Create Notion page
        transcript_chunks = split_transcript(transcript)
        logger.info(f"Split transcript into {len(transcript_chunks)} chunks")
        
        page_id = rate_limited_call(
            notion.create_meeting_page,
            database_id=config['notion_activities_db'],
            title=f"{meeting['title']} - {meeting['date']} {meeting['time']}",
            summary=summary,
            insights=insights,
            transcript_chunks=transcript_chunks
        )
        
        if not page_id:
            logger.error(f"Failed to create Notion page for meeting {meeting['id']}")
            return {"success": False, "actions_created": 0}
        
        logger.info(f"Created Notion page: {page_id}")
        
        # Create action items in Notion
        actions_created = 0
        for action in actions:
            try:
                action_id = rate_limited_call(
                    notion.create_action_item,
                    database_id=config['notion_tasks_db'],
                    text=action['text'],
                    owner=action.get('owner', 'Brian'),
                    due_date=action.get('due_date'),
                    meeting_page_id=page_id
                )
                if action_id:
                    actions_created += 1
                    logger.info(f"Created action item: {action['text'][:50]}...")
            except Exception as action_error:
                logger.error(f"Failed to create action item: {action_error}")
        
        # Mark meeting as processed
        db.mark_processed(meeting['id'], meeting['title'])
        
        logger.info(f"Successfully processed meeting: {meeting['title']}")
        return {"success": True, "actions_created": actions_created}
        
    except Exception as e:
        logger.error(f"Error processing meeting {meeting['id']}: {e}")
        logger.error(traceback.format_exc())
        
        # Log error to database
        db.log_error(
            sync_id=sync_id,
            meeting_id=meeting['id'],
            meeting_title=meeting['title'],
            error_type=type(e).__name__,
            error_message=str(e)
        )
        
        # Create error notification task
        try:
            rate_limited_call(
                notion.create_task,
                database_id=config['notion_tasks_db'],
                title=f"Error processing meeting: {meeting['title']}",
                description=f"Error: {str(e)}",
                owner="Brian"
            )
        except Exception as task_error:
            logger.error(f"Could not create error notification task: {task_error}")
            
        return {"success": False, "actions_created": 0}

def process_meeting(meeting, otter, notion, action_detector, config, logger, db, sync_id, scraper_type='api'):
    """Process a single meeting with enhanced tracking."""
    try:
        logger.info(f"Processing meeting: {meeting['title']}")
        
        # Extract data based on scraper type
        if scraper_type == 'api':
            # Use API methods with rate limiting
            transcript = rate_limited_call(otter.get_transcript, meeting['id']) or "Not provided"
            summary = rate_limited_call(otter.get_summary, meeting['id']) or "Not provided"
            insights = rate_limited_call(otter.get_insights, meeting['id']) or "Not provided"
            otter_actions = rate_limited_call(otter.get_action_items, meeting['id']) or []
        else:
            # Use scraper methods (Selenium or Firecrawl)
            meeting_details = otter.get_meeting_details(meeting['id'])
            if meeting_details:
                transcript = _extract_transcript_text(meeting_details.get('transcript', []))
                summary = meeting_details.get('summary', 'Not provided')
                insights = _extract_insights_text(meeting_details.get('insights', []))
                otter_actions = _process_action_items(meeting_details.get('action_items', []))
            else:
                transcript = "Not provided"
                summary = "Not provided"
                insights = "Not provided"
                otter_actions = []
        
        logger.info(f"Retrieved transcript: {len(transcript)} characters")
        logger.info(f"Retrieved summary: {len(summary)} characters")
        logger.info(f"Retrieved insights: {len(insights)} characters")
        logger.info(f"Retrieved {len(otter_actions)} action items from Otter")
        
        # Detect additional action items
        custom_actions = action_detector.detect_actions(transcript)
        logger.info(f"Detected {len(custom_actions)} custom action items")
        
        # Combine and deduplicate actions
        actions = []
        seen_texts = set()
        
        # First add Otter actions (they take precedence)
        for action in otter_actions:
            action_text = action.get('text', '').strip().lower()
            if action_text and action_text not in seen_texts:
                seen_texts.add(action_text)
                actions.append(action)
        
        # Then add custom actions that aren't duplicates
        for action in custom_actions:
            action_text = action.get('text', '').strip().lower()
            if action_text and action_text not in seen_texts:
                seen_texts.add(action_text)
                actions.append(action)
                
        logger.info(f"Total unique action items: {len(actions)}")
        
        # Create Notion page
        transcript_chunks = split_transcript(transcript)
        logger.info(f"Split transcript into {len(transcript_chunks)} chunks")
        
        page_id = rate_limited_call(
            notion.create_meeting_page,
            database_id=config['notion_activities_db'],
            title=f"{meeting['title']} - {meeting['date']} {meeting['time']}",
            summary=summary,
            insights=insights,
            transcript_chunks=transcript_chunks,
            actions=actions
        )
        
        if not page_id:
            logger.error(f"Failed to create Notion page for meeting: {meeting['id']}")
            # Log error in database
            db.log_error(sync_id, meeting['id'], 'notion_page_creation', 'Failed to create Notion page')
            # Mark as processed but with error status
            db.mark_processed(
                meeting_id=meeting['id'],
                meeting_title=meeting['title'],
                meeting_date=meeting['date'],
                notion_page_id=None,
                action_count=0
            )
            db.update_meeting_status(meeting['id'], sync_status='failed')
            return False
            
        logger.info(f"Created Notion page with ID: {page_id}")
        
        # Create Notion tasks
        task_success_count = 0
        for action in actions:
            task_id = rate_limited_call(
                notion.create_task,
                database_id=config['notion_tasks_db'],
                meeting_name=meeting['title'],
                meeting_datetime=meeting['datetime'],
                action_name=action['text'],
                owner=action.get('owner', 'Brian'),
                due_date=action.get('due_date', datetime.now() + timedelta(days=7)),
                status='Not Started'
            )
            
            if task_id:
                task_success_count += 1
                
        logger.info(f"Created {task_success_count} tasks out of {len(actions)} action items")
        
        # Mark meeting as successfully processed with all metadata
        db.mark_processed(
            meeting_id=meeting['id'],
            meeting_title=meeting['title'],
            meeting_date=meeting['date'],
            notion_page_id=page_id,
            action_count=task_success_count
        )
        
        return {"success": True, "actions_created": task_success_count}
        
    except Exception as e:
        logger.error(f"Error processing meeting {meeting['id']}: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Log the error in the database
        if 'db' in locals() and 'sync_id' in locals():
            db.log_error(sync_id, meeting['id'], 'process_error', str(e))
        
        # Create an error notification task in Notion
        try:
            rate_limited_call(
                notion.create_task,
                database_id=config['notion_tasks_db'],
                meeting_name='Error Log',
                meeting_datetime=datetime.now(),
                action_name=f"Investigate error: {str(e)}",
                owner='Brian',
                due_date=datetime.now(),
                status='High Priority'
            )
        except Exception as task_error:
            logger.error(f"Could not create error notification task: {task_error}")
            
        return {"success": False, "actions_created": 0}

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Otter.ai to Notion Sync Utility')
    parser.add_argument('--run-once', action='store_true', help='Process meetings once and exit')
    parser.add_argument('--schedule', action='store_true', help='Run every 3 hours')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--stats', action='store_true', help='Show statistics and exit')
    parser.add_argument('--scraper', choices=['api', 'selenium', 'firecrawl', 'crawl4ai', 'auto'], 
                        default='auto', help='Scraper backend to use (default: auto)')
    parser.add_argument('--browser', choices=['chrome', 'firefox', 'safari', 'chromium', 'webkit'], 
                        default='chrome', help='Browser for Selenium/Crawl4AI backend')
    parser.add_argument('--headless', action='store_true', 
                        help='Run browser in headless mode')
    parser.add_argument('--profile-dir', help='Chrome profile directory (Selenium only)')
    return parser.parse_args()

def display_stats(db, logger):
    """Display statistics about the synchronization history."""
    logger.info("Retrieving synchronization statistics...")
    
    # Get total counts
    totals = db.get_total_counts()
    logger.info("=== Otter.ai to Notion Sync Statistics ===")
    logger.info(f"Total meetings processed: {totals['total_meetings']}")
    logger.info(f"Total action items created: {totals['total_actions']}")
    logger.info(f"Total errors encountered: {totals['total_errors']}")
    logger.info(f"Total sync sessions: {totals['total_syncs']}")
    
    # Get recent sync sessions
    recent_syncs = db.get_sync_stats(days=7)
    if recent_syncs:
        logger.info("\nRecent sync sessions (last 7 days):")
        for sync in recent_syncs:
            start_time = datetime.fromisoformat(sync['sync_start'])
            end_time = datetime.fromisoformat(sync['sync_end']) if sync['sync_end'] else None
            
            if end_time:
                duration = (end_time - start_time).total_seconds() / 60
                logger.info(f"Session {sync['sync_id']}: {start_time.strftime('%Y-%m-%d %H:%M')} - Processed {sync['meetings_processed']} meetings in {duration:.1f} minutes")
            else:
                logger.info(f"Session {sync['sync_id']}: {start_time.strftime('%Y-%m-%d %H:%M')} - IN PROGRESS")
    
    # Get recent errors
    recent_errors = db.get_error_report(days=7)
    if recent_errors:
        logger.info("\nRecent errors (last 7 days):")
        for error in recent_errors:
            error_time = datetime.fromisoformat(error['error_time'])
            meeting_title = error['meeting_title'] or f"Meeting ID: {error['meeting_id']}"
            logger.info(f"{error_time.strftime('%Y-%m-%d %H:%M')} - {meeting_title} - {error['error_type']}: {error['error_message'][:100]}...")
    
    return totals

def main():
    """Main function to orchestrate Otter.ai to Notion sync."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Check for required environment variables
        required_env_vars = ['NOTION_API_KEY']
        missing_env_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        # Check for either API key or username/password for Otter
        has_otter_auth = (os.getenv('OTTER_API_KEY') and os.getenv('OTTER_API_KEY') != 'test_key') or \
                        (os.getenv('OTTER_USERNAME') and os.getenv('OTTER_PASSWORD'))
        
        if not has_otter_auth:
            missing_env_vars.append('OTTER authentication (either OTTER_API_KEY or OTTER_USERNAME/OTTER_PASSWORD)')
        
        if missing_env_vars:
            print(f"ERROR: Missing required environment variables: {', '.join(missing_env_vars)}")
            print("Please create a .env file with these variables or set them in your environment.")
            sys.exit(1)
        
        # Load configuration
        config = load_config()
        if not config:
            print("ERROR: Failed to load configuration. Exiting.")
            sys.exit(1)
        
        # Setup logging
        logger = setup_logging(config)
        
        # Parse command-line arguments
        args = parse_arguments()
        
        # Set log level based on args
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Debug logging enabled")
        else:
            # Force enable debug logging temporarily for troubleshooting
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Debug logging forcibly enabled for troubleshooting")
        
        # Initialize database
        db_path = os.path.join('data', 'processed_meetings.db')
        db = ProcessedMeetingsDB(db_path)
        
        # If stats flag is provided, show statistics and exit
        if args.stats:
            display_stats(db, logger)
            return
        
        # Initialize APIs and utilities
        logger.info("Initializing APIs and utilities")
        
        # Initialize Otter scraper based on selected backend
        if args.scraper == 'api':
            # Use direct API approach
            if os.getenv('OTTER_API_KEY') and os.getenv('OTTER_API_KEY') != 'test_key':
                logger.info("Using Otter.ai API key for authentication")
                otter = OtterAPI(api_key=os.getenv('OTTER_API_KEY'))
            else:
                logger.info("Using Otter.ai username/password for authentication")
                otter = OtterAPI(
                    username=os.getenv('OTTER_USERNAME'),
                    password=os.getenv('OTTER_PASSWORD')
                )
        else:
            # Use unified scraper (Selenium, Firecrawl, or Crawl4AI)
            logger.info(f"Using {args.scraper} scraper backend")
            otter = UnifiedOtterScraper(
                backend=args.scraper,
                browser=args.browser,
                headless=args.headless,
                profile_dir=args.profile_dir,
                browser_type=args.browser if args.scraper == 'crawl4ai' else None
            )
            # Set up scraper if needed (for Selenium)
            otter.setup()
        
        notion = NotionAPI(os.getenv('NOTION_API_KEY'))
        action_detector = ActionItemDetector()
        
        async def run():
            """Run the synchronization process."""
            logger.info("Starting Otter.ai to Notion sync")
            
            # Start a new sync session
            sync_id = db.start_sync_session()
            logger.info(f"Started sync session with ID: {sync_id}")
            
            meetings_processed = 0
            actions_created = 0
            errors = 0
            
            try:
                # Get recent meetings based on scraper type
                if args.scraper == 'api':
                    # Use API method
                    meetings = rate_limited_call(otter.get_recent_meetings, limit=config['max_meetings'])
                else:
                    # Use scraper method (Selenium, Firecrawl, or Crawl4AI)
                    if hasattr(otter, 'authenticate'):
                        if asyncio.iscoroutinefunction(otter.authenticate):
                            await otter.authenticate()
                        else:
                            otter.authenticate()
                    
                    if asyncio.iscoroutinefunction(otter.get_all_meetings):
                        meetings = await otter.get_all_meetings(limit=config['max_meetings'])
                    else:
                        meetings = otter.get_all_meetings(limit=config['max_meetings'])
                logger.info(f"Retrieved {len(meetings)} recent meetings from Otter.ai")
                
                if not meetings:
                    logger.warning("No meetings retrieved from Otter.ai")
                    # End the sync session with zeroes
                    db.end_sync_session(sync_id, 0, 0, 0)
                    return
                
                # Filter for unprocessed meetings
                unprocessed = [m for m in meetings if not db.is_processed(m['id'])]
                logger.info(f"Found {len(unprocessed)} unprocessed meetings")
                
                if not unprocessed:
                    logger.info("No unprocessed meetings found")
                    # End the sync session with zeroes
                    db.end_sync_session(sync_id, 0, 0, 0)
                    return
                
                # Process each unprocessed meeting
                for meeting in unprocessed:
                    logger.info(f"Processing meeting: {meeting['title']} ({meeting['id']})")
                    if args.scraper in ['crawl4ai'] and hasattr(otter, 'get_meeting_details'):
                        # For async scrapers, we need to handle the async process_meeting
                        result = await process_meeting_async(meeting, otter, notion, action_detector, config, logger, db, sync_id, args.scraper)
                    else:
                        result = process_meeting(meeting, otter, notion, action_detector, config, logger, db, sync_id, args.scraper)
                    
                    if result["success"]:
                        meetings_processed += 1
                        actions_created += result["actions_created"]
                        logger.info(f"Successfully processed meeting: {meeting['title']}")
                    else:
                        errors += 1
                        logger.warning(f"Failed to process meeting: {meeting['title']}")
                
                logger.info(f"Processed {meetings_processed} out of {len(unprocessed)} meetings successfully")
                
            except Exception as e:
                logger.error(f"Error during sync run: {str(e)}")
                logger.error(traceback.format_exc())
                errors += 1
                # Log the error in the database
                db.log_error(sync_id, "sync_session", "run_error", str(e))
            finally:
                # End the sync session with statistics
                db.end_sync_session(sync_id, meetings_processed, actions_created, errors)
                logger.info(f"Sync session {sync_id} completed with {meetings_processed} meetings processed, {actions_created} actions created, and {errors} errors")
        
        # Execute based on command-line arguments
        if args.run_once:
            logger.info("Running in single-run mode")
            if args.scraper in ['crawl4ai']:
                asyncio.run(run())
            else:
                run()
            logger.info("Single run completed")
            
            # Display statistics after the run
            display_stats(db, logger)
            
        elif args.schedule:
            logger.info("Running in scheduled mode (every 3 hours)")
            
            # Schedule to run every 3 hours
            if args.scraper in ['crawl4ai']:
                schedule.every(3).hours.do(lambda: asyncio.run(run()))
            else:
                schedule.every(3).hours.do(run)
            logger.info("Scheduled task for every 3 hours")
            
            # Run once immediately
            logger.info("Running initial sync")
            if args.scraper in ['crawl4ai']:
                asyncio.run(run())
            else:
                run()
            
            # Display initial statistics
            display_stats(db, logger)
            
            # Keep running
            logger.info("Entering scheduling loop")
            try:
                while True:
                    schedule.run_pending()
                    time.sleep(60)
            except KeyboardInterrupt:
                logger.info("Scheduling interrupted by user. Exiting...")
                
        else:
            logger.error("No valid argument provided. Use --run-once, --schedule, or --stats.")
            print("Please specify either --run-once, --schedule, or --stats. Use --help for more information.")
            return
        
        # Clean up scraper if needed
        if args.scraper != 'api' and hasattr(otter, 'close'):
            if args.scraper in ['crawl4ai'] and asyncio.iscoroutinefunction(otter.close):
                asyncio.run(otter.close())
            else:
                otter.close()
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        if 'logger' in locals():
            logger.critical(f"Fatal error: {str(e)}")
            logger.critical(traceback.format_exc())
        else:
            print(f"CRITICAL ERROR: {str(e)}")
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main() 