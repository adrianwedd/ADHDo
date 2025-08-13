#!/usr/bin/env python3
"""
Basic usage example for claude-browser package.
"""

import asyncio
import os
from claude_browser import ClaudeBrowserClient


async def main():
    """Basic example of using Claude Browser Client."""
    
    # Set your authentication (or use environment variables)
    # os.environ['CLAUDE_SESSION_KEY'] = 'your-session-key-here'
    
    # Create client
    client = ClaudeBrowserClient(headless=True)
    
    try:
        # Initialize and connect
        print("🚀 Connecting to Claude...")
        success = await client.initialize()
        
        if not success:
            print("❌ Failed to connect to Claude")
            return
        
        print("✅ Connected to Claude!")
        
        # Send some messages
        messages = [
            "Hello Claude! Please respond with exactly 5 words.",
            "What's 2 + 2?",
            "Tell me a very short joke."
        ]
        
        for message in messages:
            print(f"\n💬 You: {message}")
            response = await client.send_message(message)
            print(f"🤖 Claude: {response}")
            
            # Small delay between messages
            await asyncio.sleep(2)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        # Always clean up
        await client.close()
        print("\n👋 Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())