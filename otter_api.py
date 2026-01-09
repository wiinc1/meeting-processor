import logging
import requests
from datetime import datetime
from dateutil import parser
from tenacity import retry, stop_after_attempt, wait_exponential
import otterai
import json

class OtterAPI:
    def __init__(self, username=None, password=None, api_key=None):
        """Initialize the Otter.ai API client.
        
        Can use either username/password or API key authentication.
        """
        self.username = username
        self.password = password
        self.api_key = api_key
        self.session_token = None
        
        # Try to use the API key if provided
        if api_key and api_key != 'test_key':
            try:
                # Try to use the official otterai client first
                self.client = otterai.Api(api_key)
                self.use_client = True
                logging.info("Successfully initialized otterai client with API key")
                return
            except Exception as e:
                # Fall back to direct API calls if client doesn't work
                logging.warning(f"Could not initialize otterai client with API key: {e}. Falling back to direct API calls.")
                self.use_client = False
                self.base_url = 'https://otter.ai/forward/api/'
                self.headers = {'Authorization': f'Bearer {self.api_key}'}
                return
        
        # Use username/password if API key isn't provided or is a placeholder
        if username and password:
            self.use_client = False
            self.base_url = 'https://otter.ai/forward/api/'
            # Authenticate with username/password to get session token
            self._authenticate()
        else:
            logging.error("Neither valid API key nor username/password provided")
            raise ValueError("You must provide either a valid API key or username/password for Otter.ai authentication")
    
    def _authenticate(self):
        """Authenticate with Otter.ai using username and password to get a session token."""
        try:
            logging.info(f"Attempting to authenticate with Otter.ai using username: {self.username}")
            # Based on the gmchad/otterai-api GitHub repo, Otter.ai uses a different authentication endpoint
            auth_url = 'https://otter.ai/forward/api/v1/login'
            auth_data = {
                'username': self.username,
                'password': self.password
            }
            
            # Log request details for debugging
            logging.debug(f"Auth URL: {auth_url}")
            logging.debug(f"Auth data: {json.dumps(auth_data)}")
            
            # Include required headers for the Otter.ai API
            headers = {
                'Content-Type': 'application/json',
                'Referer': 'https://otter.ai/',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
            }
            
            response = requests.post(auth_url, json=auth_data, headers=headers)
            
            # Log response details for debugging
            logging.debug(f"Auth response status: {response.status_code}")
            if response.content:
                try:
                    logging.debug(f"Auth response: {json.dumps(response.json(), indent=2)}")
                except:
                    logging.debug(f"Auth response (raw): {response.content}")
            
            response.raise_for_status()
            
            auth_response = response.json()
            self.session_token = auth_response.get('access_token')
            
            if not self.session_token:
                logging.error("Authentication failed: No token in response")
                raise ValueError("Authentication failed: No token in response")
                
            # Set up headers with session token
            self.headers = {
                'Authorization': f'Bearer {self.session_token}',
                'Referer': 'https://otter.ai/',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
            }
            logging.info("Successfully authenticated with Otter.ai using username/password")
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Authentication failed: {e}")
            if hasattr(e, 'response') and e.response:
                logging.error(f"Response: {e.response.text}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error during authentication: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_recent_meetings(self, limit=5):
        """Retrieve a list of recent meetings from Otter.ai."""
        try:
            if self.use_client:
                # Use the client library
                meetings_data = self.client.get_meetings(limit=limit)
                return self._process_meetings(meetings_data)
            else:
                # Direct API call
                response = requests.get(
                    f'{self.base_url}meetings', 
                    headers=self.headers, 
                    params={'limit': limit}
                )
                response.raise_for_status()
                return self._process_meetings(response.json().get('meetings', []))
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP error occurred: {e}")
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Connection error occurred: {e}")
        except requests.exceptions.Timeout as e:
            logging.error(f"Timeout error occurred: {e}")
        except requests.exceptions.RequestException as e:
            logging.error(f"An error occurred: {e}")
        except Exception as e:
            logging.error(f"Error retrieving meetings: {e}")
        return []
        
    def _process_meetings(self, meetings_data):
        """Process and standardize meeting data regardless of source."""
        processed_meetings = []
        for meeting in meetings_data:
            try:
                # Parse date and time from the meeting data
                meeting_time = parser.parse(meeting.get('created_at') or meeting.get('date_time', ''))
                
                processed_meetings.append({
                    'id': meeting.get('id', ''),
                    'title': meeting.get('title', 'Untitled Meeting'),
                    'date': meeting_time.strftime('%Y-%m-%d'),
                    'time': meeting_time.strftime('%H:%M'),
                    'datetime': meeting_time,
                    'duration': meeting.get('duration', 0),
                    'speaker_count': meeting.get('speaker_count', 0)
                })
            except Exception as e:
                logging.error(f"Error processing meeting data: {e}")
                
        return processed_meetings

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_transcript(self, meeting_id):
        """Retrieve the full transcript for a given meeting."""
        try:
            if self.use_client:
                # Use the client library
                transcript_data = self.client.get_transcript(meeting_id)
                return self._extract_transcript_text(transcript_data)
            else:
                # Direct API call
                response = requests.get(
                    f'{self.base_url}meetings/{meeting_id}/transcript', 
                    headers=self.headers
                )
                response.raise_for_status()
                return self._extract_transcript_text(response.json())
        except Exception as e:
            logging.error(f"Failed to retrieve transcript for meeting {meeting_id}: {e}")
            return ''
            
    def _extract_transcript_text(self, transcript_data):
        """Extract and format the transcript text from various response formats."""
        # Handle different response formats
        if isinstance(transcript_data, str):
            return transcript_data
            
        if isinstance(transcript_data, dict):
            # Try to get the transcript from different possible locations
            if 'transcript' in transcript_data:
                return transcript_data['transcript']
            if 'transcripts' in transcript_data:
                segments = transcript_data.get('transcripts', [])
                return '\n'.join([seg.get('text', '') for seg in segments])
                
        return ''

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_summary(self, meeting_id):
        """Retrieve the summary for a given meeting."""
        try:
            if self.use_client:
                # Use the client library
                summary_data = self.client.get_summary(meeting_id)
                return self._extract_summary_text(summary_data)
            else:
                # Direct API call
                response = requests.get(
                    f'{self.base_url}meetings/{meeting_id}/summary', 
                    headers=self.headers
                )
                response.raise_for_status()
                return self._extract_summary_text(response.json())
        except Exception as e:
            logging.error(f"Failed to retrieve summary for meeting {meeting_id}: {e}")
            return 'No summary available'
            
    def _extract_summary_text(self, summary_data):
        """Extract and format the summary text from various response formats."""
        if isinstance(summary_data, str):
            return summary_data
            
        if isinstance(summary_data, dict):
            # Try to get the summary from different possible locations
            if 'summary' in summary_data:
                return summary_data['summary']
                
        return 'No summary available'

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_insights(self, meeting_id):
        """Retrieve insights for a given meeting."""
        try:
            if self.use_client:
                # Use the client library if available
                insights_data = self.client.get_insights(meeting_id)
                return self._extract_insights_text(insights_data)
            else:
                # Direct API call
                response = requests.get(
                    f'{self.base_url}meetings/{meeting_id}/insights', 
                    headers=self.headers
                )
                response.raise_for_status()
                return self._extract_insights_text(response.json())
        except Exception as e:
            logging.error(f"Failed to retrieve insights for meeting {meeting_id}: {e}")
            return 'No insights available'
            
    def _extract_insights_text(self, insights_data):
        """Extract and format insights text from various response formats."""
        if isinstance(insights_data, str):
            return insights_data
            
        if isinstance(insights_data, dict):
            # Try to get insights from different possible locations
            if 'insights' in insights_data:
                return insights_data['insights']
                
        return 'No insights available'

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def get_action_items(self, meeting_id):
        """Retrieve action items for a given meeting."""
        try:
            if self.use_client:
                # Use the client library
                actions_data = self.client.get_action_items(meeting_id)
                return self._process_action_items(actions_data)
            else:
                # Direct API call
                response = requests.get(
                    f'{self.base_url}meetings/{meeting_id}/action_items', 
                    headers=self.headers
                )
                response.raise_for_status()
                return self._process_action_items(response.json())
        except Exception as e:
            logging.error(f"Failed to retrieve action items for meeting {meeting_id}: {e}")
            return []
            
    def _process_action_items(self, actions_data):
        """Process and standardize action items data regardless of source."""
        processed_actions = []
        
        # Handle different response formats
        if isinstance(actions_data, list):
            action_items = actions_data
        elif isinstance(actions_data, dict):
            action_items = actions_data.get('action_items', [])
        else:
            return []
            
        for action in action_items:
            if isinstance(action, str):
                processed_actions.append({
                    'text': action,
                    'owner': 'Brian',  # Default owner
                    'due_date': None   # No due date available
                })
            elif isinstance(action, dict):
                processed_actions.append({
                    'text': action.get('text', ''),
                    'owner': action.get('owner', 'Brian'),
                    'due_date': action.get('due_date')
                })
                
        return processed_actions 