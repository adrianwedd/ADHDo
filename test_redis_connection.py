#!/usr/bin/env python3
"""
Test Redis connection and context building.
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_redis_connection():
    """Test direct Redis connection and context building."""
    try:
        from traces.memory import trace_memory
        from frames.builder import frame_builder
        
        print("🔗 Testing Redis connection...")
        
        # Test connection
        await trace_memory.connect()
        print("✅ Connected to Redis successfully!")
        
        # Test storing a trace
        from mcp_server.models import TraceMemory
        test_trace = TraceMemory(
            user_id="test_user",
            event_type="test_connection",
            event_data={"message": "Redis connection test"},
            source="test_script"
        )
        
        await trace_memory.store_trace(test_trace)
        print("✅ Stored test trace successfully!")
        
        # Test building a frame with context
        print("🏗️ Testing context frame building...")
        contextual_frame = await frame_builder.build_frame(
            user_id="test_user",
            agent_id="test_agent",
            task_focus="Test Redis context",
            include_patterns=True
        )
        
        print(f"✅ Built contextual frame:")
        print(f"  Frame ID: {contextual_frame.frame.frame_id}")
        print(f"  Context items: {len(contextual_frame.frame.context)}")
        print(f"  Cognitive load: {contextual_frame.cognitive_load:.2f}")
        print(f"  Accessibility score: {contextual_frame.accessibility_score:.2f}")
        print(f"  Recommended action: {contextual_frame.recommended_action}")
        
        # List context items
        for i, ctx in enumerate(contextual_frame.frame.context):
            print(f"    {i+1}. {ctx.type.value}: {ctx.data}")
        
        # Test retrieving traces
        traces = await trace_memory.get_user_traces("test_user", limit=5)
        print(f"✅ Retrieved {len(traces)} recent traces")
        
        # Cleanup
        await trace_memory.disconnect()
        print("✅ Disconnected from Redis cleanly")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    success = await test_redis_connection()
    if success:
        print("\n🎉 Redis integration is working perfectly!")
        print("🔄 Context building now has persistent memory")
        print("📊 User patterns will be tracked and learned")
        return 0
    else:
        print("\n⚠️ Redis integration has issues - check the errors above")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))