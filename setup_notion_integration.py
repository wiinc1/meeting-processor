#!/usr/bin/env python
import os
import yaml
from dotenv import load_dotenv

def setup_notion_integration():
    # Load environment variables
    load_dotenv()
    
    # Get Notion API key
    notion_api_key = os.getenv('NOTION_API_KEY')
    if not notion_api_key:
        print("ERROR: No Notion API key found in .env file")
        return

    # Load database IDs from config
    try:
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
            
        activities_db = config.get('notion_activities_db')
        tasks_db = config.get('notion_tasks_db')
    except Exception as e:
        print(f"Error reading config file: {e}")
        return
    
    # Extract integration ID from the API key (if possible)
    # Some API keys may not expose this information
    integration_id = None
    if notion_api_key.startswith('ntn_'):
        # Try to extract integration info
        parts = notion_api_key.split('_')
        if len(parts) > 1:
            integration_id = parts[1][:8] + "..." if len(parts[1]) > 8 else parts[1]
    
    # Print setup instructions
    print("\n===== NOTION INTEGRATION SETUP INSTRUCTIONS =====\n")
    print("To use your Notion databases with this application, you need to share them with your integration:")
    
    print("\n1. Go to the following Notion database pages:")
    print(f"   - Activities database: https://notion.so/{activities_db.replace('-', '')}")
    print(f"   - Tasks database: https://notion.so/{tasks_db.replace('-', '')}")
    
    print("\n2. For each database:")
    print("   a. Click the '...' menu in the top-right corner")
    print("   b. Select 'Add connections'")
    print("   c. Find and select your integration")
    
    if integration_id:
        print(f"\n   Your integration ID starts with: {integration_id}")
    
    print("\n3. Verify that:")
    print("   - Your integration name matches what you created in the Notion Integrations page")
    print("   - Both databases are shared with the integration")
    
    print("\n4. After sharing the databases, run the test_notion_connection.py script again")
    
    print("\nNOTE: If the database URLs above don't work, you may need to find the databases manually in your Notion workspace.")
    print("      Make sure the database IDs in config.yaml match your actual databases.")

if __name__ == "__main__":
    setup_notion_integration() 