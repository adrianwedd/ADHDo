"""
Claude Client for MCP ADHD Server - Browser auth integration for Claude Pro/Max
"""
import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any, Union
import re
from enum import Enum

import httpx
import structlog
from pydantic import BaseModel

from mcp_server.config import settings

logger = structlog.get_logger()


class ClaudeModel(Enum):
    """Available Claude models for different complexity levels."""
    HAIKU = "claude-3-haiku-20240307"          # Fast, simple tasks
    SONNET = "claude-3-sonnet-20240229"       # Balanced speed/quality  
    OPUS = "claude-3-opus-20240229"           # Complex reasoning
    SONNET_4 = "claude-3-5-sonnet-20241022"  # Latest high-quality model


class ClaudeResponse(BaseModel):
    """Response from Claude API with metadata."""
    text: str
    model: str
    usage_tokens: int = 0
    cost_estimate_usd: float = 0.0
    latency_ms: float = 0.0
    confidence: float = 0.9


class ClaudeBrowserSession:
    """Browser-based Claude session using user's Claude Pro/Max subscription."""
    
    def __init__(self, session_token: Optional[str] = None):
        """Initialize Claude browser session."""
        self.session_token = session_token
        self.organization_id: Optional[str] = None
        self.conversation_id: Optional[str] = None
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/event-stream',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        )
        self._authenticated = False
        
        # Cost tracking for Claude Pro/Max usage
        self.usage_stats = {
            'requests_today': 0,
            'tokens_used': 0,
            'last_reset': time.time()
        }
        
    async def authenticate(self, session_token: str) -> bool:
        """Authenticate with Claude using browser session token."""
        try:
            self.session_token = session_token
            
            # Set authentication header
            self.client.headers.update({
                'Cookie': f'sessionKey={session_token}',
                'Authorization': f'Bearer {session_token}'
            })
            
            # Test authentication by getting user info
            response = await self.client.get('https://claude.ai/api/organizations')
            
            if response.status_code == 200:
                orgs = response.json()
                if orgs and len(orgs) > 0:
                    self.organization_id = orgs[0]['uuid']
                    self._authenticated = True
                    logger.info("Claude browser session authenticated", 
                               org_id=self.organization_id[:8] + "...")
                    return True
            
            logger.error("Claude authentication failed", 
                        status=response.status_code,
                        response=response.text[:200])
            return False
            
        except Exception as e:
            logger.error("Claude authentication error", error=str(e))
            return False
    
    async def create_conversation(self, name: str = "ADHD Support Session") -> bool:
        """Create a new conversation for this session."""
        try:
            if not self._authenticated:
                return False
                
            payload = {
                'name': name,
                'summary': 'ADHD executive function support conversation'
            }
            
            response = await self.client.post(
                f'https://claude.ai/api/organizations/{self.organization_id}/chat_conversations',
                json=payload
            )
            
            if response.status_code == 201:
                conv_data = response.json()
                self.conversation_id = conv_data['uuid']
                logger.info("Claude conversation created", 
                           conv_id=self.conversation_id[:8] + "...")
                return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to create Claude conversation", error=str(e))
            return False
    
    async def send_message(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        model: ClaudeModel = ClaudeModel.SONNET,
        max_tokens: int = 200
    ) -> ClaudeResponse:
        """Send message to Claude using browser session."""
        start_time = time.time()
        
        try:
            if not self._authenticated or not self.conversation_id:
                raise Exception("Claude session not authenticated or conversation not created")
            
            # Build message payload
            attachments = []
            
            # Add system prompt as a "context" attachment if provided
            if system_prompt:
                attachments.append({
                    'content': system_prompt,
                    'file_name': 'system_context.txt',
                    'file_type': 'text/plain',
                    'file_size': len(system_prompt)
                })
            
            payload = {
                'completion': {
                    'prompt': message,
                    'timezone': 'America/New_York',
                    'model': model.value
                },
                'organization_uuid': self.organization_id,
                'conversation_uuid': self.conversation_id,
                'text': message,
                'attachments': attachments
            }
            
            # Send message via Claude's chat API
            response = await self.client.post(
                f'https://claude.ai/api/organizations/{self.organization_id}/chat_conversations/{self.conversation_id}/completion',
                json=payload
            )
            
            if response.status_code == 200:
                # Claude returns streaming response, need to parse
                response_text = ""
                
                # Handle streaming response
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])  # Remove "data: " prefix
                            if 'completion' in data:
                                response_text += data['completion']
                            elif 'stop_reason' in data:
                                break
                        except json.JSONDecodeError:
                            continue
                
                # Clean up response
                response_text = self._clean_response(response_text)
                latency_ms = (time.time() - start_time) * 1000
                
                # Update usage stats
                self._update_usage_stats(len(message) + len(response_text or ""))
                
                return ClaudeResponse(
                    text=response_text,
                    model=model.value,
                    usage_tokens=len(message.split()) + len((response_text or "").split()),
                    latency_ms=latency_ms,
                    confidence=0.95  # Claude is generally high confidence
                )
            else:
                raise Exception(f"Claude API error: {response.status_code} - {response.text[:200]}")
                
        except Exception as e:
            logger.error("Claude message failed", error=str(e))
            
            # Return fallback response
            return ClaudeResponse(
                text="I'm having trouble accessing Claude right now. The local system can help with simpler requests.",
                model="fallback",
                latency_ms=(time.time() - start_time) * 1000,
                confidence=0.1
            )
    
    def _clean_response(self, text: str) -> str:
        """Clean up Claude's response text."""
        if not text:
            return "I'm here to help! What would you like to work on?"
        
        # Remove any JSON artifacts or control characters
        text = re.sub(r'[^\x20-\x7E\n\r\t]', '', text)
        
        # Remove duplicate whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Ensure response isn't too long for ADHD users
        if len(text) > 300:
            sentences = text.split('. ')
            if len(sentences) > 1:
                text = '. '.join(sentences[:2]) + '.'
        
        return text
    
    def _update_usage_stats(self, tokens: int):
        """Update usage statistics for rate limiting."""
        now = time.time()
        
        # Reset daily stats if needed
        if now - self.usage_stats['last_reset'] > 24 * 3600:
            self.usage_stats['requests_today'] = 0
            self.usage_stats['tokens_used'] = 0
            self.usage_stats['last_reset'] = now
        
        self.usage_stats['requests_today'] += 1
        self.usage_stats['tokens_used'] += tokens
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        return {
            **self.usage_stats,
            'is_near_limit': self.usage_stats['requests_today'] > 80,  # Conservative limit
            'subscription_type': 'claude_pro'  # Assumed since using browser auth
        }
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class ClaudeClient:
    """High-level Claude client with ADHD-optimized routing."""
    
    def __init__(self):
        """Initialize Claude client."""
        self.browser_session: Optional[ClaudeBrowserSession] = None
        self.authenticated = False
        
        # Model selection for different ADHD use cases
        self.model_routing = {
            'quick_response': ClaudeModel.HAIKU,      # Fast turnaround
            'complex_reasoning': ClaudeModel.SONNET,  # Balanced quality/speed
            'deep_analysis': ClaudeModel.OPUS,        # Thoughtful responses
            'latest': ClaudeModel.SONNET_4            # Best available
        }
        
        # ADHD-specific system prompts optimized for Claude
        self.adhd_prompts = {
            'gentle_nudge': (
                "You are Claude, helping someone with ADHD. Respond with:\n"
                "• 1-2 sentences maximum for quick processing\n"
                "• Specific, actionable next steps\n"
                "• Encouraging but not overwhelming tone\n"
                "• Focus on executive function support\n"
                "• Use clear, simple language"
            ),
            'complex_breakdown': (
                "You are Claude, helping someone with ADHD break down complex tasks. Provide:\n"
                "• Step-by-step breakdown in simple terms\n"
                "• Each step should be 5-15 minutes max\n"
                "• Include transition cues between steps\n"
                "• Acknowledge executive function challenges\n"
                "• Keep total response under 150 words"
            ),
            'pattern_analysis': (
                "You are Claude, analyzing ADHD patterns and behaviors. Provide:\n"
                "• Clear insights without judgment\n"
                "• Practical coping strategies\n"
                "• Recognition of neurodivergent strengths\n"
                "• Actionable accommodation suggestions\n"
                "• Empowering, not pathologizing language"
            )
        }
    
    async def authenticate_with_token(self, session_token: str) -> bool:
        """Authenticate Claude using browser session token."""
        try:
            self.browser_session = ClaudeBrowserSession(session_token)
            
            if await self.browser_session.authenticate(session_token):
                if await self.browser_session.create_conversation("MCP ADHD Support"):
                    self.authenticated = True
                    logger.info("Claude client authenticated successfully")
                    return True
            
            logger.error("Claude client authentication failed")
            return False
            
        except Exception as e:
            logger.error("Claude authentication error", error=str(e))
            return False
    
    async def generate_response(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        use_case: str = 'gentle_nudge',
        max_tokens: int = 200
    ) -> ClaudeResponse:
        """Generate response using Claude with ADHD optimizations."""
        try:
            if not self.authenticated or not self.browser_session:
                raise Exception("Claude not authenticated")
            
            # Select model based on use case
            if use_case in ['quick_response', 'gentle_nudge']:
                model = self.model_routing['quick_response']
                max_tokens = min(max_tokens, 100)  # Keep responses short
            elif use_case == 'complex_breakdown':
                model = self.model_routing['complex_reasoning']
                max_tokens = min(max_tokens, 150)
            elif use_case == 'pattern_analysis':
                model = self.model_routing['deep_analysis']
                max_tokens = min(max_tokens, 200)
            else:
                model = self.model_routing['latest']
            
            # Use appropriate ADHD system prompt
            if not system_prompt and use_case in self.adhd_prompts:
                system_prompt = self.adhd_prompts[use_case]
            
            # Check usage limits
            usage_stats = self.browser_session.get_usage_stats()
            if usage_stats['is_near_limit']:
                logger.warning("Claude usage approaching daily limit")
                # Could switch to local model here
            
            # Send to Claude
            response = await self.browser_session.send_message(
                message=user_input,
                system_prompt=system_prompt,
                model=model,
                max_tokens=max_tokens
            )
            
            logger.info("Claude response generated", 
                       model=model.value,
                       latency=f"{response.latency_ms:.1f}ms",
                       tokens=response.usage_tokens)
            
            return response
            
        except Exception as e:
            logger.error("Claude generation failed", error=str(e))
            
            # Return fallback response
            return ClaudeResponse(
                text="I'm having trouble accessing Claude right now. Let me try helping with the local system.",
                model="fallback",
                confidence=0.1
            )
    
    def is_available(self) -> bool:
        """Check if Claude is available for use."""
        return self.authenticated and self.browser_session is not None
    
    async def close(self):
        """Close Claude client and cleanup resources."""
        if self.browser_session:
            await self.browser_session.close()
        self.authenticated = False


# Global Claude client instance
claude_client = ClaudeClient()