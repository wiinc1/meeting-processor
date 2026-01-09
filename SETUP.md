# Otter.ai to Notion Integration Setup Guide

This guide will help you set up the Otter.ai to Notion integration correctly.

## Prerequisites

- A Notion account with admin access to your workspace
- The Notion integration (named "otter asana" in this case) already created
- An Otter.ai account with API access
- Python 3.8 or higher

## 1. Environment Setup

Make sure your `.env` file in the project root contains valid API keys:

```
NOTION_API_KEY=your_notion_api_key
OTTER_API_KEY=your_otter_api_key
```

## 2. Notion Database Setup

You have two options for setting up the databases:

### Option A: Use Existing Databases

If you want to use existing databases:

1. Go to your Notion workspace
2. Navigate to each database you want to use (activities and tasks)
3. Click the "..." menu in the top-right corner
4. Select "Add connections"
5. Find and select your integration (named "otter asana" according to the test output)
6. Give the integration the necessary permissions

### Option B: Create New Databases

If you prefer to create new databases specifically for this integration:

1. Create a new database in Notion for Activities:
   - Include columns for: Name, Created, Status
   
2. Create a new database in Notion for Tasks:
   - Include columns for: Name, Meeting Name, Status, Meeting Date & Time, Action Owner, Action Due Date
   
3. Share both databases with your integration during creation

4. Update the database IDs in your `config.yaml` file:
   ```yaml
   notion_activities_db: your-activities-database-id
   notion_tasks_db: your-tasks-database-id
   max_meetings: 5
   log_file_path: otter_notion_sync.log
   ```

## 3. Testing the Connection

Run the test script to verify your setup:

```
python test_notion_minimal.py
```

You should see successful connections to both databases.

If everything is set up correctly, you can move on to testing the full integration:

```
python test_notion_connection.py
```

This will create a test page and task to confirm the integration works.

## 4. Running the Integration

Once your setup is verified, you can run the integration:

```
python main.py
```

You can also schedule the integration to run periodically:

```
python main.py --schedule=daily
```

## Troubleshooting

- **404 Error**: This usually means the integration doesn't have access to the database. Make sure you've shared the databases with your integration.
- **Authentication Error**: Check your Notion API key in the `.env` file.
- **Database ID Format**: Notion accepts database IDs with or without hyphens. Both formats should work.

## Support

If you continue to experience issues, check the logs in the `logs` directory for more detailed error information. 