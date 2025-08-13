#!/usr/bin/env python3
"""Simple test of Home Assistant connection"""
import aiohttp
import asyncio
import os

async def test():
    url = "http://homeassistant.local:8123"
    token = os.getenv("HOME_ASSISTANT_TOKEN", "")
    
    if not token:
        print("❌ HOME_ASSISTANT_TOKEN environment variable not set")
        print("💡 Get your token from Home Assistant > Profile > Long-lived access tokens")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"Testing: {url}")
    print(f"Token: {token[:20]}...")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test basic API
            async with session.get(f"{url}/api/", headers=headers) as resp:
                print(f"API Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(f"Response: {data}")
                    
            # Get calendars
            async with session.get(f"{url}/api/calendars", headers=headers) as resp:
                print(f"\nCalendars Status: {resp.status}")
                if resp.status == 200:
                    calendars = await resp.json()
                    print(f"Found {len(calendars)} calendar(s)")
                    for cal in calendars[:3]:
                        print(f"  - {cal.get('entity_id', 'Unknown')}: {cal.get('name', 'Unknown')}")
            
            # Get some entities
            async with session.get(f"{url}/api/states", headers=headers) as resp:
                print(f"\nStates Status: {resp.status}")
                if resp.status == 200:
                    states = await resp.json()
                    print(f"Found {len(states)} entities")
                    
                    # Look for interesting sensors
                    health_entities = []
                    calendar_entities = []
                    
                    for entity in states:
                        entity_id = entity.get('entity_id', '')
                        if 'calendar.' in entity_id:
                            calendar_entities.append(entity_id)
                        elif any(kw in entity_id.lower() for kw in ['step', 'heart', 'sleep', 'activity']):
                            health_entities.append(entity_id)
                    
                    print(f"\nCalendar entities: {calendar_entities[:5]}")
                    print(f"Health entities: {health_entities[:5]}")
                    
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(test())