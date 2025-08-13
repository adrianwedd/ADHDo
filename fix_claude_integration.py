#!/usr/bin/env python3
"""
Fix Claude integration in the cognitive loop.
This script ensures Claude is properly initialized and working.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

async def test_claude_integration():
    """Test that Claude is properly integrated in the cognitive loop."""
    
    print("🔧 Testing Claude Integration in Cognitive Loop...")
    
    # Check environment variables
    session_key = os.getenv('CLAUDE_SESSION_KEY')
    if not session_key:
        print("❌ CLAUDE_SESSION_KEY not found in environment")
        print("   Please set it in your .env file")
        return False
    else:
        print(f"✅ CLAUDE_SESSION_KEY found: {session_key[:20]}...")
    
    # Test the Claude browser client directly
    try:
        from mcp_server.claude_browser_working import get_claude_browser
        
        print("\n📡 Initializing Claude browser client...")
        client = await get_claude_browser()
        
        print("🧪 Testing Claude response...")
        response = await client.send_message("Say 'Hello ADHD system' in exactly 3 words")
        print(f"✅ Claude responded: {response}")
        
    except Exception as e:
        print(f"❌ Claude browser test failed: {e}")
        return False
    
    # Test the LLM router with Claude
    try:
        from mcp_server.llm_client import llm_router
        
        print("\n🔄 Testing LLM Router with Claude...")
        await llm_router.initialize()
        
        if llm_router._claude_available:
            print("✅ Claude is available in LLM router")
            
            # Test a simple request
            response = await llm_router.process_request(
                user_input="Hello, I need help focusing",
                context=None
            )
            print(f"✅ LLM Router response via {response.source}: {response.text[:100]}...")
            
        else:
            print("❌ Claude not available in LLM router")
            return False
            
    except Exception as e:
        print(f"❌ LLM router test failed: {e}")
        return False
    
    # Test the cognitive loop
    try:
        from mcp_server.cognitive_loop import CognitiveLoop
        
        print("\n🧠 Testing Cognitive Loop with Claude...")
        loop = CognitiveLoop()
        
        result = await loop.process_user_input(
            user_id="test_user",
            user_input="Help me start working on my project"
        )
        
        if result.success:
            print(f"✅ Cognitive loop success! Source: {result.response.source if result.response else 'N/A'}")
            if result.response:
                print(f"   Response: {result.response.text[:100]}...")
        else:
            print(f"❌ Cognitive loop failed: {result.error}")
            return False
            
    except Exception as e:
        print(f"❌ Cognitive loop test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✨ All tests passed! Claude is integrated in the cognitive loop.")
    return True


async def fix_minimal_main():
    """Update minimal_main.py to load environment variables."""
    
    print("\n🔧 Fixing minimal_main.py to load .env variables...")
    
    minimal_main_path = Path(__file__).parent / "src" / "mcp_server" / "minimal_main.py"
    
    if not minimal_main_path.exists():
        print(f"❌ File not found: {minimal_main_path}")
        return False
    
    content = minimal_main_path.read_text()
    
    # Check if dotenv is already imported
    if "from dotenv import load_dotenv" in content:
        print("✅ dotenv already imported in minimal_main.py")
        return True
    
    # Add dotenv import at the beginning
    lines = content.split('\n')
    
    # Find where to insert (after the imports)
    import_index = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            import_index = i + 1
    
    # Insert dotenv loading
    lines.insert(import_index, "from dotenv import load_dotenv")
    lines.insert(import_index + 1, "load_dotenv()  # Load .env variables including CLAUDE_SESSION_KEY")
    lines.insert(import_index + 2, "")
    
    # Write back
    minimal_main_path.write_text('\n'.join(lines))
    print("✅ Added dotenv loading to minimal_main.py")
    
    return True


async def main():
    """Main function."""
    
    # First fix the server to load env vars
    await fix_minimal_main()
    
    # Then test Claude integration
    success = await test_claude_integration()
    
    if success:
        print("\n🎉 Claude integration is working!")
        print("\n📌 Next steps:")
        print("1. Restart the server to load the .env variables:")
        print("   pkill -f 'python.*minimal_main'")
        print("   PYTHONPATH=/home/pi/repos/ADHDo/src PORT=23444 /home/pi/repos/ADHDo/venv_beta/bin/python -m mcp_server.minimal_main &")
        print("\n2. Test the chat endpoint:")
        print("   curl -X POST http://localhost:23444/chat -H 'Content-Type: application/json' -d '{\"user_id\": \"test\", \"message\": \"Hello Claude!\"}'")
    else:
        print("\n⚠️ Claude integration needs fixing. Check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())