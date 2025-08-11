"""
Home Assistant Integration for ADHD Context
Pulls calendar, health, and sensor data from your existing Home Assistant setup
"""
import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

class HomeAssistantClient:
    """Client for Home Assistant API integration."""
    
    def __init__(self, 
                 ha_url: str = None,
                 ha_token: str = None):
        """Initialize Home Assistant client.
        
        Args:
            ha_url: Home Assistant URL (e.g., http://192.168.1.100:8123)
            ha_token: Long-lived access token from Home Assistant
        """
        self.ha_url = ha_url or os.getenv("HOME_ASSISTANT_URL", "http://homeassistant.local:8123")
        self.ha_token = ha_token or os.getenv("HOME_ASSISTANT_TOKEN", "")
        self.headers = {
            "Authorization": f"Bearer {self.ha_token}",
            "Content-Type": "application/json"
        }
        self.session = None
        self.is_connected = False
    
    async def initialize(self) -> bool:
        """Initialize connection to Home Assistant."""
        try:
            self.session = aiohttp.ClientSession()
            
            # Test connection
            async with self.session.get(
                f"{self.ha_url}/api/",
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"✅ Connected to Home Assistant: {data.get('message', 'OK')}")
                    self.is_connected = True
                    return True
                else:
                    logger.warning(f"Home Assistant connection failed: {response.status}")
                    await self.session.close()
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to connect to Home Assistant: {e}")
            if self.session:
                await self.session.close()
            return False
    
    async def get_calendar_events(self, days_ahead: int = 7) -> List[Dict]:
        """Get calendar events from Home Assistant.
        
        Home Assistant aggregates all your calendars (Google, etc.)
        """
        if not self.is_connected:
            return []
        
        try:
            # Get all calendar entities
            async with self.session.get(
                f"{self.ha_url}/api/calendars",
                headers=self.headers
            ) as response:
                if response.status != 200:
                    return []
                calendars = await response.json()
            
            all_events = []
            start = datetime.now(timezone.utc)
            end = start + timedelta(days=days_ahead)
            
            # Get events from each calendar
            for calendar in calendars:
                calendar_id = calendar['entity_id']
                
                async with self.session.get(
                    f"{self.ha_url}/api/calendars/{calendar_id}",
                    headers=self.headers,
                    params={
                        "start": start.isoformat(),
                        "end": end.isoformat()
                    }
                ) as response:
                    if response.status == 200:
                        events = await response.json()
                        for event in events:
                            all_events.append(self._process_ha_event(event))
            
            # Sort by start time
            all_events.sort(key=lambda x: x['start_time'])
            return all_events
            
        except Exception as e:
            logger.error(f"Failed to get calendar events: {e}")
            return []
    
    def _process_ha_event(self, event: Dict) -> Dict:
        """Process Home Assistant calendar event for ADHD context."""
        # Extract and enhance event data
        summary = event.get('summary', 'Untitled')
        start = datetime.fromisoformat(event.get('start', {}).get('dateTime', ''))
        end = datetime.fromisoformat(event.get('end', {}).get('dateTime', ''))
        
        now = datetime.now(timezone.utc)
        time_until = start - now
        duration = end - start
        
        # Calculate ADHD metrics
        if time_until.total_seconds() < 0:
            urgency = "happening_now"
        elif time_until.total_seconds() < 900:  # 15 min
            urgency = "imminent"
        elif time_until.total_seconds() < 3600:  # 1 hour
            urgency = "soon"
        else:
            urgency = "later"
        
        return {
            "summary": summary,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "urgency": urgency,
            "time_until_minutes": int(time_until.total_seconds() / 60),
            "duration_minutes": int(duration.total_seconds() / 60),
            "location": event.get('location', ''),
            "description": event.get('description', '')
        }
    
    async def get_health_data(self) -> Dict[str, Any]:
        """Get health and activity data from Home Assistant sensors."""
        if not self.is_connected:
            return {}
        
        health_data = {}
        
        # Common health sensor patterns
        health_sensors = {
            "steps": ["sensor.*step", "sensor.*steps"],
            "heart_rate": ["sensor.*heart_rate", "sensor.*heartrate", "sensor.*bpm"],
            "sleep": ["sensor.*sleep", "sensor.*bed", "sensor.*asleep"],
            "activity": ["sensor.*activity", "sensor.*exercise"],
            "stress": ["sensor.*stress", "sensor.*hrv"],
            "weight": ["sensor.*weight"],
            "blood_pressure": ["sensor.*blood_pressure", "sensor.*bp"]
        }
        
        try:
            # Get all entities
            async with self.session.get(
                f"{self.ha_url}/api/states",
                headers=self.headers
            ) as response:
                if response.status != 200:
                    return health_data
                states = await response.json()
            
            # Extract health-related sensors
            for entity in states:
                entity_id = entity.get('entity_id', '')
                
                for category, patterns in health_sensors.items():
                    for pattern in patterns:
                        if pattern.replace('*', '') in entity_id.lower():
                            if category not in health_data:
                                health_data[category] = []
                            
                            health_data[category].append({
                                "entity_id": entity_id,
                                "state": entity.get('state'),
                                "attributes": entity.get('attributes', {}),
                                "last_updated": entity.get('last_updated')
                            })
            
            # Process sleep data for ADHD insights
            if 'sleep' in health_data:
                health_data['sleep_quality'] = self._analyze_sleep_quality(health_data['sleep'])
            
            # Process activity for dopamine insights
            if 'activity' in health_data or 'steps' in health_data:
                health_data['activity_level'] = self._analyze_activity_level(
                    health_data.get('activity', []),
                    health_data.get('steps', [])
                )
            
            return health_data
            
        except Exception as e:
            logger.error(f"Failed to get health data: {e}")
            return health_data
    
    def _analyze_sleep_quality(self, sleep_data: List[Dict]) -> Dict:
        """Analyze sleep data for ADHD impact."""
        # This would analyze sleep patterns
        # Poor sleep severely impacts ADHD symptoms
        return {
            "quality": "unknown",
            "adhd_impact": "Sleep quality affects focus and impulse control",
            "recommendation": "Track sleep patterns for better ADHD management"
        }
    
    def _analyze_activity_level(self, activity_data: List[Dict], steps_data: List[Dict]) -> Dict:
        """Analyze activity for dopamine regulation."""
        # Physical activity helps ADHD symptom management
        total_steps = 0
        for step_sensor in steps_data:
            try:
                total_steps += int(step_sensor.get('state', 0))
            except:
                pass
        
        if total_steps > 10000:
            activity_level = "high"
            adhd_benefit = "Excellent for dopamine regulation"
        elif total_steps > 5000:
            activity_level = "moderate"
            adhd_benefit = "Good for focus improvement"
        else:
            activity_level = "low"
            adhd_benefit = "Consider a walk for better focus"
        
        return {
            "level": activity_level,
            "steps_today": total_steps,
            "adhd_benefit": adhd_benefit
        }
    
    async def get_environment_context(self) -> Dict[str, Any]:
        """Get environmental context (lights, temperature, etc.)."""
        if not self.is_connected:
            return {}
        
        context = {
            "lights": [],
            "climate": [],
            "media": []
        }
        
        try:
            async with self.session.get(
                f"{self.ha_url}/api/states",
                headers=self.headers
            ) as response:
                if response.status != 200:
                    return context
                states = await response.json()
            
            for entity in states:
                entity_id = entity.get('entity_id', '')
                state = entity.get('state')
                
                # Track what's happening in environment
                if entity_id.startswith('light.'):
                    if state == 'on':
                        context['lights'].append(entity_id)
                
                elif entity_id.startswith('climate.'):
                    context['climate'].append({
                        "entity": entity_id,
                        "temperature": entity.get('attributes', {}).get('current_temperature'),
                        "state": state
                    })
                
                elif entity_id.startswith('media_player.'):
                    if state == 'playing':
                        context['media'].append({
                            "entity": entity_id,
                            "media": entity.get('attributes', {}).get('media_title', 'Unknown')
                        })
            
            # Analyze for ADHD optimization
            context['adhd_optimization'] = self._analyze_environment_for_adhd(context)
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get environment context: {e}")
            return context
    
    def _analyze_environment_for_adhd(self, context: Dict) -> Dict:
        """Analyze environment for ADHD optimization."""
        suggestions = []
        
        # Check lighting
        if len(context['lights']) == 0:
            suggestions.append("Consider turning on lights for better alertness")
        elif len(context['lights']) > 5:
            suggestions.append("Many lights on - might be overstimulating")
        
        # Check media
        if context['media']:
            suggestions.append("Media playing - might be distracting from tasks")
        
        # Check temperature
        for climate in context['climate']:
            temp = climate.get('temperature')
            if temp and (temp < 18 or temp > 24):
                suggestions.append(f"Temperature {temp}°C might affect focus")
        
        return {
            "suggestions": suggestions,
            "focus_score": self._calculate_focus_score(context)
        }
    
    def _calculate_focus_score(self, context: Dict) -> float:
        """Calculate environment focus score (0-1)."""
        score = 1.0
        
        # Deduct for distractions
        if context['media']:
            score -= 0.3
        
        if len(context['lights']) == 0:
            score -= 0.2
        elif len(context['lights']) > 5:
            score -= 0.1
        
        return max(0, min(1, score))
    
    async def create_calendar_event(self, 
                                   summary: str,
                                   start: datetime,
                                   end: datetime,
                                   description: str = "") -> bool:
        """Create calendar event through Home Assistant."""
        if not self.is_connected:
            return False
        
        try:
            # Home Assistant calendar create event service
            service_data = {
                "summary": summary,
                "description": description,
                "start_date_time": start.isoformat(),
                "end_date_time": end.isoformat()
            }
            
            async with self.session.post(
                f"{self.ha_url}/api/services/calendar/create_event",
                headers=self.headers,
                json={
                    "entity_id": "calendar.primary",  # Adjust to your calendar
                    **service_data
                }
            ) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            return False
    
    async def send_notification(self, message: str, title: str = "ADHDo Reminder") -> bool:
        """Send notification through Home Assistant."""
        if not self.is_connected:
            return False
        
        try:
            async with self.session.post(
                f"{self.ha_url}/api/services/notify/notify",
                headers=self.headers,
                json={
                    "message": message,
                    "title": title
                }
            ) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    async def get_adhd_context(self) -> Dict[str, Any]:
        """Get comprehensive ADHD-optimized context from Home Assistant."""
        context = {
            "calendar": await self.get_calendar_events(days_ahead=1),
            "health": await self.get_health_data(),
            "environment": await self.get_environment_context()
        }
        
        # Calculate overall cognitive load
        cognitive_load = 0.3  # Base load
        
        # Add load from upcoming events
        imminent_events = [e for e in context['calendar'] if e['urgency'] in ['imminent', 'happening_now']]
        cognitive_load += len(imminent_events) * 0.2
        
        # Adjust for sleep quality
        if context['health'].get('sleep_quality', {}).get('quality') == 'poor':
            cognitive_load += 0.2
        
        # Adjust for environment
        focus_score = context['environment'].get('adhd_optimization', {}).get('focus_score', 0.5)
        cognitive_load += (1 - focus_score) * 0.2
        
        context['cognitive_load'] = min(1.0, cognitive_load)
        context['recommendations'] = self._generate_recommendations(context)
        
        return context
    
    def _generate_recommendations(self, context: Dict) -> List[str]:
        """Generate ADHD-specific recommendations based on context."""
        recs = []
        
        # Check calendar
        if context['calendar']:
            next_event = context['calendar'][0]
            if next_event['urgency'] == 'imminent':
                recs.append(f"⏰ {next_event['summary']} starting soon - wrap up current task")
            elif next_event['urgency'] == 'soon':
                recs.append(f"📅 {next_event['summary']} in {next_event['time_until_minutes']} minutes")
        
        # Check activity
        activity = context['health'].get('activity_level', {})
        if activity.get('level') == 'low':
            recs.append("🚶 Consider a quick walk to boost dopamine")
        
        # Check environment
        env_suggestions = context['environment'].get('adhd_optimization', {}).get('suggestions', [])
        recs.extend(env_suggestions[:2])  # Top 2 environment suggestions
        
        return recs
    
    async def cleanup(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()


# Global instance
ha_client: Optional[HomeAssistantClient] = None

async def initialize_home_assistant(ha_url: str = None, ha_token: str = None) -> bool:
    """Initialize Home Assistant integration."""
    global ha_client
    
    try:
        ha_client = HomeAssistantClient(ha_url, ha_token)
        success = await ha_client.initialize()
        
        if success:
            logger.info("🏠 Home Assistant integration ready")
            return True
        else:
            ha_client = None
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize Home Assistant: {e}")
        ha_client = None
        return False