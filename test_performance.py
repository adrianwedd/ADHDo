#!/usr/bin/env python3
"""
Performance test for MCP ADHD Server optimizations.
"""
import asyncio
import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_performance():
    """Test performance improvements."""
    try:
        from mcp_server.cognitive_loop import cognitive_loop
        from mcp_server.models import NudgeTier
        
        print("⚡ Performance Test - Target: <3s response time")
        print("=" * 60)
        
        test_scenarios = [
            {
                "name": "Quick nudge",
                "input": "I need to start my email",
                "task_focus": "Email task"
            },
            {
                "name": "Focus request", 
                "input": "Help me get focused",
                "task_focus": "Focus session"
            },
            {
                "name": "Same as first (cache test)",
                "input": "I need to start my email", 
                "task_focus": "Email task"
            },
            {
                "name": "Simple check-in",
                "input": "How should I tackle this?",
                "task_focus": "Current task"
            }
        ]
        
        results = []
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n🎯 Test {i}: {scenario['name']}")
            print(f"Input: \"{scenario['input']}\"")
            
            start_time = time.time()
            
            result = await cognitive_loop.process_user_input(
                user_id=f"perf_test_{i}",
                user_input=scenario['input'],
                task_focus=scenario['task_focus'],
                nudge_tier=NudgeTier.GENTLE
            )
            
            end_time = time.time()
            total_time = (end_time - start_time) * 1000  # Convert to ms
            
            print(f"⏱️  Total time: {total_time:.1f}ms")
            print(f"🤖 Response: {result.response.text[:80] if result.response else 'None'}...")
            if result.response:
                print(f"📡 Source: {result.response.source}")
                print(f"🧠 Processing: {result.processing_time_ms:.1f}ms")
            
            results.append({
                'scenario': scenario['name'],
                'total_time_ms': total_time,
                'processing_time_ms': result.processing_time_ms,
                'source': result.response.source if result.response else 'none',
                'success': result.success
            })
            
            # Check if under target
            if total_time < 3000:
                print("✅ UNDER TARGET (<3s)")
            else:
                print("❌ OVER TARGET (>3s)")
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE SUMMARY")
        print("=" * 60)
        
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r['success'])
        under_target = sum(1 for r in results if r['total_time_ms'] < 3000)
        cached_responses = sum(1 for r in results if 'cached' in r['source'])
        
        avg_time = sum(r['total_time_ms'] for r in results) / len(results)
        min_time = min(r['total_time_ms'] for r in results)
        max_time = max(r['total_time_ms'] for r in results)
        
        print(f"🎯 Target achievement: {under_target}/{total_tests} tests under 3s")
        print(f"✅ Success rate: {successful_tests}/{total_tests}")
        print(f"💾 Cache hits: {cached_responses}/{total_tests}")
        print(f"⏱️  Average time: {avg_time:.1f}ms")
        print(f"⚡ Fastest: {min_time:.1f}ms")
        print(f"🐌 Slowest: {max_time:.1f}ms")
        
        # Detailed results
        print(f"\n📋 Detailed Results:")
        for r in results:
            status = "✅" if r['total_time_ms'] < 3000 else "❌"
            print(f"  {status} {r['scenario']}: {r['total_time_ms']:.1f}ms ({r['source']})")
        
        if under_target == total_tests:
            print(f"\n🎉 ALL TESTS PASSED! Performance target achieved!")
            return True
        else:
            print(f"\n⚠️ Performance target not fully achieved. Need more optimization.")
            return False
            
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    success = await test_performance()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))