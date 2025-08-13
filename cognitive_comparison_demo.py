#!/usr/bin/env python3
"""
Demonstration comparing old pattern-matching vs new Claude cognitive engine
Shows the difference between "if-else dressed as AI" vs real thinking
"""

import asyncio
import json
import sys
from typing import Dict, Any

sys.path.insert(0, '/home/pi/repos/ADHDo/src')


class OldPatternBasedSystem:
    """The old 'cognitive loop' that was really just pattern matching."""
    
    def process_message(self, message: str) -> Dict[str, Any]:
        """Old system: if-else statements dressed as cognitive processing."""
        
        message_lower = message.lower()
        
        # Pattern matching responses
        if "overwhelmed" in message_lower:
            return {
                "response": "It sounds like you're feeling overwhelmed. Try breaking things into smaller tasks.",
                "thinking": "Pattern matched 'overwhelmed' → standard response #3",
                "actions": [{"type": "suggest_break"}],
                "confidence": 1.0  # Always confident in patterns
            }
        
        elif "focus" in message_lower:
            return {
                "response": "Let's help you focus. I'll start some background music.",
                "thinking": "Pattern matched 'focus' → start music routine",
                "actions": [{"type": "play_music", "params": {"mood": "focus"}}],
                "confidence": 1.0
            }
        
        elif any(word in message_lower for word in ["sitting", "hours", "long time"]):
            return {
                "response": "You should take a movement break.",
                "thinking": "Pattern matched sitting keywords → movement response",
                "actions": [{"type": "movement_reminder"}],
                "confidence": 1.0
            }
        
        else:
            return {
                "response": "I'm here to help with your ADHD management. What's your biggest challenge right now?",
                "thinking": "No patterns matched → generic fallback",
                "actions": [],
                "confidence": 0.5
            }


async def demo_comparison():
    """Compare old pattern matching vs Claude's actual thinking."""
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    COGNITIVE SYSTEM COMPARISON DEMO                         ║
║                                                                              ║
║  OLD SYSTEM: Pattern matching disguised as "cognitive processing"           ║
║  NEW SYSTEM: Claude as actual thinking cognitive engine                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Test messages designed to show the difference
    test_messages = [
        "I've been sitting for 3 hours coding and missed lunch but I'm in flow state",
        "It's 2am and I'm hyperfocused on reorganizing my bookmarks",
        "I have 5 urgent tasks and a meeting in 30 minutes, feeling panicked",
        "My medication wore off and everything feels chaotic",
        "I keep switching between tasks and getting nothing done"
    ]
    
    # Initialize systems
    old_system = OldPatternBasedSystem()
    
    try:
        from mcp_server.claude_cognitive_engine_v2 import get_cognitive_engine_v2
        new_system = get_cognitive_engine_v2()
        claude_available = True
    except ImportError as e:
        print(f"⚠️  Claude system not available: {e}")
        claude_available = False
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{'='*120}")
        print(f"TEST SCENARIO {i}: {message}")
        print(f"{'='*120}")
        
        # Old system response
        print(f"\n🤖 OLD PATTERN-BASED SYSTEM:")
        print(f"{'-'*50}")
        old_result = old_system.process_message(message)
        print(f"Response: {old_result['response']}")
        print(f"Thinking: {old_result['thinking']}")
        print(f"Actions: {[a['type'] for a in old_result['actions']]}")
        print(f"Confidence: {old_result['confidence']:.0%}")
        
        # New system response
        if claude_available:
            print(f"\n🧠 NEW CLAUDE COGNITIVE ENGINE:")
            print(f"{'-'*50}")
            try:
                new_result = await new_system.process(message, f"demo_user_{i}")
                
                print(f"Response: {new_result['response']}")
                
                thinking = new_result.get('thinking', {})
                print(f"Reasoning: {thinking.get('reasoning', 'N/A')}")
                print(f"Confidence: {thinking.get('confidence', 0):.0%}")
                print(f"Patterns detected: {thinking.get('patterns', [])}")
                
                actions = new_result.get('actions_taken', [])
                if actions:
                    print(f"Actions planned:")
                    for action in actions:
                        print(f"  • {action.get('type', 'unknown')}: {action.get('status', '')}")
                
                # Show prediction
                prediction = new_result.get('prediction', {})
                if prediction:
                    print(f"Prediction: {prediction.get('next_need')} in {prediction.get('timeframe_minutes')}min")
                
            except Exception as e:
                print(f"❌ Error with Claude system: {e}")
        
        else:
            print(f"\n🧠 NEW CLAUDE COGNITIVE ENGINE:")
            print(f"{'-'*50}")
            print("(Not available - would provide contextual reasoning)")
        
        print(f"\n💡 THE DIFFERENCE:")
        print(f"   OLD: Simple keyword matching → predefined responses")
        print(f"   NEW: Contextual understanding → reasoned interventions")
        
        # Pause between scenarios
        await asyncio.sleep(2)
    
    print(f"\n{'='*120}")
    print(f"CONCLUSION:")
    print(f"{'='*120}")
    print(f"""
The old system:
• Matches keywords to canned responses
• Always 100% confident (even when wrong)
• One-size-fits-all solutions
• No understanding of context or nuance
• Can't chain multiple tools or adapt to situations

The new Claude system:
• Actually understands the full context
• Reasons about multiple factors (time, energy, medication, patterns)
• Chooses appropriate tools for the specific situation
• Confidence reflects actual certainty
• Can execute complex, multi-step interventions
• Learns patterns and predicts needs

This isn't just a better chatbot - it's a genuine cognitive prosthetic.
    """)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)  # Reduce noise
    
    asyncio.run(demo_comparison())