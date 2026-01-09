import requests
import browser_cookie3
import time
import os
import yaml
from dotenv import load_dotenv
from notion_api import NotionAPI
from nlp_processor import ActionItemDetector
from datetime import datetime, timedelta
import argparse

# Load environment variables
load_dotenv()
notion_api_key = os.getenv('NOTION_API_KEY')
if not notion_api_key:
    print("ERROR: No Notion API key found in .env file")
    exit(1)

# Load Notion database IDs from config.yaml
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)
notion_activities_db = config.get('notion_activities_db')
notion_tasks_db = config.get('notion_tasks_db')

# Initialize Notion API and ActionItemDetector
notion = NotionAPI(notion_api_key)
action_detector = ActionItemDetector()

# Get Chrome cookies for otter.ai
cookies = browser_cookie3.chrome(domain_name='otter.ai')

# Extract user ID from cookies
user_id = None
for c in cookies:
    if c.name == 'user_id':
        user_id = c.value
        break
# MANUAL OVERRIDE: Set user_id directly for reliability
user_id = "10564255"  # <-- Set your Otter.ai user_id here
print(f"Detected user_id from cookies or override: {user_id}")

# The API endpoint
url = "https://otter.ai/forward/api/v1/available_speeches"

# Initial parameters
params = {
    "funnel": "home_feed",
    "page_size": 20,  # Adjust as needed (max may be enforced by server)
    "source": "home",
    "speech_metadata": "true"
}

all_meetings = []
modified_after = None
page = 1

def get_full_transcript_from_outline(speech_outline):
    transcript_lines = []
    for section in speech_outline or []:
        section_title = section.get('text', '').strip()
        if section_title:
            transcript_lines.append(section_title)
        for seg in section.get('segments', []) or []:
            seg_text = seg.get('text', '').strip()
            if seg_text:
                transcript_lines.append(seg_text)
    return '\n'.join(transcript_lines)

# Helper function to split text into <=2000 Unicode code point chunks
MAX_BLOCK_SIZE = 2000
def chunk_text(text, max_size=MAX_BLOCK_SIZE):
    # Ensure input is a string
    if not isinstance(text, str):
        text = str(text)
    return [text[i:i+max_size] for i in range(0, len(text), max_size)] if text else []

def main():
    parser = argparse.ArgumentParser(description="Fetch Otter.ai meetings and sync to Notion.")
    parser.add_argument('--otid', type=str, help='Specific Otter meeting otid to process')
    args = parser.parse_args()

    if args.otid:
        otid = args.otid
        print(f"[INFO] Processing only otid: {otid}")
        # Fetch the meeting data for this otid from the available_speeches API
        # (since /speech does not have outline, use available_speeches to get outline)
        url = "https://otter.ai/forward/api/v1/available_speeches"
        params = {
            "funnel": "home_feed",
            "page_size": 100,
            "source": "home",
            "speech_metadata": "true"
        }
        response = requests.get(url, params=params, cookies=cookies)
        response.raise_for_status()
        data = response.json()
        speeches = data.get("speeches", [])
        meeting = next((m for m in speeches if m.get('speech_id') == otid or m.get('otid') == otid), None)
        if not meeting:
            print(f"[ERROR] Could not find meeting with otid {otid} in available_speeches.")
            return
        title = meeting.get('title', f'Otter Meeting {otid}')
        summary = meeting.get('summary', '')
        speech_outline = meeting.get('speech_outline', [])
        transcript_blocks = []
        if speech_outline:
            full_transcript = get_full_transcript_from_outline(speech_outline)
            transcript_blocks = chunk_text(full_transcript)
            print(f"[DEBUG] Transcript blocks (from outline): {len(transcript_blocks)}")
            for b in transcript_blocks[:3]:
                print(f"    {b}")
        else:
            print(f"[WARNING] No speech_outline found. Falling back to summary.")
            transcript_blocks = chunk_text(summary)
        final_insights_list = transcript_blocks
        final_transcript_chunks = transcript_blocks
        try:
            page_id = notion.create_meeting_page(
                database_id=notion_activities_db,
                title=title,
                summary=summary,
                insights=final_insights_list,
                transcript_chunks=final_transcript_chunks,
                actions=[],
                activity_date=None
            )
            if page_id:
                print(f"✓ Created Notion page for meeting: {title} (ID: {page_id})")
            else:
                print(f"✗ Failed to create Notion page for meeting: {title}")
        except Exception as e:
            print(f"✗ Exception creating Notion page for otid '{otid}': {e}")
    else:
        while True:
            # Add pagination param if available
            if modified_after is not None:
                params["modified_after"] = modified_after
            else:
                params.pop("modified_after", None)

            print(f"Fetching page {page}...")
            response = requests.get(url, params=params, cookies=cookies)
            response.raise_for_status()
            data = response.json()
            speeches = data.get("speeches", [])
            if page == 1:
                print("\n--- Full JSON response from first page ---")
                import json as _json
                print(_json.dumps(data, indent=2))
                print("--- End of JSON response ---\n")
            if not speeches:
                break
            all_meetings.extend(speeches)
            print(f"Fetched {len(speeches)} meetings on this page. Total so far: {len(all_meetings)}")

            # Pagination: update modified_after for next request
            modified_after = data.get("last_modified_at")
            if not modified_after or len(speeches) < params["page_size"]:
                break  # No more pages
            page += 1
            time.sleep(0.5)  # Be polite to the server

        print(f"\nTotal meetings found: {len(all_meetings)}")

        # Limit to only the first meeting for verification
        if all_meetings:
            print(f"[INFO] Limiting to first meeting: {all_meetings[0].get('title', 'Untitled Meeting')}")
            all_meetings = [all_meetings[0]]

        # Print the full JSON for the first meeting to inspect available fields
        if all_meetings:
            print("\n--- Full JSON for first meeting ---")
            import json as _json
            print(_json.dumps(all_meetings[0], indent=2))
            print("--- End of JSON for first meeting ---\n")

        for idx, meeting in enumerate(all_meetings):
            title = meeting.get('title', 'Untitled Meeting')
            summary = meeting.get('summary', '')
            otid = meeting.get('speech_id') or meeting.get('otid')
            transcript_blocks = []
            # Fetch full transcript from /forward/api/v1/speech?userid=...&otid=...
            if otid and user_id:
                transcript_url = f"https://otter.ai/forward/api/v1/speech?userid={user_id}&otid={otid}"
                if idx == 0:
                    print(f"[DEBUG] Fetching transcript from: {transcript_url}")
                try:
                    resp = requests.get(transcript_url, cookies=cookies)
                    resp.raise_for_status()
                    speech_json = resp.json()
                    if idx == 0:
                        import json as _json
                        print("[DEBUG] Full /speech JSON response:")
                        print(_json.dumps(speech_json, indent=2))
                    # Try to extract transcript from a list of objects (not segments)
                    transcript_blocks = []
                    # Map speaker_id to speaker_name
                    speakers = {}
                    if 'speakers' in speech_json:
                        for s in speech_json['speakers']:
                            if 'id' in s:
                                speakers[s['id']] = s.get('speaker_name', '')
                    # The transcript may be a list at the root or under a key
                    transcript_items = None
                    if isinstance(speech_json, list):
                        transcript_items = speech_json
                    elif 'results' in speech_json and isinstance(speech_json['results'], list):
                        transcript_items = speech_json['results']
                    elif 'paragraphs' in speech_json and isinstance(speech_json['paragraphs'], list):
                        transcript_items = speech_json['paragraphs']
                    elif 'speech' in speech_json and isinstance(speech_json['speech'], list):
                        transcript_items = speech_json['speech']
                    elif 'speech' in speech_json and isinstance(speech_json['speech'], dict) and 'segments' in speech_json['speech']:
                        transcript_items = speech_json['speech']['segments']
                    elif 'speech' in speech_json and isinstance(speech_json['speech'], dict) and 'transcript' in speech_json['speech'] and isinstance(speech_json['speech']['transcript'], list):
                        transcript_items = speech_json['speech']['transcript']
                    # Try to find a list of transcript objects with 'transcript' key
                    if not transcript_items:
                        # Try to find a list at the root with 'transcript' key
                        for v in speech_json.values():
                            if isinstance(v, list) and v and isinstance(v[0], dict) and 'transcript' in v[0]:
                                transcript_items = v
                                break
                    if transcript_items:
                        for item in transcript_items:
                            text = item.get('transcript', '').strip()
                            speaker_id = item.get('speaker_id')
                            speaker = speakers.get(speaker_id, '')
                            timestamp = format_timestamp(item.get('start_offset'))
                            if text:
                                line = f"{speaker} {timestamp}: {text}" if speaker or timestamp else text
                                transcript_blocks.append(line)
                        if idx == 0:
                            print(f"[DEBUG] Transcript items found: {len(transcript_items)}")
                            print(f"[DEBUG] First 3 transcript blocks:")
                            for b in transcript_blocks[:3]:
                                print(f"    {b}")
                    else:
                        print(f"[WARNING] No transcript items found in /speech response for meeting '{title}'. Falling back to outline or summary.")
                        speech_outline = meeting.get('speech_outline', [])
                        if speech_outline:
                            full_transcript = get_full_transcript_from_outline(speech_outline)
                            transcript_blocks = chunk_text(full_transcript)
                        else:
                            print(f"[WARNING] No speech_outline found. Falling back to summary.")
                except Exception as e:
                    print(f"Could not fetch full transcript for meeting '{title}': {e}")
            # Fallback: use summary if nothing else
            if not transcript_blocks and summary:
                print(f"[WARNING] Using summary as transcript for meeting '{title}'.")
                transcript_blocks = chunk_text(summary)
            meeting_date = meeting.get('start_time')
            if meeting_date:
                try:
                    # Convert UNIX timestamp to ISO format
                    meeting_date = datetime.fromtimestamp(meeting_date).isoformat()
                except Exception:
                    meeting_date = str(meeting_date)
            else:
                meeting_date = datetime.now().isoformat()

            # Extract action items from transcript or summary
            action_items = action_detector.detect_actions('\n'.join(transcript_blocks) or summary)

            # Use transcript_blocks for insights as well
            final_insights_list = transcript_blocks
            final_transcript_chunks = transcript_blocks

            # Print what will be sent to Notion as transcript (first 3 blocks)
            if idx == 0:
                print(f"[DEBUG] First 3 transcript blocks to Notion:")
                for b in final_transcript_chunks[:3]:
                    print(f"    {b}")

            # Create Notion page for the meeting
            try:
                page_id = notion.create_meeting_page(
                    database_id=notion_activities_db,
                    title=title,
                    summary=summary,
                    insights=final_insights_list,
                    transcript_chunks=final_transcript_chunks,
                    actions=action_items,
                    activity_date=meeting_date
                )
                if page_id:
                    print(f"✓ Created Notion page for meeting: {title} (ID: {page_id})")
                else:
                    print(f"✗ Failed to create Notion page for meeting: {title}")
            except Exception as e:
                print(f"✗ Exception creating Notion page for meeting '{title}': {e}")
                continue

            # Create Notion tasks for each action item
            for action in action_items:
                try:
                    task_id = notion.create_task(
                        database_id=notion_tasks_db,
                        meeting_name=title,
                        meeting_datetime=meeting_date,
                        action_name=action.get('text', ''),
                        owner=action.get('owner', 'Brian'),
                        due_date=action.get('due_date'),
                        status='Not Started'
                    )
                    if task_id:
                        print(f"  ✓ Created Notion task for action: {action.get('text', '')} (ID: {task_id})")
                    else:
                        print(f"  ✗ Failed to create Notion task for action: {action.get('text', '')}")
                except Exception as e:
                    print(f"  ✗ Exception creating Notion task for action '{action.get('text', '')}': {e}")

if __name__ == "__main__":
    main() 