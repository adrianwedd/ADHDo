#!/usr/bin/env python3
"""
Example using context manager for automatic cleanup.
"""

import asyncio
from claude_browser import ClaudeBrowserClient


async def main():
    """Example using context manager."""
    
    # Context manager handles initialization and cleanup
    async with ClaudeBrowserClient(headless=True) as client:
        print("✅ Connected to Claude!")
        
        # Have a conversation
        response = await client.send_message(
            "I'm learning Python. Give me one tip for writing better code."
        )
        print(f"Claude's tip: {response}")
        
        # Follow-up question
        response = await client.send_message(
            "Can you give an example of that?"
        )
        print(f"Example: {response}")
    
    # Client is automatically closed here
    print("✅ Cleanup complete!")


if __name__ == "__main__":
    asyncio.run(main())