#!/usr/bin/env python3
"""
Example demonstrating error handling.
"""

import asyncio
import logging
from claude_browser import (
    ClaudeBrowserClient,
    ClaudeAuthenticationError,
    ClaudeTimeoutError,
    ClaudeResponseError
)

# Set up logging
logging.basicConfig(level=logging.INFO)


async def main():
    """Example with comprehensive error handling."""
    
    client = ClaudeBrowserClient(headless=True)
    
    try:
        # Try to initialize
        print("🚀 Attempting to connect to Claude...")
        await client.initialize()
        print("✅ Connected successfully!")
        
        # Send a message with timeout handling
        try:
            response = await client.send_message(
                "What's the weather like?",
                timeout=10  # 10 second timeout
            )
            print(f"Claude: {response}")
            
        except ClaudeTimeoutError:
            print("⏱️ Request timed out - Claude might be slow")
            
        except ClaudeResponseError as e:
            print(f"📝 Failed to get response: {e}")
        
    except ClaudeAuthenticationError as e:
        print(f"🔐 Authentication failed: {e}")
        print("Please check your session cookies are valid")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        
    finally:
        await client.close()
        print("🔒 Cleaned up resources")


if __name__ == "__main__":
    asyncio.run(main())