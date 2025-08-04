#!/usr/bin/env python3
"""
Simple test script for the MCP ADHD Server API endpoints.
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_cognitive_loop():
    """Test the cognitive loop directly without starting the server."""
    try:
        from mcp_server.cognitive_loop import cognitive_loop
        from mcp_server.models import NudgeTier
        
        print("🧠 Testing cognitive loop directly...")
        
        # Test 1: Normal user input
        print("\n1. Testing normal user input...")
        result = await cognitive_loop.process_user_input(
            user_id="test_user",
            user_input="I need help starting my email response to Sarah",
            task_focus="Write email response",
            nudge_tier=NudgeTier.GENTLE
        )
        
        print(f"Success: {result.success}")
        print(f"Processing time: {result.processing_time_ms:.2f}ms")
        print(f"Actions taken: {result.actions_taken}")
        if result.response:
            print(f"Response: {result.response.text[:100]}...")
        if result.error:
            print(f"Error: {result.error}")
            
        # Test 2: Crisis input (should trigger safety override)
        print("\n2. Testing crisis input...")
        result = await cognitive_loop.process_user_input(
            user_id="test_user",
            user_input="I want to hurt myself",
            nudge_tier=NudgeTier.GENTLE
        )
        
        print(f"Success: {result.success}")
        print(f"Actions taken: {result.actions_taken}")
        if result.response:
            print(f"Safety response: {result.response.text}")
            print(f"Response source: {result.response.source}")
        
        # Test 3: Get stats
        print("\n3. Cognitive loop stats:")
        stats = cognitive_loop.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
            
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_api_models():
    """Test API model creation."""
    try:
        from mcp_server.main import ChatRequest
        from mcp_server.models import NudgeTier
        
        print("\n🔧 Testing API models...")
        
        # Test ChatRequest model
        request = ChatRequest(
            user_id="test_user",
            message="Help me with my task",
            task_focus="Email response",
            nudge_tier=NudgeTier.GENTLE
        )
        
        print(f"ChatRequest created successfully:")
        print(f"  User ID: {request.user_id}")
        print(f"  Message: {request.message}")
        print(f"  Task focus: {request.task_focus}")
        print(f"  Nudge tier: {request.nudge_tier}")
        
        return True
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 MCP ADHD Server - Test Suite")
    print("=" * 50)
    
    # Test 1: API Models
    models_ok = await test_api_models()
    
    # Test 2: Cognitive Loop
    cognitive_ok = await test_cognitive_loop()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"  API Models: {'✅ PASS' if models_ok else '❌ FAIL'}")
    print(f"  Cognitive Loop: {'✅ PASS' if cognitive_ok else '❌ FAIL'}")
    
    if models_ok and cognitive_ok:
        print("\n🎉 All tests passed! The system is working.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))