#!/usr/bin/env python3
"""Test Nest nudge system with wait for device discovery."""
import asyncio
import sys
sys.path.insert(0, 'src')

from mcp_server.nest_nudges import NestNudgeSystem

async def test_nudges_with_wait():
    print("🔔 Testing Nest nudge system with background discovery...")
    
    nudge_system = NestNudgeSystem()
    success = await nudge_system.initialize()
    
    if success:
        print("✅ Nudge system initialized!")
        
        # Wait for background device discovery
        print("⏳ Waiting for device discovery (up to 30 seconds)...")
        for i in range(30):
            await asyncio.sleep(1)
            if nudge_system.devices:
                print(f"✅ Found {len(nudge_system.devices)} devices after {i+1} seconds!")
                break
            if i % 5 == 4:
                print(f"   Still searching... ({i+1}/30 seconds)")
        
        if nudge_system.devices:
            print("📱 Available devices:")
            for device in nudge_system.devices:
                print(f"   - {device.name} ({device.model_name})")
            
            # Test sending a nudge
            print("\n🎯 Testing nudge delivery...")
            result = await nudge_system.send_nudge(
                "This is a test nudge from your ADHD system! Testing, testing, one two three.",
                volume=0.3
            )
            
            if result:
                print("✅ Test nudge sent successfully!")
            else:
                print("❌ Nudge failed")
        else:
            print("❌ No devices found after waiting")
            
        await nudge_system.cleanup()
    else:
        print("❌ System initialization failed")

if __name__ == "__main__":
    asyncio.run(test_nudges_with_wait())