"""
Google Calendar Integration for ADHD Time Management Support.

This module provides ADHD-specific calendar integration features including:
- Proactive transition support (pre-event notifications)
- Executive function assistance (preparation checklists)
- Time blindness compensation (visual time indicators)
- Overwhelm prevention (schedule density analysis)
- Context-aware notifications
"""

from .client import CalendarClient
from .models import CalendarEvent, CalendarInsight, TransitionAlert
from .processor import ADHDCalendarProcessor
from .nudges import CalendarNudger

__all__ = [
    "CalendarClient",
    "CalendarEvent", 
    "CalendarInsight",
    "TransitionAlert",
    "ADHDCalendarProcessor",
    "CalendarNudger"
]