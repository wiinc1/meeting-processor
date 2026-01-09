# Otter.ai to Notion Integration with Selenium

This guide explains how to use the Selenium-based Otter.ai scraper to extract meeting data and integrate it with Notion.

## Prerequisites

- Python 3.8 or higher
- Chrome or Firefox browser installed
- Otter.ai account (with Apple ID for login)
- Notion account with integration set up
- Notion databases for meeting activities and tasks

## Setup

1. Install required Python packages:
   ```
   pip install selenium webdriver-manager python-dotenv pyyaml requests
   ```

2. Update your `.env` file with the necessary credentials:
   ```
   NOTION_API_KEY=your_notion_api_key
   NOTION_DATABASE_MEETINGS=your_meetings_database_id
   NOTION_DATABASE_ACTION_ITEMS=your_tasks_database_id
   APPLE_ID=your_apple_id@example.com
   APPLE_PASSWORD=your_apple_password
   ```

   Note: If you leave `APPLE_ID` and `APPLE_PASSWORD` empty, the script will open the browser for you to manually log in.

3. Make sure your `config.yaml` file has the correct database IDs:
   ```yaml
   notion_activities_db: 86e4319e-46c6-4c26-8c2a-d14f13ce32f9
   notion_tasks_db: 1f5c54e7-c4ed-804c-9d8a-eaf3d4d91d02
   max_meetings: 5
   log_file_path: otter_notion_sync.log
   ```

## Usage

### Standalone Otter.ai Scraper

To use just the Otter.ai scraper (no Notion integration):

```bash
python otter_selenium.py --browser chrome
```

Optional arguments:
- `--browser`: Choose between `chrome` or `firefox` (default: `chrome`)
- `--headless`: Run the browser in headless mode (no visible window)
- `--limit`: Maximum number of meetings to extract (default: 5)
- `--output`: Directory to save the extracted data (default: `data`)

This will:
1. Open a browser window
2. Navigate to Otter.ai's login page
3. Click on "Continue with Apple"
4. Wait for you to complete the authentication (unless Apple credentials are provided)
5. Extract meeting data and save it to the specified output directory

### Full Otter.ai to Notion Integration

To run the full integration (scrape Otter.ai and create Notion pages/tasks):

```bash
python otter_to_notion.py --browser chrome
```

Optional arguments:
- Same as with `otter_selenium.py`
- `--data-dir`: Directory to save extracted data (default: `data`)

This will:
1. Scrape Otter.ai as described above
2. Create a page in Notion for each meeting
3. Create tasks for each action item detected
4. Track which meetings have been processed to avoid duplicates

## Manual Authentication Flow

If you don't provide Apple ID credentials, the script will:

1. Open the browser and navigate to Otter.ai's login page
2. Click the "Continue with Apple" button
3. Wait for you to manually enter your credentials and complete any verification steps
4. Prompt you to press Enter in the terminal once you've completed authentication
5. Continue with the extraction process

## Notes

- The Selenium scraper is designed to handle different Otter.ai UI layouts, but it may need adjustments if the site changes significantly.
- All action items are assigned to "Brian" in Notion, but the original person from the transcript is included in the task description.
- If you encounter "No such element" or "Element not found" errors, the script may need to be updated to match Otter.ai's current UI.
- The script creates a SQLite database to track processed meetings and avoid duplicates.
- Data is saved locally in the `data` directory (or your custom directory) for backup and debugging purposes. 