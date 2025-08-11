#!/usr/bin/env python3
"""Test Nest nudge system."""
import asyncio
import sys
sys.path.insert(0, 'src')

from mcp_server.nest_nudges import NestNudgeSystem

async def test_nudges():
    print("🔔 Testing Nest nudge system...")
    
    nudge_system = NestNudgeSystem()
    success = await nudge_system.initialize()
    
    if success:
        print("✅ Nudge system initialized!")
        print(f"Found {len(nudge_system.devices)} Nest devices")
        
        # Test sending a simple nudge
        result = await nudge_system.send_nudge(
            "This is a test nudge from your ADHD system!",
            volume=0.4
        )
        
        if result:
            print("✅ Test nudge sent!")
        else:
            print("❌ Nudge failed")
            
        await nudge_system.cleanup()
    else:
        print("❌ No Nest devices found")

if __name__ == "__main__":
    asyncio.run(test_nudges())