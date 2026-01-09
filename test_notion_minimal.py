#!/usr/bin/env python
import os
import logging
import yaml
import requests
from dotenv import load_dotenv

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
    
    # Test Notion API connection by making a simple users/me request
    try:
        headers = {
            'Authorization': f'Bearer {notion_api_key}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
        
        logger.info("Testing connection to Notion API...")
        response = requests.get('https://api.notion.com/v1/users/me', headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            user_name = user_data.get('name', 'Unknown')
            logger.info(f"✓ Connection successful! Connected as: {user_name}")
            logger.info(f"✓ Bot ID: {user_data.get('bot', {}).get('id', 'Unknown')}")
            logger.info(f"✓ Workspace name: {user_data.get('workspace_name', 'Unknown')}")
        else:
            logger.error(f"✗ Failed to connect to Notion API: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return
        
        # Try to fetch databases to verify permissions
        for db_name, db_id in [("Activities", notion_activities_db), ("Tasks", notion_tasks_db)]:
            logger.info(f"Testing access to {db_name} database...")
            try:
                response = requests.get(f'https://api.notion.com/v1/databases/{db_id}', headers=headers)
                
                if response.status_code == 200:
                    logger.info(f"✓ Successfully accessed {db_name} database!")
                    db_title = response.json().get('title', [{}])[0].get('text', {}).get('content', 'Untitled')
                    logger.info(f"  Database title: {db_title}")
                else:
                    logger.error(f"✗ Failed to access {db_name} database: {response.status_code}")
                    logger.error(f"  Response: {response.text}")
                    logger.error(f"  Make sure the database is shared with your integration")
            except Exception as e:
                logger.error(f"Error accessing {db_name} database: {e}")
    
    except Exception as e:
        logger.error(f"Error testing Notion API connection: {e}")

if __name__ == "__main__":
    test_notion_connection() 