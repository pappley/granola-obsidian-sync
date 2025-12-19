"""
Granola API client with smart data management and validation

Handles all interactions with the Granola API including documents,
transcripts, and document lists with intelligent caching and error handling.
"""

import json
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

from .config import GranolaConfig


class GranolaAPIError(Exception):
    """Custom exception for Granola API errors"""
    pass


class GranolaAPI:
    """Client for interacting with the Granola API"""
    
    def __init__(self, config: GranolaConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._access_token: Optional[str] = None
        
    def _load_credentials(self) -> str:
        """Load Granola API credentials from supabase.json"""
        try:
            with open(self.config.paths.credentials, 'r') as f:
                creds = json.load(f)
            
            # Try WorkOS token first, then Cognito
            workos_tokens = json.loads(creds.get('workos_tokens', '{}'))
            if 'access_token' in workos_tokens:
                return workos_tokens['access_token']
            
            # Fallback to Cognito tokens
            cognito_tokens = json.loads(creds['cognito_tokens'])
            return cognito_tokens['access_token']
            
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            raise GranolaAPIError(f"Failed to load credentials: {e}")
    
    @property
    def access_token(self) -> str:
        """Get access token, loading if necessary"""
        if self._access_token is None:
            self._access_token = self._load_credentials()
        return self._access_token
    
    def _make_request(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make authenticated request to Granola API with retry logic"""
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        for attempt in range(self.config.api.max_retries):
            try:
                response = requests.post(
                    url, 
                    json=payload, 
                    headers=headers,
                    timeout=self.config.api.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if self._validate_api_response(data):
                        return data
                    else:
                        self.logger.warning(f"Invalid API response structure: {url}")
                        
                elif response.status_code == 401:
                    # Token might be expired, reload and retry once
                    if attempt == 0:
                        self._access_token = None  # Force reload
                        continue
                    else:
                        raise GranolaAPIError(f"Authentication failed: {response.status_code}")
                        
                else:
                    self.logger.warning(f"API request failed: {response.status_code} - {response.text}")
                    
                # Wait before retry with exponential backoff
                if attempt < self.config.api.max_retries - 1:
                    wait_time = min(
                        self.config.error_handling['retry_base_delay'] * (2 ** attempt),
                        self.config.error_handling['retry_max_delay']
                    )
                    time.sleep(wait_time)
                    
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request exception on attempt {attempt + 1}: {e}")
                if attempt < self.config.api.max_retries - 1:
                    time.sleep(self.config.error_handling['retry_base_delay'])
        
        raise GranolaAPIError(f"Failed to get valid response from {url} after {self.config.api.max_retries} attempts")
    
    def _validate_api_response(self, data: Dict[str, Any]) -> bool:
        """Validate API response structure"""
        if not self.config.data['validate_api_responses']:
            return True
            
        # Basic validation - ensure response is a dict or list (transcripts can be lists)
        return isinstance(data, (dict, list))
    
    def fetch_documents_since(self, since_date: datetime) -> List[Dict[str, Any]]:
        """Fetch documents created or updated since the given date"""
        url = self.config.get_api_url('documents')
        all_documents = []
        offset = 0
        
        self.logger.info(f"Fetching documents since {since_date.strftime('%Y-%m-%d %H:%M')}...")
        
        while True:
            payload = {
                'limit': self.config.api.batch_size,
                'offset': offset
            }
            
            try:
                data = self._make_request(url, payload)
                documents = data.get('docs', data.get('documents', []))
                
                if not documents:
                    break
                
                # Filter documents by date
                recent_documents = []
                for doc in documents:
                    if self._is_document_recent(doc, since_date):
                        recent_documents.append(doc)
                    elif self._get_document_date(doc, 'created_at') < since_date:
                        # If we're seeing documents older than our cutoff, we can stop
                        break
                
                all_documents.extend(recent_documents)
                offset += self.config.api.batch_size
                
                # If we didn't find any recent documents in this batch, we can stop
                if not recent_documents:
                    break
                
                time.sleep(self.config.api.request_delay)
                
            except GranolaAPIError as e:
                if self.config.should_continue_on_error('document'):
                    self.logger.error(f"Error fetching documents batch at offset {offset}: {e}")
                    break
                else:
                    raise
        
        self.logger.info(f"Found {len(all_documents)} documents to sync")
        return all_documents
    
    def _is_document_recent(self, doc: Dict[str, Any], since_date: datetime) -> bool:
        """Check if document was created or updated since the given date"""
        try:
            created_dt = self._get_document_date(doc, 'created_at')
            updated_dt = self._get_document_date(doc, 'updated_at') or created_dt
            
            return created_dt >= since_date or updated_dt >= since_date
        except:
            # If we can't parse the date, include it to be safe
            return True
    
    def _get_document_date(self, doc: Dict[str, Any], field: str) -> Optional[datetime]:
        """Extract and parse date field from document"""
        date_str = doc.get(field, '')
        if not date_str:
            return None
            
        try:
            # Handle ISO format with Z timezone
            if date_str.endswith('Z'):
                date_str = date_str.replace('Z', '+00:00')
            return datetime.fromisoformat(date_str)
        except ValueError:
            return None
    
    def fetch_transcript(self, document_id: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch transcript content for a specific document"""
        url = self.config.get_api_url('transcript')
        payload = {'document_id': document_id}
        
        try:
            data = self._make_request(url, payload)
            
            # Return the transcript data - could be a list or nested structure
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'transcript' in data:
                return data['transcript']
            else:
                return data
                
        except GranolaAPIError as e:
            if self.config.should_continue_on_error('transcript'):
                self.logger.warning(f"Could not fetch transcript for document {document_id}: {e}")
                return None
            else:
                raise
    
    def fetch_document_lists(self) -> List[Dict[str, Any]]:
        """Fetch all document lists for mapping generation"""
        url = self.config.get_api_url('document_lists')
        
        try:
            data = self._make_request(url, {})
            document_lists = data.get('document_lists', [])
            
            self.logger.info(f"Fetched {len(document_lists)} document lists")
            return document_lists
            
        except GranolaAPIError as e:
            if self.config.should_continue_on_error('mapping'):
                self.logger.error(f"Failed to fetch document lists: {e}")
                return []
            else:
                raise
    
    def load_participant_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load participant data from user preferences"""
        try:
            with open(self.config.paths.user_preferences, 'r') as f:
                data = json.load(f)
            
            # Parse the JSON string inside the preferences
            prefs = json.loads(data['preferences'])
            participants = prefs['state'].get('suggestedParticipants', {})
            
            self.logger.info(f"Loaded participant data for {len(participants)} document lists")
            return participants
            
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Could not load participant data: {e}")
            return {}
    
    def get_last_sync_time(self) -> datetime:
        """Get the timestamp of the last sync from tracking file"""
        sync_file = self.config.paths.last_sync_file
        
        if sync_file.exists():
            try:
                with open(sync_file, 'r') as f:
                    timestamp = f.read().strip()
                return datetime.fromisoformat(timestamp)
            except (ValueError, IOError):
                pass
        
        # Default to configured lookback if no sync file exists
        return datetime.now() - timedelta(days=self.config.sync['default_lookback_days'])
    
    def update_last_sync_time(self):
        """Update the last sync timestamp"""
        sync_file = self.config.paths.last_sync_file
        
        with open(sync_file, 'w') as f:
            f.write(datetime.now().isoformat())