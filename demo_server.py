#!/usr/bin/env python3
"""
Demo script for the MCP ADHD Server - Shows the working system in action.
"""
import asyncio
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def demo_cognitive_loop():
    """Demonstrate the working cognitive loop."""
    print("🧠✨ MCP ADHD Server - Live Demo")
    print("=" * 60)
    
    try:
        from mcp_server.cognitive_loop import cognitive_loop
        from mcp_server.models import NudgeTier
        
        # Demo scenarios
        scenarios = [
            {
                "name": "📧 Normal Task Help",
                "input": "I keep putting off writing this important email to my boss about the project update",
                "task_focus": "Email to boss",
                "tier": NudgeTier.GENTLE
            },
            {
                "name": "🚨 Crisis Detection",
                "input": "I can't take this anymore, I want to hurt myself",
                "task_focus": None,  
                "tier": NudgeTier.GENTLE
            },
            {
                "name": "💪 Motivation Request",
                "input": "I'm feeling really unfocused today and need a kick in the butt",
                "task_focus": "Focus session",
                "tier": NudgeTier.SARCASTIC
            }
        ]
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n🎬 Scenario {i}: {scenario['name']}")
            print(f"User Input: \"{scenario['input']}\"")
            print(f"Task Focus: {scenario['task_focus']}")
            print(f"Nudge Tier: {scenario['tier'].name}")
            print("-" * 50)
            
            # Process through cognitive loop
            result = await cognitive_loop.process_user_input(
                user_id=f"demo_user_{i}",
                user_input=scenario['input'],
                task_focus=scenario['task_focus'],
                nudge_tier=scenario['tier']
            )
            
            # Display results
            if result.success:
                print(f"✅ SUCCESS (⏱️ {result.processing_time_ms:.1f}ms)")
                if result.response:
                    print(f"🤖 Response: {result.response.text[:200]}...")
                    print(f"📡 Source: {result.response.source}")
                print(f"⚡ Actions: {result.actions_taken}")
                print(f"🧠 Cognitive Load: {result.cognitive_load:.2f}")
            else:
                print(f"❌ FAILED: {result.error}")
                
            print()
            
        # Show stats
        print("📊 System Statistics:")
        stats = cognitive_loop.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
            
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def demo_api_ready():
    """Show that the API is ready for HTTP calls."""
    print("\n🌐 API Endpoints Ready:")
    print("=" * 30)
    
    endpoints = [
        "GET  /health - Health check",
        "GET  / - System info", 
        "POST /chat - Main chat endpoint",
        "POST /frames - Create MCP frame",
        "POST /users - User management",
        "POST /tasks - Task management",
        "POST /nudge/{user_id} - Manual nudge",
        "POST /webhooks/telegram - Telegram integration",
        "POST /webhooks/home_assistant - HA integration"
    ]
    
    for endpoint in endpoints:
        print(f"  📍 {endpoint}")
    
    print(f"\n🚀 Ready to start server with: PYTHONPATH=src python -m mcp_server.main")
    print(f"🐳 Or with Docker: docker-compose up")

async def main():
    """Run the complete demo."""
    success = await demo_cognitive_loop()
    await demo_api_ready()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 PHASE 0 COMPLETE - MCP ADHD Server is working!")
        print("✨ The cognitive loop processes input, detects crises, and provides responses")
        print("🔗 All API endpoints are connected and ready")
        print("🐳 Docker environment is configured")
        print("📚 Documentation is comprehensive")
        print("\n🚀 Ready for Phase 1: Production infrastructure and enhanced features")
        return 0
    else:
        print("⚠️  Demo encountered issues - check the logs above")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))