#!/usr/bin/env python3
"""Quick test to send a bedtime nudge."""

import asyncio
import sys
sys.path.append('/home/pi/repos/ADHDo/src')

from mcp_server.nest_nudges import nest_nudge_system, initialize_nest_nudges

async def send_bedtime_nudge():
    """Send a bedtime nudge directly."""
    # Initialize first
    success = await initialize_nest_nudges()
    if not success:
        print("❌ Failed to initialize nest nudge system")
        return
    
    # Get the global instance after initialization
    from mcp_server.nest_nudges import nest_nudge_system, NudgeType
    if not nest_nudge_system:
        print("❌ Nest nudge system not available after initialization")
        return
    
    # Send bedtime nudge
    message = "Hey! It's past 10:30 PM. Time to go to bed. Your ADHD brain needs consistent sleep to function well tomorrow."
    print(f"📢 Sending nudge: {message}")
    
    success = await nest_nudge_system.send_nudge(
        message=message,
        nudge_type=NudgeType.URGENT,
        volume=0.7
    )
    
    if success:
        print("✅ Nudge sent successfully!")
    else:
        print("❌ Failed to send nudge")

if __name__ == "__main__":
    asyncio.run(send_bedtime_nudge())