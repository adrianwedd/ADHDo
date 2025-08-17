#!/usr/bin/env python3
"""
Google API Integration for ADHD Support System
Provides real-time access to Calendar, Tasks, and Fitness data
"""
import pickle
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

try:
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    logger.error("Google API libraries not installed!")

class TaskPriority(Enum):
    """Task priority levels for ADHD management."""
    URGENT = "urgent"  # Do now - overdue or due today
    HIGH = "high"      # Important - due tomorrow
    MEDIUM = "medium"  # Standard - due this week
    LOW = "low"        # Can wait - due later

@dataclass
class GoogleEvent:
    """Represents a calendar event."""
    id: str
    summary: str
    start_time: datetime
    end_time: Optional[datetime]
    location: Optional[str]
    description: Optional[str]
    is_all_day: bool
    minutes_until: int
    
    @property
    def is_soon(self) -> bool:
        """Event is within 30 minutes."""
        return 0 <= self.minutes_until <= 30
    
    @property
    def urgency_level(self) -> str:
        """Get urgency level for ADHD nudging."""
        if self.minutes_until < 0:
            return "happening_now"
        elif self.minutes_until <= 5:
            return "critical"
        elif self.minutes_until <= 15:
            return "urgent"
        elif self.minutes_until <= 30:
            return "soon"
        elif self.minutes_until <= 60:
            return "upcoming"
        else:
            return "later"

@dataclass
class GoogleTask:
    """Represents a task from Google Tasks."""
    id: str
    title: str
    due: Optional[datetime]
    notes: Optional[str]
    status: str  # needsAction or completed
    list_name: str
    
    @property
    def priority(self) -> TaskPriority:
        """Calculate priority based on due date."""
        if not self.due:
            return TaskPriority.LOW
        
        now = datetime.now(timezone.utc)
        if self.due < now:
            return TaskPriority.URGENT  # Overdue
        elif self.due.date() == now.date():
            return TaskPriority.URGENT  # Due today
        elif self.due.date() == (now + timedelta(days=1)).date():
            return TaskPriority.HIGH    # Due tomorrow
        elif self.due < now + timedelta(days=7):
            return TaskPriority.MEDIUM  # Due this week
        else:
            return TaskPriority.LOW     # Due later

@dataclass
class SleepData:
    """Sleep data from Google Fit."""
    duration_hours: float
    bedtime: Optional[datetime]
    wake_time: Optional[datetime]
    quality_score: int  # 1-10 calculated from duration
    
    @property
    def is_poor_sleep(self) -> bool:
        """Check if sleep was poor (affects ADHD)."""
        return self.duration_hours < 6 or self.quality_score < 5

@dataclass
class FitnessData:
    """Fitness data from Google Fit."""
    steps_today: int
    steps_last_hour: int
    last_activity_minutes_ago: int
    calories_burned: int
    distance_meters: int
    active_minutes: int
    sleep_data: Optional[SleepData] = None
    
    @property
    def needs_movement(self) -> bool:
        """Check if user needs a movement break."""
        return (self.steps_last_hour < 100 or 
                self.last_activity_minutes_ago > 60)
    
    @property
    def activity_level(self) -> str:
        """Get current activity level."""
        if self.steps_today < 1000:
            return "sedentary"
        elif self.steps_today < 3000:
            return "low"
        elif self.steps_today < 7000:
            return "moderate"
        elif self.steps_today < 10000:
            return "active"
        else:
            return "very_active"

class GoogleIntegration:
    """Unified Google API integration for ADHD support."""
    
    def __init__(self, token_file: str = "token.pickle"):
        self.token_file = token_file
        self.creds = None
        self.calendar_service = None
        self.tasks_service = None
        self.fitness_service = None
        self._initialize()
    
    def _initialize(self):
        """Initialize Google services."""
        if not GOOGLE_AVAILABLE:
            logger.error("Google API libraries not available")
            return
        
        if not os.path.exists(self.token_file):
            logger.error(f"Token file {self.token_file} not found")
            return
        
        try:
            # Load credentials
            with open(self.token_file, 'rb') as token:
                self.creds = pickle.load(token)
            
            # Refresh if needed
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
                with open(self.token_file, 'wb') as token:
                    pickle.dump(self.creds, token)
            
            # Build services
            if self.creds and self.creds.valid:
                self.calendar_service = build('calendar', 'v3', credentials=self.creds)
                self.tasks_service = build('tasks', 'v1', credentials=self.creds)
                self.fitness_service = build('fitness', 'v1', credentials=self.creds)
                logger.info("✅ Google services initialized")
            else:
                logger.error("Invalid credentials")
                
        except Exception as e:
            logger.error(f"Failed to initialize Google services: {e}")
    
    def get_upcoming_events(self, hours: int = 24) -> List[GoogleEvent]:
        """Get calendar events for the next N hours."""
        if not self.calendar_service:
            return []
        
        try:
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(hours=hours)).isoformat() + 'Z'
            
            events_result = self.calendar_service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=20,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = []
            for item in events_result.get('items', []):
                # Parse start time
                start = item['start'].get('dateTime', item['start'].get('date'))
                if 'T' in start:  # DateTime
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    is_all_day = False
                else:  # Date only (all-day event)
                    start_dt = datetime.fromisoformat(start + 'T00:00:00+00:00')
                    is_all_day = True
                
                # Parse end time
                end = item.get('end', {})
                end_time = None
                if 'dateTime' in end:
                    end_time = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
                
                # Calculate minutes until event - handle timezone
                now_utc = datetime.now(timezone.utc)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                minutes_until = int((start_dt - now_utc).total_seconds() / 60)
                
                events.append(GoogleEvent(
                    id=item['id'],
                    summary=item.get('summary', 'No title'),
                    start_time=start_dt,
                    end_time=end_time,
                    location=item.get('location'),
                    description=item.get('description'),
                    is_all_day=is_all_day,
                    minutes_until=minutes_until
                ))
            
            return sorted(events, key=lambda e: e.start_time)
            
        except Exception as e:
            logger.error(f"Failed to get calendar events: {e}")
            return []
    
    def get_tasks(self, include_completed: bool = False) -> List[GoogleTask]:
        """Get tasks from all task lists."""
        if not self.tasks_service:
            return []
        
        try:
            all_tasks = []
            
            # Get all task lists
            tasklists = self.tasks_service.tasklists().list().execute()
            
            for task_list in tasklists.get('items', []):
                list_id = task_list['id']
                list_name = task_list['title']
                
                # Get tasks from this list
                tasks_result = self.tasks_service.tasks().list(
                    tasklist=list_id,
                    showCompleted=include_completed,
                    maxResults=100
                ).execute()
                
                for item in tasks_result.get('items', []):
                    # Skip completed unless requested
                    if item.get('status') == 'completed' and not include_completed:
                        continue
                    
                    # Parse due date
                    due = None
                    if 'due' in item:
                        due_str = item['due'].replace('Z', '+00:00')
                        due = datetime.fromisoformat(due_str)
                        if due.tzinfo is None:
                            due = due.replace(tzinfo=timezone.utc)
                    
                    all_tasks.append(GoogleTask(
                        id=item['id'],
                        title=item.get('title', 'Untitled'),
                        due=due,
                        notes=item.get('notes'),
                        status=item.get('status', 'needsAction'),
                        list_name=list_name
                    ))
            
            # Sort by priority (use timezone-aware max datetime for comparison)
            max_date = datetime.max.replace(tzinfo=timezone.utc)
            return sorted(all_tasks, key=lambda t: (t.priority.value, t.due or max_date))
            
        except Exception as e:
            logger.error(f"Failed to get tasks: {e}")
            return []
    
    def get_sleep_data(self) -> Optional[SleepData]:
        """Get most recent sleep data from Google Fit (checks last 7 days)."""
        if not self.fitness_service:
            return None
        
        try:
            now = datetime.now()
            week_ago = now - timedelta(days=7)
            
            # First try to find sleep sessions (more reliable)
            sessions = self.fitness_service.users().sessions().list(
                userId='me',
                startTime=week_ago.isoformat() + 'Z',
                endTime=now.isoformat() + 'Z'
            ).execute()
            
            # Find most recent sleep session
            sleep_sessions = []
            for session in sessions.get('session', []):
                if 'sleep' in session.get('name', '').lower() or \
                   session.get('activityType') == 72:  # 72 is sleep
                    sleep_sessions.append(session)
            
            if sleep_sessions:
                # Sort by start time, get most recent
                sleep_sessions.sort(key=lambda s: s['startTimeMillis'], reverse=True)
                latest = sleep_sessions[0]
                
                start_ms = int(latest['startTimeMillis'])
                end_ms = int(latest['endTimeMillis'])
                duration_hours = (end_ms - start_ms) / (1000 * 60 * 60)
                
                bedtime = datetime.fromtimestamp(start_ms / 1000)
                wake_time = datetime.fromtimestamp(end_ms / 1000)
                
                # Calculate quality based on duration
                if duration_hours >= 8:
                    quality_score = 10
                elif duration_hours >= 7:
                    quality_score = 8
                elif duration_hours >= 6:
                    quality_score = 6
                elif duration_hours >= 5:
                    quality_score = 4
                else:
                    quality_score = 2
                
                logger.info(f"Found sleep: {bedtime} to {wake_time} ({duration_hours:.1f}h)")
                
                return SleepData(
                    duration_hours=round(duration_hours, 1),
                    bedtime=bedtime,
                    wake_time=wake_time,
                    quality_score=quality_score
                )
            
            # Fallback to aggregate API if no sessions found
            body = {
                "aggregateBy": [{
                    "dataTypeName": "com.google.sleep.segment"
                }],
                "startTimeMillis": int(week_ago.timestamp() * 1000),
                "endTimeMillis": int(now.timestamp() * 1000)
            }
            
            result = self.fitness_service.users().dataset().aggregate(
                userId='me',
                body=body
            ).execute()
            
            # Parse sleep segments
            total_sleep_ms = 0
            bedtime = None
            wake_time = None
            
            for bucket in result.get('bucket', []):
                for dataset in bucket.get('dataset', []):
                    for point in dataset.get('point', []):
                        # Get sleep segment times
                        start_ms = int(point.get('startTimeNanos', 0)) // 1000000
                        end_ms = int(point.get('endTimeNanos', 0)) // 1000000
                        
                        if start_ms and end_ms:
                            # Track earliest bedtime and latest wake time
                            segment_start = datetime.fromtimestamp(start_ms / 1000)
                            segment_end = datetime.fromtimestamp(end_ms / 1000)
                            
                            if not bedtime or segment_start < bedtime:
                                bedtime = segment_start
                            if not wake_time or segment_end > wake_time:
                                wake_time = segment_end
                            
                            # Add to total sleep
                            for value in point.get('value', []):
                                # Sleep segment type: 72 = sleep, 109 = light, 110 = deep, 111 = REM
                                if 'intVal' in value and value['intVal'] in [72, 109, 110, 111]:
                                    total_sleep_ms += (end_ms - start_ms)
            
            if total_sleep_ms > 0:
                duration_hours = total_sleep_ms / (1000 * 60 * 60)
                
                # Calculate quality score based on duration
                if duration_hours >= 8:
                    quality_score = 10
                elif duration_hours >= 7:
                    quality_score = 8
                elif duration_hours >= 6:
                    quality_score = 6
                elif duration_hours >= 5:
                    quality_score = 4
                else:
                    quality_score = 2
                
                return SleepData(
                    duration_hours=round(duration_hours, 1),
                    bedtime=bedtime,
                    wake_time=wake_time,
                    quality_score=quality_score
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not get sleep data: {e}")
            return None
    
    def get_fitness_data(self) -> Optional[FitnessData]:
        """Get fitness data for today."""
        if not self.fitness_service:
            return None
        
        try:
            now = datetime.now()
            midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
            hour_ago = now - timedelta(hours=1)
            
            # Convert to milliseconds
            now_millis = int(now.timestamp() * 1000)
            midnight_millis = int(midnight.timestamp() * 1000)
            hour_ago_millis = int(hour_ago.timestamp() * 1000)
            
            # Get today's aggregate data
            body = {
                "aggregateBy": [
                    {"dataTypeName": "com.google.step_count.delta"},
                    {"dataTypeName": "com.google.calories.expended"},
                    {"dataTypeName": "com.google.distance.delta"},
                    {"dataTypeName": "com.google.active_minutes"}
                ],
                "startTimeMillis": midnight_millis,
                "endTimeMillis": now_millis
            }
            
            result = self.fitness_service.users().dataset().aggregate(
                userId='me',
                body=body
            ).execute()
            
            # Parse results
            steps_today = 0
            calories = 0
            distance = 0
            active_minutes = 0
            
            for bucket in result.get('bucket', []):
                for dataset in bucket.get('dataset', []):
                    data_type = dataset.get('dataSourceId', '')
                    
                    for point in dataset.get('point', []):
                        for value in point.get('value', []):
                            if 'step_count' in data_type:
                                steps_today += value.get('intVal', 0)
                            elif 'calories' in data_type:
                                calories += int(value.get('fpVal', 0))
                            elif 'distance' in data_type:
                                distance += int(value.get('fpVal', 0))
                            elif 'active_minutes' in data_type:
                                active_minutes += value.get('intVal', 0)
            
            # Get last hour's steps
            hour_body = {
                "aggregateBy": [{"dataTypeName": "com.google.step_count.delta"}],
                "startTimeMillis": hour_ago_millis,
                "endTimeMillis": now_millis
            }
            
            hour_result = self.fitness_service.users().dataset().aggregate(
                userId='me',
                body=hour_body
            ).execute()
            
            steps_last_hour = 0
            last_activity_time = hour_ago
            
            for bucket in hour_result.get('bucket', []):
                for dataset in bucket.get('dataset', []):
                    for point in dataset.get('point', []):
                        for value in point.get('value', []):
                            steps_last_hour += value.get('intVal', 0)
                        # Update last activity time
                        if point.get('endTimeNanos'):
                            last_activity_time = datetime.fromtimestamp(
                                int(point['endTimeNanos']) / 1e9
                            )
            
            last_activity_minutes = int((now - last_activity_time).total_seconds() / 60)
            
            # Also get sleep data
            sleep_data = self.get_sleep_data()
            
            return FitnessData(
                steps_today=steps_today,
                steps_last_hour=steps_last_hour,
                last_activity_minutes_ago=last_activity_minutes,
                calories_burned=calories,
                distance_meters=distance,
                active_minutes=active_minutes,
                sleep_data=sleep_data
            )
            
        except Exception as e:
            logger.error(f"Failed to get fitness data: {e}")
            return None
    
    def get_adhd_context(self) -> Dict[str, Any]:
        """Get comprehensive ADHD context from all Google services."""
        context = {
            "calendar": {
                "next_event": None,
                "events_today": [],
                "urgent_items": []
            },
            "tasks": {
                "urgent_tasks": [],
                "high_priority": [],
                "total_pending": 0
            },
            "fitness": {
                "needs_movement": False,
                "activity_level": "unknown",
                "steps_today": 0
            },
            "recommendations": []
        }
        
        # Get calendar events
        events = self.get_upcoming_events(hours=12)
        if events:
            context["calendar"]["next_event"] = {
                "title": events[0].summary,
                "time": events[0].start_time.strftime("%I:%M %p"),
                "minutes_until": events[0].minutes_until,
                "urgency": events[0].urgency_level
            }
            
            # Today's events
            today = datetime.now().date()
            context["calendar"]["events_today"] = [
                {
                    "title": e.summary,
                    "time": e.start_time.strftime("%I:%M %p"),
                    "urgency": e.urgency_level
                }
                for e in events if e.start_time.date() == today
            ]
            
            # Urgent items (within 30 minutes)
            context["calendar"]["urgent_items"] = [
                e.summary for e in events if e.is_soon
            ]
        
        # Get tasks
        tasks = self.get_tasks()
        if tasks:
            context["tasks"]["total_pending"] = len(tasks)
            context["tasks"]["urgent_tasks"] = [
                {"title": t.title, "list": t.list_name}
                for t in tasks if t.priority == TaskPriority.URGENT
            ][:3]
            context["tasks"]["high_priority"] = [
                {"title": t.title, "list": t.list_name}
                for t in tasks if t.priority == TaskPriority.HIGH
            ][:3]
        
        # Get fitness data
        fitness = self.get_fitness_data()
        if fitness:
            context["fitness"] = {
                "needs_movement": fitness.needs_movement,
                "activity_level": fitness.activity_level,
                "steps_today": fitness.steps_today,
                "steps_last_hour": fitness.steps_last_hour,
                "last_activity_minutes": fitness.last_activity_minutes_ago
            }
            
            # Generate recommendations
            if fitness.needs_movement and events and events[0].minutes_until > 20:
                context["recommendations"].append(
                    f"Take a 5-minute walk before {events[0].summary} - you haven't moved in {fitness.last_activity_minutes_ago} minutes"
                )
            
            if fitness.steps_today < 1000 and len(tasks) > 5:
                context["recommendations"].append(
                    "High task load + low movement = recipe for ADHD paralysis. Take a quick walk to reset!"
                )
        
        # Cross-integration insights
        if events and tasks:
            if len(context["calendar"]["urgent_items"]) > 0 and len(context["tasks"]["urgent_tasks"]) > 2:
                context["recommendations"].append(
                    "⚠️ Multiple urgent items detected. Pick ONE task to do before your meeting."
                )
        
        return context

# Singleton instance
_google_integration = None

def get_google_integration() -> Optional[GoogleIntegration]:
    """Get or create the Google integration singleton."""
    global _google_integration
    if _google_integration is None:
        try:
            _google_integration = GoogleIntegration()
        except Exception as e:
            logger.error(f"Failed to create Google integration: {e}")
    return _google_integration

# Quick test
if __name__ == "__main__":
    google = get_google_integration()
    if google:
        context = google.get_adhd_context()
        print("ADHD Context from Google APIs:")
        import json
        print(json.dumps(context, indent=2, default=str))