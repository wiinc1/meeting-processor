#!/usr/bin/env python
import os
from notion_api import NotionAPI
import logging
import yaml
from datetime import datetime, timedelta

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

def test_notion_task_creation():
    # Load environment variables
    load_dotenv()
    
    # Get Notion API key
    notion_api_key = os.getenv('NOTION_API_KEY')
    if not notion_api_key:
        logger.error("No Notion API key found in environment variables")
        return
    
    logger.info(f"Using Notion API key: {notion_api_key[:4]}...{notion_api_key[-4:] if len(notion_api_key) > 8 else ''}")
    
    # Get database IDs from config or .env file
    try:
        # Try config file first
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            
        notion_tasks_db = config.get('notion_tasks_db')
        
        # If not in config, try .env
        if not notion_tasks_db:
            notion_tasks_db = os.getenv('NOTION_DATABASE_ACTION_ITEMS')
            
        if not notion_tasks_db:
            logger.error("Tasks database ID not found in config.yaml or .env")
            return
            
        logger.info(f"Using Tasks database ID: {notion_tasks_db}")
        
        # Initialize Notion API
        notion = NotionAPI(notion_api_key)
        
        # Test data
        test_meeting_name = "Test Meeting for Task Owner"
        test_meeting_datetime = datetime.now()
        
        # Create test task with original owner identified in transcript
        original_owner = "Alice"
        task_id = notion.create_task(
            database_id=notion_tasks_db,
            meeting_name=test_meeting_name,
            meeting_datetime=test_meeting_datetime,
            action_name=f"Review the quarterly report",
            owner=original_owner,  # This should be included in the task description
            due_date=datetime.now() + timedelta(days=3),
            status='Not Started'
        )
        
        if task_id:
            logger.info(f"✅ Successfully created task in Notion with ID: {task_id}")
            logger.info(f"The task should be assigned to Brian but mention that it was originally for {original_owner}")
            logger.info(f"Check your Notion tasks database to verify")
        else:
            logger.error("❌ Failed to create task in Notion")
            
    except Exception as e:
        logger.error(f"Error testing Notion task creation: {str(e)}")

if __name__ == "__main__":
    test_notion_task_creation() 