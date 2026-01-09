import requests
import logging
from ratelimit import limits, sleep_and_retry
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
import re
import json

class NotionAPI:
    def __init__(self, api_key):
        """Initialize the Notion API client."""
        self.api_key = api_key
        self.base_url = 'https://api.notion.com/v1/'
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'  # Updated to newer version
        }
        logging.info("Initialized Notion API client")

    @sleep_and_retry
    @limits(calls=3, period=1)
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def create_meeting_page(self, database_id, title, summary, insights, transcript_chunks, actions, activity_date=None):
        """Create a new meeting page in the Notion database with enhanced formatting."""
        try:
            # Clean and prepare content
            title = self._clean_text(title)
            summary = self._clean_text(summary) or "No summary available"
            insights = self._clean_text(insights) or "No insights available"
            MAX_BLOCK_SIZE = 2000
            
            # Helper to chunk text
            def _chunk_text(text, max_size=MAX_BLOCK_SIZE):
                if not isinstance(text, str):
                    text = str(text)
                return [text[i:i+max_size] for i in range(0, len(text), max_size)] if text else []

            # Create the meeting page content with properties that match the Activities database schema
            data = {
                'parent': {'database_id': database_id},
                'properties': {
                    'Name': {'title': [{'text': {'content': title}}]},
                    'Activity Date': {'date': {'start': activity_date or datetime.now().isoformat()}},
                    'Activity': {'multi_select': [{'name': 'Meeting'}]}
                },
                'children': [
                    # Summary section
                    self._create_heading_block('Meeting Summary', level=1),
                    self._create_paragraph_block(summary),
                    self._create_divider_block(),
                    
                    # Action Items section with callout for visibility
                    self._create_heading_block('Action Items', level=1),
                    self._create_callout_block('Tasks identified from this meeting:', '📋'),
                ]
            }
            
            # Add action items with checkboxes and formatting
            if actions:
                for action in actions:
                    owner = action.get('owner', 'Brian')
                    action_text = action.get('text', '').strip()
                    due_date = action.get('due_date')
                    
                    due_date_text = ''
                    if due_date:
                        if isinstance(due_date, datetime):
                            due_date_text = f" (Due: {due_date.strftime('%Y-%m-%d')})"
                        else:
                            due_date_text = f" (Due: {due_date})"
                    
                    # Create a to-do item for each action
                    for chunk in _chunk_text(f"{action_text} - Assigned to: {owner}{due_date_text}"):
                        data['children'].append(self._create_to_do_block(chunk))
            else:
                data['children'].append(
                    self._create_paragraph_block("No action items were identified for this meeting.")
                )
            
            # Add insights section (each as a separate block)
            data['children'].extend([
                self._create_divider_block(),
                self._create_heading_block('Insights', level=1),
            ])
            # Ensure insights is a list
            if isinstance(insights, str):
                insights_list = [i.strip() for i in insights.split('\n') if i.strip()]
                if len(insights_list) == 1 and '.' in insights_list[0]:
                    # If it's a long paragraph, split by period+space for fallback
                    insights_list = [i.strip() for i in insights_list[0].split('. ') if i.strip()]
            elif isinstance(insights, list):
                insights_list = [str(i).strip() for i in insights if str(i).strip()]
            else:
                insights_list = []
            if insights_list:
                for insight in insights_list:
                    for chunk in _chunk_text(self._clean_text(insight)):
                        data['children'].append(self._create_paragraph_block(chunk))
            else:
                data['children'].append(self._create_paragraph_block("No insights available"))
            data['children'].append(self._create_divider_block())
            
            # Add full transcript with toggle to hide it by default
            transcript_toggle = {
                'object': 'block',
                'type': 'toggle',
                'toggle': {
                    'rich_text': [{'type': 'text', 'text': {'content': 'Full Transcript (Click to expand)'}}],
                    'children': []
                }
            }
            
            # Add transcript chunks to the toggle, chunking each to <=2000 chars
            for chunk in transcript_chunks:
                for subchunk in _chunk_text(self._clean_text(chunk)):
                    transcript_toggle['toggle']['children'].append(
                        self._create_paragraph_block(subchunk)
                    )
            
            # Add the transcript toggle to the page
            data['children'].append(transcript_toggle)
            
            # Make the API request
            response = requests.post(f'{self.base_url}pages', headers=self.headers, json=data)
            response.raise_for_status()
            
            page_id = response.json().get('id')
            logging.info(f"Successfully created Notion page with ID: {page_id}")
            return page_id
            
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error occurred when creating Notion page: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response content: {e.response.text}")
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Connection error occurred: {e}")
        except requests.exceptions.Timeout as e:
            logging.error(f"Timeout error occurred: {e}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Request error occurred: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred when creating Notion page: {e}")
        
        return None

    @sleep_and_retry
    @limits(calls=3, period=1)
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def create_task(self, database_id, meeting_name, meeting_datetime, action_name, owner, due_date, status):
        """Create a new task in the Notion database."""
        try:
            # Clean and prepare content
            meeting_name = self._clean_text(meeting_name)
            action_name = self._clean_text(action_name)
            owner = self._clean_text(owner)
            
            # Include the identified owner in the task name if available
            if owner and owner.lower() != "brian":
                full_action_name = f"{action_name} (Originally assigned to: {owner})"
            else:
                full_action_name = action_name
            
            # Ensure due_date is a datetime object
            if due_date and not isinstance(due_date, datetime):
                try:
                    if isinstance(due_date, str):
                        # Try to parse the string to a datetime
                        due_date = datetime.strptime(due_date, '%Y-%m-%d')
                    else:
                        # Default to one week from now
                        due_date = datetime.now() + timedelta(days=7)
                except ValueError:
                    due_date = datetime.now() + timedelta(days=7)
            
            # If no due date is provided, set a default (one week from now)
            if not due_date:
                due_date = datetime.now() + timedelta(days=7)
                
            # Prepare the task data with properties that match the Tasks database schema
            # Make the current user the action owner for all tasks
            data = {
                'parent': {'database_id': database_id},
                'properties': {
                    'Meeting Name': {'title': [{'text': {'content': full_action_name}}]},
                    'Meeting Date & Time': {'date': {'start': meeting_datetime.isoformat() if isinstance(meeting_datetime, datetime) else meeting_datetime}},
                    'Action Due Date': {'date': {'start': due_date.isoformat()}}
                }
            }
            
            # The Action Owner field is a people type, but we'll leave it empty for now
            # The current user will be assigned by default in many Notion setups
            
            # Create the task
            response = requests.post(f'{self.base_url}pages', headers=self.headers, json=data)
            response.raise_for_status()
            
            task_id = response.json().get('id')
            logging.info(f"Successfully created Notion task with ID: {task_id}")
            return task_id
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to create task: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response content: {e.response.text}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred when creating task: {e}")
            return None
            
    def _clean_text(self, text):
        """Clean and normalize text for Notion."""
        if not text:
            return ""
            
        # Convert to string if it's not already
        if not isinstance(text, str):
            text = str(text)
            
        # Replace special characters that might cause issues in Notion
        text = text.replace('\x00', '')  # Remove null bytes
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
        
    def _create_heading_block(self, text, level=1):
        """Create a heading block of specified level."""
        return {
            'object': 'block',
            'type': f'heading_{level}',
            f'heading_{level}': {
                'rich_text': [{'type': 'text', 'text': {'content': text}}]
            }
        }
        
    def _create_paragraph_block(self, text):
        """Create a paragraph block."""
        return {
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'rich_text': [{'type': 'text', 'text': {'content': text}}]
            }
        }
        
    def _create_bulleted_list_item_block(self, text):
        """Create a bulleted list item block."""
        return {
            'object': 'block',
            'type': 'bulleted_list_item',
            'bulleted_list_item': {
                'rich_text': [{'type': 'text', 'text': {'content': text}}]
            }
        }
        
    def _create_to_do_block(self, text, checked=False):
        """Create a to-do item block."""
        return {
            'object': 'block',
            'type': 'to_do',
            'to_do': {
                'rich_text': [{'type': 'text', 'text': {'content': text}}],
                'checked': checked
            }
        }
        
    def _create_divider_block(self):
        """Create a divider block."""
        return {
            'object': 'block',
            'type': 'divider',
            'divider': {}
        }
        
    def _create_callout_block(self, text, emoji='💡'):
        """Create a callout block with an emoji."""
        return {
            'object': 'block',
            'type': 'callout',
            'callout': {
                'rich_text': [{'type': 'text', 'text': {'content': text}}],
                'icon': {'type': 'emoji', 'emoji': emoji}
            }
        } 