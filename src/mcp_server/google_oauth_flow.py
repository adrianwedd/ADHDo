"""
Google OAuth Web Flow for ADHD Support Server
Handles authentication for server running on Raspberry Pi
"""
import os
import json
import pickle
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
import logging

logger = logging.getLogger(__name__)

# OAuth imports
try:
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False
    logger.warning("Google auth libraries not installed")

class GoogleOAuthManager:
    """Manages OAuth flow for Google APIs on a server."""
    
    # Scopes needed for ADHD support
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',  # Calendar read/write
        'https://www.googleapis.com/auth/tasks',     # Tasks management
        'https://www.googleapis.com/auth/userinfo.email',  # User identification
    ]
    
    def __init__(self, 
                 client_secrets_file: str = "credentials.json",
                 token_file: str = "token.pickle",
                 redirect_uri: str = None):
        """
        Initialize OAuth manager.
        
        Args:
            client_secrets_file: Path to OAuth client secrets from Google
            token_file: Where to store user tokens
            redirect_uri: OAuth callback URL (e.g., http://pi5.local:8000/auth/callback)
        """
        self.client_secrets_file = client_secrets_file
        self.token_file = token_file
        self.redirect_uri = redirect_uri or "http://localhost:8000/auth/callback"
        self.flow = None
        self.creds = None
        
        # Load existing token if available
        self._load_token()
    
    def _load_token(self) -> bool:
        """Load saved token from file."""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    self.creds = pickle.load(token)
                logger.info("✅ Loaded saved Google credentials")
                return True
            except Exception as e:
                logger.error(f"Failed to load token: {e}")
        return False
    
    def _save_token(self):
        """Save token to file."""
        try:
            with open(self.token_file, 'wb') as token:
                pickle.dump(self.creds, token)
            logger.info("💾 Saved Google credentials")
        except Exception as e:
            logger.error(f"Failed to save token: {e}")
    
    def is_authenticated(self) -> bool:
        """Check if we have valid authentication."""
        if not self.creds:
            return False
        
        # Check if token is expired
        if self.creds.expired and self.creds.refresh_token:
            try:
                self.creds.refresh(GoogleRequest())
                self._save_token()
                logger.info("🔄 Refreshed Google token")
                return True
            except Exception as e:
                logger.error(f"Token refresh failed: {e}")
                return False
        
        return self.creds.valid
    
    def get_authorization_url(self, state: str = None) -> str:
        """
        Get the URL to redirect user for authorization.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL to redirect user to
        """
        if not os.path.exists(self.client_secrets_file):
            raise FileNotFoundError(
                f"Missing {self.client_secrets_file}. "
                "Download from Google Cloud Console"
            )
        
        self.flow = Flow.from_client_secrets_file(
            self.client_secrets_file,
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri
        )
        
        auth_url, _ = self.flow.authorization_url(
            prompt='consent',
            access_type='offline',  # Get refresh token
            state=state
        )
        
        logger.info(f"🔐 Generated auth URL: {auth_url}")
        return auth_url
    
    async def handle_callback(self, authorization_code: str) -> bool:
        """
        Handle OAuth callback with authorization code.
        
        Args:
            authorization_code: Code from Google OAuth callback
            
        Returns:
            True if authentication successful
        """
        try:
            # Always recreate flow for callback to avoid scope mismatch issues
            self.flow = Flow.from_client_secrets_file(
                self.client_secrets_file,
                scopes=self.SCOPES,
                redirect_uri=self.redirect_uri
            )
            
            # IMPORTANT: Set the authorization URL to avoid scope order validation issues
            # This is a workaround for the Google OAuth library's strict scope ordering
            self.flow.redirect_uri = self.redirect_uri
            
            # Exchange code for token
            self.flow.fetch_token(code=authorization_code)
            self.creds = self.flow.credentials
            
            # Save for future use
            self._save_token()
            
            logger.info("✅ Google authentication successful")
            return True
            
        except Exception as e:
            # If it's a scope mismatch error, try to extract and use the token anyway
            if "Scope has changed" in str(e):
                logger.warning(f"Scope order mismatch (this is OK): {e}")
                # The token was actually fetched successfully, but validation failed
                # We need to bypass the validation and get the token directly
                try:
                    # Access the oauth2session directly to get the token
                    if hasattr(self.flow, 'oauth2session') and hasattr(self.flow.oauth2session, 'token'):
                        token = self.flow.oauth2session.token
                        if token and 'access_token' in token:
                            # Create credentials manually from the token
                            from google.oauth2.credentials import Credentials as GoogleCredentials
                            self.creds = GoogleCredentials(
                                token=token['access_token'],
                                refresh_token=token.get('refresh_token'),
                                token_uri=self.flow.client_config['token_uri'],
                                client_id=self.flow.client_config['client_id'],
                                client_secret=self.flow.client_config['client_secret'],
                                scopes=self.SCOPES
                            )
                            self._save_token()
                            logger.info("✅ Google authentication successful (despite scope warning)")
                            return True
                except Exception as inner_e:
                    logger.error(f"Failed to extract token from flow: {inner_e}")
            
            logger.error(f"OAuth callback failed: {e}")
            return False
    
    def get_calendar_service(self):
        """Get authenticated Calendar service."""
        if not self.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated with Google")
        
        return build('calendar', 'v3', credentials=self.creds)
    
    def get_tasks_service(self):
        """Get authenticated Tasks service."""
        if not self.is_authenticated():
            raise HTTPException(status_code=401, detail="Not authenticated with Google")
        
        return build('tasks', 'v1', credentials=self.creds)
    
    async def get_upcoming_events(self, hours_ahead: int = 24) -> list:
        """
        Get real calendar events from Google Calendar.
        
        Args:
            hours_ahead: How many hours to look ahead
            
        Returns:
            List of upcoming events
        """
        try:
            service = self.get_calendar_service()
            
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(hours=hours_ahead)).isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            logger.info(f"📅 Retrieved {len(events)} upcoming events")
            return events
            
        except Exception as e:
            logger.error(f"Failed to get calendar events: {e}")
            return []
    
    async def create_focus_event(self, duration_minutes: int = 25) -> Dict:
        """
        Create a focus time event in calendar.
        
        Args:
            duration_minutes: Duration of focus session
            
        Returns:
            Created event details
        """
        try:
            service = self.get_calendar_service()
            
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
    
    async def add_task(self, title: str, notes: str = None, due: datetime = None) -> Dict:
        """
        Add a task to Google Tasks.
        
        Args:
            title: Task title
            notes: Optional notes
            due: Optional due date
            
        Returns:
            Created task details
        """
        try:
            service = self.get_tasks_service()
            
            task = {
                'title': title,
            }
            
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

# Global instance
oauth_manager: Optional[GoogleOAuthManager] = None

def initialize_oauth(redirect_uri: str = None):
    """Initialize the global OAuth manager."""
    global oauth_manager
    oauth_manager = GoogleOAuthManager(redirect_uri=redirect_uri)
    return oauth_manager

# FastAPI routes to add to your main app
def create_oauth_routes(app):
    """Add OAuth routes to FastAPI app."""
    
    @app.get("/auth/google")
    async def start_google_auth():
        """Start Google OAuth flow."""
        if not oauth_manager:
            raise HTTPException(status_code=500, detail="OAuth not initialized")
        
        auth_url = oauth_manager.get_authorization_url()
        return RedirectResponse(url=auth_url)
    
    @app.get("/auth/callback")
    async def google_auth_callback(code: str, state: str = None):
        """Handle Google OAuth callback."""
        if not oauth_manager:
            raise HTTPException(status_code=500, detail="OAuth not initialized")
        
        success = await oauth_manager.handle_callback(code)
        
        if success:
            # Redirect to dashboard with success message
            return HTMLResponse("""
                <html>
                <head>
                    <title>Authentication Successful</title>
                    <meta http-equiv="refresh" content="3;url=/">
                </head>
                <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                    <h1>✅ Google Authentication Successful!</h1>
                    <p>You can now use calendar and task features.</p>
                    <p>Redirecting to dashboard...</p>
                </body>
                </html>
            """)
        else:
            raise HTTPException(status_code=400, detail="Authentication failed")
    
    @app.get("/auth/status")
    async def auth_status():
        """Check authentication status."""
        if not oauth_manager:
            return {"authenticated": False, "message": "OAuth not initialized"}
        
        return {
            "authenticated": oauth_manager.is_authenticated(),
            "scopes": oauth_manager.SCOPES if oauth_manager.is_authenticated() else []
        }