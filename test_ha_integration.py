#!/usr/bin/env python3
"""Test Home Assistant Integration"""
import asyncio
import sys
import os
sys.path.insert(0, 'src')

from mcp_server.home_assistant_integration import initialize_home_assistant, ha_client

async def test_ha():
    print("🏠 Testing Home Assistant Integration")
    print("=" * 50)
    
    # Initialize
    success = await initialize_home_assistant()
    if not success:
        print("❌ Failed to connect to Home Assistant")
        return
    
    print("\n📅 Getting calendar events...")
    events = await ha_client.get_calendar_events(days_ahead=7)
    if events:
        print(f"Found {len(events)} upcoming events:")
        for event in events[:3]:  # Show first 3
            print(f"  - {event['summary']}")
            print(f"    Time: {event['urgency']} ({event['time_until_minutes']} min)")
    else:
        print("No upcoming events found")
    
    print("\n💓 Getting health data...")
    health = await ha_client.get_health_data()
    if health:
        print("Health sensors found:")
        for category, data in health.items():
            if isinstance(data, list):
                print(f"  - {category}: {len(data)} sensor(s)")
            else:
                print(f"  - {category}: {data}")
    else:
        print("No health data found")
    
    print("\n🏡 Getting environment context...")
    env = await ha_client.get_environment_context()
    print(f"  - Lights on: {len(env.get('lights', []))}")
    print(f"  - Media playing: {len(env.get('media', []))}")
    print(f"  - Focus score: {env.get('adhd_optimization', {}).get('focus_score', 0):.2f}")
    
    suggestions = env.get('adhd_optimization', {}).get('suggestions', [])
    if suggestions:
        print("  Suggestions:")
        for sug in suggestions:
            print(f"    • {sug}")
    
    print("\n🧠 Getting ADHD context...")
    context = await ha_client.get_adhd_context()
    print(f"  - Cognitive load: {context.get('cognitive_load', 0):.2f}")
    
    recs = context.get('recommendations', [])
    if recs:
        print("  Recommendations:")
        for rec in recs:
            print(f"    • {rec}")
    
    await ha_client.cleanup()
    print("\n✅ Home Assistant integration working!")

if __name__ == "__main__":
    asyncio.run(test_ha())