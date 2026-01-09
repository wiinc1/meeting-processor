#!/usr/bin/env python
import os
import logging
import yaml
import json
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_notion_schema():
    # Load environment variables
    load_dotenv()
    
    # Get Notion API key
    notion_api_key = os.getenv('NOTION_API_KEY')
    if not notion_api_key:
        logger.error("No Notion API key found in environment variables")
        return
    
    # Get database IDs from config.yaml
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
    
    # Set up headers for API requests
    headers = {
        'Authorization': f'Bearer {notion_api_key}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }
    
    # Check schema for both databases
    for db_name, db_id in [("Activities", notion_activities_db), ("Tasks", notion_tasks_db)]:
        logger.info(f"\nChecking schema for {db_name} database...")
        try:
            response = requests.get(f'https://api.notion.com/v1/databases/{db_id}', headers=headers)
            
            if response.status_code == 200:
                db_data = response.json()
                
                # Get database title
                db_title = db_data.get('title', [{}])[0].get('text', {}).get('content', 'Untitled')
                logger.info(f"Database Title: {db_title}")
                
                # Get properties
                properties = db_data.get('properties', {})
                logger.info("Properties:")
                
                for prop_name, prop_details in properties.items():
                    prop_type = prop_details.get('type', 'unknown')
                    logger.info(f"  - {prop_name} ({prop_type})")
                
                # Print JSON format for reference
                logger.info("\nFull Properties JSON:")
                logger.info(json.dumps(properties, indent=2))
                
            else:
                logger.error(f"Failed to access {db_name} database: {response.status_code}")
                logger.error(f"Response: {response.text}")
        except Exception as e:
            logger.error(f"Error checking schema for {db_name} database: {e}")

if __name__ == "__main__":
    check_notion_schema() 