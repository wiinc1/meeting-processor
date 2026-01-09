import os
from notion_api import NotionAPI
import logging
import yaml
from datetime import datetime

# Try different import statements for dotenv
try:
    from dotenv import load_dotenv
except ImportError:
    try:
        from python_dotenv import load_dotenv
    except ImportError:
        print("ERROR: Could not import dotenv. Please install with 'pip install python-dotenv'")
        exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_notion_connection():
    # Load environment variables
    load_dotenv()
    
    # Get Notion API key
    notion_api_key = os.getenv('NOTION_API_KEY')
    if not notion_api_key:
        logger.error("No Notion API key found in environment variables")
        return
    
    logger.info(f"Using Notion API key: {notion_api_key[:4]}...{notion_api_key[-4:] if len(notion_api_key) > 8 else ''}")
    
    # Get database IDs from config
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            
        notion_activities_db = config.get('notion_activities_db')
        notion_tasks_db = config.get('notion_tasks_db')
        
        logger.info(f"Activities database ID: {notion_activities_db}")
        logger.info(f"Tasks database ID: {notion_tasks_db}")
    except Exception as e:
        logger.error(f"Error reading config file: {e}")
        return
    
    # Initialize Notion API
    try:
        notion = NotionAPI(notion_api_key)
        logger.info("Notion API client initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing Notion API client: {e}")
        return
    
    # Test creating a test page in the database
    try:
        page_id = notion.create_meeting_page(
            database_id=notion_activities_db,
            title="Test Meeting - API Test",
            summary="This is a test meeting summary created to verify the Notion API connection.",
            insights="Test insights",
            transcript_chunks=["This is a test transcript chunk."],
            actions=[{"text": "Test action item", "owner": "Test User", "due_date": None}]
        )
        
        if page_id:
            logger.info(f"Successfully created test page with ID: {page_id}")
            logger.info(f"View the page at: https://notion.so/{page_id.replace('-', '')}")
        else:
            logger.error("Failed to create test page")
        
        # Test creating a task
        logger.info("Testing task creation...")
        
        task_id = notion.create_task(
            database_id=notion_tasks_db,
            meeting_name="Test Meeting",
            meeting_datetime=datetime.now(),
            action_name="Test Action Item",
            owner="Sarah Jones",  # This will be included in the task description
            due_date=None,  # Will default to 1 week from now
            status="Not Started"
        )
        
        if task_id:
            logger.info(f"Successfully created test task with ID: {task_id}")
            logger.info(f"View the task at: https://notion.so/{task_id.replace('-', '')}")
        else:
            logger.error("Failed to create test task")
    except Exception as e:
        logger.error(f"Error in test: {e}")

if __name__ == "__main__":
    test_notion_connection() 