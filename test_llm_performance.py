#!/usr/bin/env python3
"""
Performance test for LLM client optimizations.

Tests cold start time, warm-up effectiveness, and response patterns.
"""
import asyncio
import time
import sys
import os

# Add src to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_server.llm_client import LLMRouter
from mcp_server.models import NudgeTier

async def test_llm_performance():
    """Test LLM performance improvements."""
    
    print("🚀 Testing LLM Performance Optimizations")
    print("=" * 50)
    
    router = LLMRouter()
    
    # Test 1: Cold start performance
    print("\n🥶 Test 1: Cold Start Performance")
    test_prompts = [
        "I'm ready to work",
        "I'm stuck on this task", 
        "Feeling overwhelmed right now",
        "I need help getting started"
    ]
    
    cold_start_times = []
    for prompt in test_prompts:
        start_time = time.time()
        response = await router.process_request(prompt)
        latency = (time.time() - start_time) * 1000
        cold_start_times.append(latency)
        
        print(f"  📝 '{prompt[:30]}...'")
        print(f"     Response: {response.text[:50]}...")
        print(f"     Source: {response.source}")
        print(f"     Latency: {latency:.1f}ms")
        print()
    
    avg_cold_start = sum(cold_start_times) / len(cold_start_times)
    print(f"📊 Average cold start time: {avg_cold_start:.1f}ms")
    
    # Test 2: Warm performance  
    print(f"\n🔥 Test 2: Warm Performance (after initialization)")
    warm_times = []
    for prompt in test_prompts:
        start_time = time.time()
        response = await router.process_request(prompt)
        latency = (time.time() - start_time) * 1000
        warm_times.append(latency)
        
        print(f"  📝 '{prompt[:30]}...'")
        print(f"     Response: {response.text[:50]}...")
        print(f"     Source: {response.source}")
        print(f"     Latency: {latency:.1f}ms")
        print()
    
    avg_warm = sum(warm_times) / len(warm_times)
    print(f"📊 Average warm time: {avg_warm:.1f}ms")
    
    # Test 3: Pattern matching speed
    print(f"\n⚡ Test 3: Pattern Matching Speed")
    pattern_prompts = [
        "I'm ready to tackle this",
        "I'm stuck and don't know how to start",
        "Feeling totally overwhelmed",
        "I'm tired and have low energy"
    ]
    
    pattern_times = []
    for prompt in pattern_prompts:
        start_time = time.time()
        response = await router.process_request(prompt)
        latency = (time.time() - start_time) * 1000
        pattern_times.append(latency)
        
        print(f"  📝 '{prompt}'")
        print(f"     Response: {response.text}")
        print(f"     Source: {response.source}")
        print(f"     Latency: {latency:.1f}ms")
        print()
    
    avg_pattern = sum(pattern_times) / len(pattern_times)
    print(f"📊 Average pattern match time: {avg_pattern:.1f}ms")
    
    # Test 4: Cache effectiveness
    print(f"\n💾 Test 4: Cache Effectiveness")
    repeated_prompt = "I need help starting this email"
    
    # First request (cache miss)
    start_time = time.time()
    first_response = await router.process_request(repeated_prompt)
    first_latency = (time.time() - start_time) * 1000
    
    # Second request (cache hit)
    start_time = time.time()
    second_response = await router.process_request(repeated_prompt)
    second_latency = (time.time() - start_time) * 1000
    
    print(f"  📝 Prompt: '{repeated_prompt}'")
    print(f"     First request: {first_latency:.1f}ms ({first_response.source})")
    print(f"     Second request: {second_latency:.1f}ms ({second_response.source})")
    
    if "cached" in second_response.source:
        cache_speedup = (first_latency - second_latency) / first_latency * 100
        print(f"     Cache speedup: {cache_speedup:.1f}%")
    
    # Summary
    print(f"\n🎯 Performance Summary")
    print("=" * 30)
    print(f"Cold start average: {avg_cold_start:.1f}ms")
    print(f"Warm average: {avg_warm:.1f}ms") 
    print(f"Pattern match average: {avg_pattern:.1f}ms")
    
    target_time = 3000  # 3 seconds
    if avg_warm < target_time:
        print(f"✅ Target <{target_time}ms achieved! ({avg_warm:.1f}ms)")
    else:
        print(f"⚠️  Target <{target_time}ms not reached ({avg_warm:.1f}ms)")
        
    if avg_pattern < 100:
        print("✅ Ultra-fast pattern matching achieved!")
    else:
        print("⚠️  Pattern matching could be faster")

if __name__ == "__main__":
    try:
        asyncio.run(test_llm_performance())
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()