#!/usr/bin/env python3
"""
Setup Home Assistant Integration for ADHDo
Gets your HA token and tests the connection
"""
import asyncio
import aiohttp
import os
import json

async def test_home_assistant():
    """Test Home Assistant connection and setup."""
    
    print("🏠 ADHDo Home Assistant Setup")
    print("=" * 50)
    
    # Check for existing config
    ha_url = os.getenv("HOME_ASSISTANT_URL", "http://homeassistant.local:8123")
    ha_token = os.getenv("HOME_ASSISTANT_TOKEN", "")
    
    if not ha_token:
        print("\n📝 To connect to Home Assistant, you need a Long-Lived Access Token")
        print("\nSteps to get your token:")
        print("1. Open Home Assistant: http://homeassistant.local:8123")
        print("2. Click on your profile (bottom left)")
        print("3. Scroll down to 'Long-Lived Access Tokens'")
        print("4. Click 'Create Token'")
        print("5. Name it 'ADHDo Integration'")
        print("6. Copy the token (you won't see it again!)")
        print()
        ha_token = input("Paste your Home Assistant token here: ").strip()
    
    print(f"\n🔍 Testing connection to: {ha_url}")
    
    headers = {
        "Authorization": f"Bearer {ha_token}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            # Test API connection
            async with session.get(
                f"{ha_url}/api/",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Connected to Home Assistant!")
                    print(f"   Version: {data.get('version', 'Unknown')}")
                else:
                    print(f"❌ Connection failed: {response.status}")
                    return
        except Exception as e:
            print(f"❌ Could not connect: {e}")
            print("\nTroubleshooting:")
            print("- Is Home Assistant running?")
            print("- Is the URL correct? (try http://192.168.1.XXX:8123)")
            print("- Is the token correct?")
            return
        
        # Get available calendars
        print("\n📅 Checking calendars...")
        try:
            async with session.get(
                f"{ha_url}/api/calendars",
                headers=headers
            ) as response:
                if response.status == 200:
                    calendars = await response.json()
                    print(f"   Found {len(calendars)} calendar(s):")
                    for cal in calendars:
                        print(f"   - {cal.get('name', 'Unknown')}")
        except:
            print("   No calendars found")
        
        # Get health sensors
        print("\n💓 Checking health sensors...")
        try:
            async with session.get(
                f"{ha_url}/api/states",
                headers=headers
            ) as response:
                if response.status == 200:
                    states = await response.json()
                    
                    health_sensors = []
                    for entity in states:
                        entity_id = entity.get('entity_id', '')
                        # Look for health-related sensors
                        health_keywords = ['step', 'heart', 'sleep', 'activity', 'weight', 'stress']
                        if any(kw in entity_id.lower() for kw in health_keywords):
                            health_sensors.append(entity_id)
                    
                    if health_sensors:
                        print(f"   Found {len(health_sensors)} health sensor(s):")
                        for sensor in health_sensors[:10]:  # Show first 10
                            print(f"   - {sensor}")
                    else:
                        print("   No health sensors found")
        except:
            print("   Could not check sensors")
        
        # Save configuration
        print("\n💾 Saving configuration...")
        
        # Update .env file
        env_file = ".env"
        env_lines = []
        
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                env_lines = f.readlines()
        
        # Update or add HA settings
        ha_url_set = False
        ha_token_set = False
        
        for i, line in enumerate(env_lines):
            if line.startswith("HOME_ASSISTANT_URL="):
                env_lines[i] = f"HOME_ASSISTANT_URL={ha_url}\n"
                ha_url_set = True
            elif line.startswith("HOME_ASSISTANT_TOKEN="):
                env_lines[i] = f"HOME_ASSISTANT_TOKEN={ha_token}\n"
                ha_token_set = True
        
        if not ha_url_set:
            env_lines.append(f"HOME_ASSISTANT_URL={ha_url}\n")
        if not ha_token_set:
            env_lines.append(f"HOME_ASSISTANT_TOKEN={ha_token}\n")
        
        with open(env_file, 'w') as f:
            f.writelines(env_lines)
        
        print("✅ Configuration saved to .env")
        
        print("\n🎉 Home Assistant integration ready!")
        print("\nWhat you can now do:")
        print("- Ask 'what's next' to see calendar events")
        print("- Say 'remind me to...' to create reminders")
        print("- Get contextual awareness based on your schedule")
        print("- View health data insights")
        print("\nRestart the ADHDo server to use the new integration.")

if __name__ == "__main__":
    asyncio.run(test_home_assistant())