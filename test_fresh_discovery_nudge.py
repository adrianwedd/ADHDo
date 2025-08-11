#!/usr/bin/env python3
"""
Test the fresh discovery nudge approach directly.
This mimics the API call but runs outside of the FastAPI context.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from mcp_server.nest_nudges import NestNudgeSystem
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_fresh_discovery_nudge():
    """Test the fresh discovery nudge method."""
    print("🧪 Testing fresh discovery nudge approach...")
    
    # Create nudge system
    nudge_system = NestNudgeSystem()
    
    # Test with a simple message
    test_message = "Testing fresh discovery approach from API context"
    
    print(f"📢 Sending nudge: '{test_message}'")
    
    # Send nudge using the fresh discovery approach
    success = await nudge_system.send_nudge(
        message=test_message,
        volume=0.6
    )
    
    if success:
        print("✅ Fresh discovery nudge succeeded!")
        return True
    else:
        print("❌ Fresh discovery nudge failed!")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_fresh_discovery_nudge())
    sys.exit(0 if success else 1)