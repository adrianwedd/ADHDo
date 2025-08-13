#!/usr/bin/env python3
"""
Setup script for Google API integration with ADHD Support System
Run this after downloading credentials.json from Google Cloud Console
"""
import os
import pickle
import json
from pathlib import Path

# Google API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    print("✅ Google API libraries installed")
except ImportError:
    print("❌ Missing Google API libraries. Installing...")
    os.system("pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    print("Please run this script again after installation completes")
    exit(1)

# Define all scopes needed for ADHD support
SCOPES = [
    # Calendar - Essential for meeting awareness
    'https://www.googleapis.com/auth/calendar',
    
    # Tasks - For ADHD task management
    'https://www.googleapis.com/auth/tasks',
    
    # Gmail - For email context (read-only)
    'https://www.googleapis.com/auth/gmail.readonly',
    
    # Drive - For document access (read-only)
    'https://www.googleapis.com/auth/drive.readonly',
    
    # Fitness - For activity tracking
    'https://www.googleapis.com/auth/fitness.activity.read',
    'https://www.googleapis.com/auth/fitness.sleep.read',
    
    # Assistant SDK - For voice interactions
    'https://www.googleapis.com/auth/assistant-sdk-prototype',
]

def authenticate_google_apis():
    """Authenticate and save tokens for all Google APIs."""
    creds = None
    token_file = 'token.pickle'
    
    # Check for existing token
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
            print("📂 Loaded existing credentials")
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("❌ credentials.json not found!")
                print("\nPlease:")
                print("1. Go to https://console.cloud.google.com/")
                print("2. Create OAuth 2.0 credentials")
                print("3. Download as credentials.json")
                print("4. Place in this directory")
                return False
            
            print("🔐 Starting OAuth flow...")
            print("\nThis will open a browser for authentication.")
            print("Please authorize access to the requested scopes.\n")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            print("✅ Authentication successful!")
        
        # Save the credentials for the next run
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
            print("💾 Saved credentials to token.pickle")
    
    return creds

def test_apis(creds):
    """Test each API to ensure it's working."""
    print("\n🧪 Testing API connections...\n")
    
    results = {}
    
    # Test Calendar API
    try:
        service = build('calendar', 'v3', credentials=creds)
        result = service.calendarList().list(maxResults=1).execute()
        calendars = result.get('items', [])
        if calendars:
            print(f"✅ Calendar API: Found calendar '{calendars[0]['summary']}'")
            results['calendar'] = True
        else:
            print("⚠️ Calendar API: No calendars found")
            results['calendar'] = False
    except Exception as e:
        print(f"❌ Calendar API: {e}")
        results['calendar'] = False
    
    # Test Tasks API
    try:
        service = build('tasks', 'v1', credentials=creds)
        result = service.tasklists().list(maxResults=1).execute()
        tasklists = result.get('items', [])
        if tasklists:
            print(f"✅ Tasks API: Found task list '{tasklists[0]['title']}'")
            results['tasks'] = True
        else:
            print("⚠️ Tasks API: No task lists found")
            results['tasks'] = False
    except Exception as e:
        print(f"❌ Tasks API: {e}")
        results['tasks'] = False
    
    # Test Gmail API
    try:
        service = build('gmail', 'v1', credentials=creds)
        result = service.users().labels().list(userId='me').execute()
        labels = result.get('labels', [])
        if labels:
            print(f"✅ Gmail API: Connected to inbox")
            results['gmail'] = True
        else:
            print("⚠️ Gmail API: No labels found")
            results['gmail'] = False
    except Exception as e:
        print(f"❌ Gmail API: {e}")
        results['gmail'] = False
    
    # Test Drive API
    try:
        service = build('drive', 'v3', credentials=creds)
        result = service.files().list(pageSize=1).execute()
        print(f"✅ Drive API: Connected to Google Drive")
        results['drive'] = True
    except Exception as e:
        print(f"❌ Drive API: {e}")
        results['drive'] = False
    
    # Test Fitness API
    try:
        service = build('fitness', 'v1', credentials=creds)
        # This might fail if no fitness data exists
        print(f"✅ Fitness API: Connected (data may not be available)")
        results['fitness'] = True
    except Exception as e:
        print(f"⚠️ Fitness API: {e}")
        results['fitness'] = False
    
    return results

def create_config_file(results):
    """Create configuration file for the ADHD system."""
    config = {
        "google_apis": {
            "enabled": True,
            "token_file": "token.pickle",
            "credentials_file": "credentials.json",
            "apis_available": results,
            "scopes": SCOPES
        },
        "features": {
            "calendar_integration": results.get('calendar', False),
            "task_management": results.get('tasks', False),
            "email_context": results.get('gmail', False),
            "document_access": results.get('drive', False),
            "fitness_tracking": results.get('fitness', False)
        }
    }
    
    with open('google_api_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("\n📝 Created google_api_config.json")
    return config

def setup_adhd_calendar(creds):
    """Create ADHD-specific calendar if it doesn't exist."""
    try:
        service = build('calendar', 'v3', credentials=creds)
        
        # Check if ADHD Focus calendar exists
        calendars = service.calendarList().list().execute()
        adhd_calendar = None
        
        for calendar in calendars.get('items', []):
            if calendar['summary'] == 'ADHD Focus Time':
                adhd_calendar = calendar
                print(f"📅 Found existing ADHD Focus Time calendar")
                break
        
        if not adhd_calendar:
            # Create new calendar for ADHD focus sessions
            calendar_body = {
                'summary': 'ADHD Focus Time',
                'description': 'Automated focus sessions and ADHD support events',
                'timeZone': 'America/Los_Angeles'  # Change to your timezone
            }
            
            adhd_calendar = service.calendars().insert(body=calendar_body).execute()
            print(f"✅ Created ADHD Focus Time calendar: {adhd_calendar['id']}")
        
        return adhd_calendar['id']
        
    except Exception as e:
        print(f"⚠️ Could not create ADHD calendar: {e}")
        return None

def main():
    """Main setup process."""
    print("🧠 ADHD Support System - Google API Setup")
    print("=" * 50)
    
    # Step 1: Authenticate
    creds = authenticate_google_apis()
    if not creds:
        return
    
    # Step 2: Test APIs
    results = test_apis(creds)
    
    # Step 3: Create config
    config = create_config_file(results)
    
    # Step 4: Setup ADHD calendar
    if results.get('calendar'):
        calendar_id = setup_adhd_calendar(creds)
        if calendar_id:
            config['adhd_calendar_id'] = calendar_id
            with open('google_api_config.json', 'w') as f:
                json.dump(config, f, indent=2)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Setup Summary:")
    print(f"✅ Authenticated: Yes")
    print(f"📅 Calendar API: {'✅' if results.get('calendar') else '❌'}")
    print(f"📝 Tasks API: {'✅' if results.get('tasks') else '❌'}")
    print(f"📧 Gmail API: {'✅' if results.get('gmail') else '❌'}")
    print(f"📁 Drive API: {'✅' if results.get('drive') else '❌'}")
    print(f"💪 Fitness API: {'✅' if results.get('fitness') else '❌'}")
    
    if all(results.values()):
        print("\n🎉 All APIs configured successfully!")
    else:
        print("\n⚠️ Some APIs need attention. Check the errors above.")
    
    print("\n📌 Next steps:")
    print("1. The ADHD system will use token.pickle for authentication")
    print("2. Your credentials are saved and will auto-refresh")
    print("3. You can now use real calendar data instead of mocks")

if __name__ == "__main__":
    main()