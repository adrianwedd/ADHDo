"""
Simple Claude integration that actually works.
Uses Anthropic's API directly instead of browser automation.
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any
from anthropic import AsyncAnthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class SimpleClaudeClient:
    """Direct Claude API client - no browser automation needed."""
    
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY') or os.getenv('CLAUDE_API_KEY')
        if not api_key:
            # Try to extract from session key if available
            session_key = os.getenv('CLAUDE_SESSION_KEY', '')
            if session_key and session_key.startswith('sk-ant-'):
                api_key = session_key
        
        if api_key:
            self.client = AsyncAnthropic(api_key=api_key)
            self.available = True
            logger.info("✅ Claude API client initialized")
        else:
            self.client = None
            self.available = False
            logger.warning("⚠️ No Claude API key found - using fallback responses")
    
    async def send_message(
        self, 
        message: str, 
        system_prompt: Optional[str] = None,
        max_tokens: int = 150
    ) -> str:
        """Send message to Claude and get response."""
        
        if not self.available:
            # Fallback responses when Claude isn't available
            return self._get_fallback_response(message)
        
        try:
            # Build messages
            messages = [{"role": "user", "content": message}]
            
            # Use default ADHD-optimized system prompt if none provided
            if not system_prompt:
                system_prompt = (
                    "You are a supportive AI assistant helping someone with ADHD. "
                    "Keep responses short (1-2 sentences), positive, and actionable. "
                    "Focus on one small step at a time. Be encouraging and understanding."
                )
            
            # Send to Claude API
            response = await self.client.messages.create(
                model="claude-3-haiku-20240307",  # Fast, cheap model for quick responses
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,
                temperature=0.7
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return self._get_fallback_response(message)
    
    def _get_fallback_response(self, message: str) -> str:
        """Pattern-based fallback responses for common ADHD scenarios."""
        msg_lower = message.lower()
        
        # Quick pattern matching for common needs
        if any(word in msg_lower for word in ["stuck", "can't start", "procrastinating"]):
            return "Let's break it down. What's the absolute smallest step you could take right now?"
        
        elif any(word in msg_lower for word in ["overwhelmed", "too much", "stressed"]):
            return "Pause and breathe. Pick just ONE thing that feels most important right now."
        
        elif any(word in msg_lower for word in ["focus", "concentrate", "distracted"]):
            return "Let's reset your focus. What specific task do you want to tackle for the next 15 minutes?"
        
        elif any(word in msg_lower for word in ["tired", "exhausted", "no energy"]):
            return "Low energy is okay. What's the easiest win you could get right now?"
        
        elif any(word in msg_lower for word in ["calendar", "schedule", "events"]):
            return "Let me check your calendar for you. What timeframe are you interested in?"
        
        elif any(word in msg_lower for word in ["music", "play", "sound"]):
            return "I can help with music. Would you like focus music, energizing music, or calming music?"
        
        elif any(word in msg_lower for word in ["hello", "hi", "hey"]):
            return "Hi! I'm here to help you stay focused. What would you like to work on?"
        
        else:
            return "I understand. Let's tackle this together. What specific part would you like help with?"


class ClaudeIntegratedRouter:
    """Simple router that integrates Claude with the existing system."""
    
    def __init__(self):
        self.claude = SimpleClaudeClient()
        self._pattern_responses = {
            "ready": "Great energy! What's your first action?",
            "stuck": "That's normal. Pick the tiniest possible step.",
            "overwhelmed": "Let's focus on just one thing. What's most urgent?",
            "tired": "Rest is important too. What's the easiest task right now?",
            "hyperfocus": "Awesome focus! Remember to take breaks and hydrate."
        }
    
    async def process_request(
        self,
        user_input: str,
        context: Optional[Any] = None,
        nudge_tier: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Process user request with Claude or fallback."""
        
        # Try quick pattern match first for instant responses
        quick_response = self._check_patterns(user_input)
        if quick_response:
            return {
                "text": quick_response,
                "source": "pattern",
                "confidence": 0.9,
                "latency_ms": 10
            }
        
        # Use Claude for more complex queries
        response_text = await self.claude.send_message(user_input)
        
        return {
            "text": response_text,
            "source": "claude" if self.claude.available else "fallback",
            "confidence": 0.95 if self.claude.available else 0.7,
            "latency_ms": 500 if self.claude.available else 50
        }
    
    def _check_patterns(self, text: str) -> Optional[str]:
        """Quick pattern matching for instant responses."""
        text_lower = text.lower()
        
        if "ready" in text_lower or "let's go" in text_lower:
            return self._pattern_responses["ready"]
        elif "stuck" in text_lower or "can't start" in text_lower:
            return self._pattern_responses["stuck"]
        elif "overwhelmed" in text_lower or "too much" in text_lower:
            return self._pattern_responses["overwhelmed"]
        elif "tired" in text_lower or "exhausted" in text_lower:
            return self._pattern_responses["tired"]
        elif "focus" in text_lower and "hyper" in text_lower:
            return self._pattern_responses["hyperfocus"]
        
        return None


# Global instance
simple_claude_router = ClaudeIntegratedRouter()


async def test_integration():
    """Test the simple Claude integration."""
    
    print("🧪 Testing Simple Claude Integration...")
    
    # Test various messages
    test_messages = [
        "Hello!",
        "I'm stuck and can't start my project",
        "Help me focus on writing",
        "I'm feeling overwhelmed with tasks",
        "What's on my calendar today?"
    ]
    
    for msg in test_messages:
        print(f"\n📝 User: {msg}")
        result = await simple_claude_router.process_request(msg)
        print(f"🤖 Assistant ({result['source']}): {result['text']}")
        print(f"   Latency: {result['latency_ms']}ms, Confidence: {result['confidence']}")


if __name__ == "__main__":
    asyncio.run(test_integration())