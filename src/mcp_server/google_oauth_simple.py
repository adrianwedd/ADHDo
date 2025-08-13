"""
Simplified Google OAuth flow that handles scope reordering issues
"""
import os
import json
import pickle
import logging
from typing import Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from fastapi import HTTPException
import requests

logger = logging.getLogger(__name__)

class SimpleGoogleOAuth:
    """Simplified OAuth manager that handles scope reordering."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/tasks', 
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/fitness.activity.read',
        'https://www.googleapis.com/auth/fitness.sleep.read',
        'https://www.googleapis.com/auth/fitness.body.read',
        'https://www.googleapis.com/auth/fitness.location.read'
    ]
    
    def __init__(self, credentials_file="credentials.json", token_file="token.pickle"):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.creds = None
        self._load_token()
    
    def _load_token(self):
        """Load saved token if it exists."""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    self.creds = pickle.load(token)
                logger.info("✅ Loaded saved Google credentials")
            except Exception as e:
                logger.error(f"Failed to load token: {e}")
    
    def _save_token(self):
        """Save credentials for future use."""
        try:
            with open(self.token_file, 'wb') as token:
                pickle.dump(self.creds, token)
            logger.info("💾 Saved Google credentials")
        except Exception as e:
            logger.error(f"Failed to save token: {e}")
    
    def is_authenticated(self) -> bool:
        """Check if we have valid credentials."""
        return self.creds is not None and self.creds.valid
    
    def get_auth_url(self, redirect_uri: str) -> str:
        """Get the authorization URL."""
        flow = Flow.from_client_secrets_file(
            self.credentials_file,
            scopes=self.SCOPES,
            redirect_uri=redirect_uri
        )
        
        auth_url, _ = flow.authorization_url(
            prompt='consent',
            access_type='offline'
        )
        
        logger.info(f"🔐 Generated auth URL: {auth_url}")
        return auth_url
    
    async def exchange_code(self, code: str, redirect_uri: str) -> bool:
        """
        Exchange authorization code for credentials.
        This version manually handles the token exchange to avoid scope validation issues.
        """
        try:
            # Load client secrets
            with open(self.credentials_file, 'r') as f:
                client_config = json.load(f)['web']
            
            # Manually exchange the code for tokens
            token_response = requests.post(
                client_config['token_uri'],
                data={
                    'code': code,
                    'client_id': client_config['client_id'],
                    'client_secret': client_config['client_secret'],
                    'redirect_uri': redirect_uri,
                    'grant_type': 'authorization_code'
                }
            )
            
            if token_response.status_code != 200:
                logger.error(f"Token exchange failed: {token_response.text}")
                return False
            
            token_data = token_response.json()
            
            # Create credentials from the token
            self.creds = Credentials(
                token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token'),
                token_uri=client_config['token_uri'],
                client_id=client_config['client_id'],
                client_secret=client_config['client_secret'],
                scopes=token_data.get('scope', '').split() or self.SCOPES
            )
            
            self._save_token()
            logger.info("✅ Google authentication successful!")
            return True
            
        except Exception as e:
            logger.error(f"OAuth exchange failed: {e}")
            return False
    
    def get_calendar_service(self):
        """Get authenticated Calendar service."""
        if not self.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated")
        return build('calendar', 'v3', credentials=self.creds)
    
    def get_fitness_service(self):
        """Get authenticated Fitness service."""
        if not self.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated")
        return build('fitness', 'v1', credentials=self.creds)
    
    async def get_fitness_data(self, data_type="steps", days=7):
        """Get fitness data from Google Fit."""
        try:
            service = self.get_fitness_service()
            
            from datetime import datetime, timedelta
            import time
            
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            # Convert to milliseconds
            start_millis = int(start_time.timestamp() * 1000)
            end_millis = int(end_time.timestamp() * 1000)
            
            # Define data sources based on type
            data_sources = {
                "steps": "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps",
                "calories": "derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended",
                "distance": "derived:com.google.distance.delta:com.google.android.gms:merge_distance_delta",
                "heart": "derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm",
                "sleep": "derived:com.google.sleep.segment:com.google.android.gms:merged",
                "activity": "derived:com.google.activity.segment:com.google.android.gms:merge_activity_segments"
            }
            
            data_source = data_sources.get(data_type, data_sources["steps"])
            
            # Request fitness data
            dataset_id = f"{start_millis}000000-{end_millis}000000"
            
            result = service.users().dataSources().datasets().get(
                userId='me',
                dataSourceId=data_source,
                datasetId=dataset_id
            ).execute()
            
            # Process the data points
            points = result.get('point', [])
            data = []
            
            for point in points:
                value = point.get('value', [{}])[0]
                
                # Extract the appropriate value based on data type
                if data_type == "steps":
                    val = value.get('intVal', 0)
                elif data_type in ["calories", "distance"]:
                    val = value.get('fpVal', 0.0)
                elif data_type == "activity":
                    val = value.get('intVal', 0)  # Activity type ID
                else:
                    val = value.get('intVal', value.get('fpVal', 0))
                
                # Convert timestamps
                start_time = int(point.get('startTimeNanos', 0)) / 1e9
                end_time = int(point.get('endTimeNanos', 0)) / 1e9
                
                data.append({
                    'value': val,
                    'start': datetime.fromtimestamp(start_time).isoformat(),
                    'end': datetime.fromtimestamp(end_time).isoformat()
                })
            
            logger.info(f"💪 Retrieved {len(data)} {data_type} data points")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get fitness data: {e}")
            return []
    
    async def get_today_stats(self):
        """Get today's fitness summary."""
        try:
            service = self.get_fitness_service()
            
            from datetime import datetime, timedelta
            import time
            
            # Get today's data
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            
            start_millis = int(today.timestamp() * 1000)
            end_millis = int(tomorrow.timestamp() * 1000)
            
            # Get aggregate data
            body = {
                "aggregateBy": [
                    {"dataTypeName": "com.google.step_count.delta"},
                    {"dataTypeName": "com.google.calories.expended"},
                    {"dataTypeName": "com.google.distance.delta"}
                ],
                "bucketByTime": {"durationMillis": 86400000},  # 1 day
                "startTimeMillis": start_millis,
                "endTimeMillis": end_millis
            }
            
            result = service.users().dataset().aggregate(userId='me', body=body).execute()
            
            stats = {
                'date': today.isoformat(),
                'steps': 0,
                'calories': 0,
                'distance': 0
            }
            
            # Extract aggregated values
            for bucket in result.get('bucket', []):
                for dataset in bucket.get('dataset', []):
                    if dataset.get('dataSourceId', '').endswith('step_count.delta'):
                        for point in dataset.get('point', []):
                            stats['steps'] += point.get('value', [{}])[0].get('intVal', 0)
                    elif dataset.get('dataSourceId', '').endswith('calories.expended'):
                        for point in dataset.get('point', []):
                            stats['calories'] += point.get('value', [{}])[0].get('fpVal', 0)
                    elif dataset.get('dataSourceId', '').endswith('distance.delta'):
                        for point in dataset.get('point', []):
                            stats['distance'] += point.get('value', [{}])[0].get('fpVal', 0)
            
            # Round values
            stats['calories'] = round(stats['calories'], 1)
            stats['distance'] = round(stats['distance'] / 1000, 2)  # Convert to km
            
            logger.info(f"📊 Today's stats: {stats['steps']} steps, {stats['calories']} cal, {stats['distance']} km")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get today's stats: {e}")
            return {'error': str(e)}
    
    async def get_calendar_events(self, max_results=10):
        """Get upcoming calendar events."""
        try:
            service = self.get_calendar_service()
            
            from datetime import datetime, timedelta
            now = datetime.utcnow().isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            logger.info(f"📅 Retrieved {len(events)} calendar events")
            return events
            
        except Exception as e:
            logger.error(f"Failed to get calendar events: {e}")
            return []

# Global instance
simple_oauth_manager: Optional[SimpleGoogleOAuth] = None

def initialize_simple_oauth():
    """Initialize the simple OAuth manager."""
    global simple_oauth_manager
    simple_oauth_manager = SimpleGoogleOAuth()
    return simple_oauth_manager