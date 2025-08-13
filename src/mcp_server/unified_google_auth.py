"""
Unified Google Authentication for ADHD Support System
Combines OAuth, Calendar, and Fitness APIs in one clean implementation
"""
import os
import json
import pickle
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from fastapi import HTTPException
import requests

logger = logging.getLogger(__name__)

# Try to import Google libraries
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger.warning("Google libraries not installed")

class UnifiedGoogleAuth:
    """Unified manager for all Google services."""
    
    # All scopes we need
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
        self._services = {}  # Cache for Google services
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
        if not GOOGLE_AVAILABLE:
            raise HTTPException(status_code=500, detail="Google libraries not installed")
            
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
        Uses manual token exchange to avoid scope validation issues.
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
            self._services.clear()  # Clear service cache to rebuild with new creds
            logger.info("✅ Google authentication successful!")
            return True
            
        except Exception as e:
            logger.error(f"OAuth exchange failed: {e}")
            return False
    
    def _get_service(self, service_name: str, version: str):
        """Get or create a Google service instance."""
        if not self.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        cache_key = f"{service_name}_{version}"
        if cache_key not in self._services:
            self._services[cache_key] = build(service_name, version, credentials=self.creds)
        
        return self._services[cache_key]
    
    # === CALENDAR METHODS ===
    
    async def get_calendar_events(self, max_results=10, hours_ahead=24):
        """Get upcoming calendar events."""
        try:
            service = self._get_service('calendar', 'v3')
            
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(hours=hours_ahead)).isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Process events for ADHD context
            processed_events = []
            for event in events:
                processed = self._process_event_for_adhd(event)
                processed_events.append(processed)
            
            logger.info(f"📅 Retrieved {len(processed_events)} calendar events")
            return processed_events
            
        except Exception as e:
            logger.error(f"Failed to get calendar events: {e}")
            return []
    
    def _process_event_for_adhd(self, event: Dict) -> Dict:
        """Process calendar event with ADHD-relevant information."""
        summary = event.get('summary', 'Untitled Event')
        start = event.get('start', {})
        
        # Parse time
        if 'dateTime' in start:
            start_time = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
        else:
            start_time = datetime.fromisoformat(start.get('date', ''))
        
        # Calculate time until event
        now = datetime.now().replace(tzinfo=start_time.tzinfo)
        time_until = start_time - now
        
        # Determine urgency
        if time_until.total_seconds() < 0:
            urgency = "happening_now"
        elif time_until.total_seconds() < 900:  # 15 minutes
            urgency = "imminent"
        elif time_until.total_seconds() < 3600:  # 1 hour
            urgency = "soon"
        else:
            urgency = "future"
        
        return {
            "id": event.get('id'),
            "summary": summary,
            "start_time": start_time.isoformat(),
            "location": event.get('location', ''),
            "description": event.get('description', ''),
            "urgency": urgency,
            "time_until_minutes": int(time_until.total_seconds() / 60),
            "raw_event": event  # Include raw event for debugging
        }
    
    async def create_focus_event(self, duration_minutes: int = 25) -> Dict:
        """Create a focus time event in calendar."""
        try:
            service = self._get_service('calendar', 'v3')
            
            start_time = datetime.utcnow()
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            event = {
                'summary': '🎯 ADHD Focus Time',
                'description': 'Deep focus session - notifications muted',
                'start': {
                    'dateTime': start_time.isoformat() + 'Z',
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.isoformat() + 'Z',
                    'timeZone': 'UTC',
                },
                'colorId': '9',  # Blue color
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 0},
                    ],
                },
            }
            
            created_event = service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            logger.info(f"✅ Created focus event: {created_event.get('htmlLink')}")
            return created_event
            
        except Exception as e:
            logger.error(f"Failed to create focus event: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # === FITNESS METHODS ===
    
    async def get_fitness_data(self, data_type="steps", days=7):
        """Get fitness data from Google Fit."""
        try:
            service = self._get_service('fitness', 'v1')
            
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
            service = self._get_service('fitness', 'v1')
            
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
    
    # === TASK METHODS ===
    
    async def add_task(self, title: str, notes: str = None, due: datetime = None) -> Dict:
        """Add a task to Google Tasks."""
        try:
            service = self._get_service('tasks', 'v1')
            
            task = {'title': title}
            
            if notes:
                task['notes'] = notes
            
            if due:
                task['due'] = due.isoformat() + 'Z'
            
            # Get default task list
            tasklists = service.tasklists().list(maxResults=1).execute()
            tasklist_id = tasklists['items'][0]['id'] if tasklists.get('items') else '@default'
            
            result = service.tasks().insert(
                tasklist=tasklist_id,
                body=task
            ).execute()
            
            logger.info(f"✅ Created task: {title}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # === CONTEXT METHODS ===
    
    async def get_adhd_context(self) -> Dict:
        """Get comprehensive context for ADHD support."""
        context = {
            "authenticated": self.is_authenticated(),
            "calendar": None,
            "fitness": None,
            "recommendations": []
        }
        
        if not self.is_authenticated():
            return context
        
        try:
            # Get calendar context
            events = await self.get_calendar_events(max_results=5, hours_ahead=4)
            if events:
                next_event = events[0]
                context["calendar"] = {
                    "next_event": next_event,
                    "upcoming_count": len(events),
                    "needs_preparation": next_event.get("urgency") in ["imminent", "soon"]
                }
                
                # Add recommendations based on calendar
                if next_event.get("urgency") == "imminent":
                    context["recommendations"].append(
                        f"⚠️ {next_event['summary']} starts in {next_event['time_until_minutes']} minutes!"
                    )
                elif next_event.get("urgency") == "soon":
                    context["recommendations"].append(
                        f"📅 Prepare for {next_event['summary']} in {next_event['time_until_minutes']} minutes"
                    )
            
            # Get fitness context
            today_stats = await self.get_today_stats()
            if not today_stats.get('error'):
                context["fitness"] = today_stats
                
                # Add fitness recommendations
                if today_stats['steps'] < 3000:
                    context["recommendations"].append("🚶 Consider taking a walk - movement helps ADHD focus!")
                elif today_stats['steps'] > 8000:
                    context["recommendations"].append("💪 Great activity today! Remember to rest too.")
            
        except Exception as e:
            logger.error(f"Failed to get ADHD context: {e}")
        
        return context

# Global instance
unified_auth: Optional[UnifiedGoogleAuth] = None

def initialize_unified_auth():
    """Initialize the unified auth manager."""
    global unified_auth
    unified_auth = UnifiedGoogleAuth()
    return unified_auth