"""
LLM Client for MCP ADHD Server - Local and Cloud routing
"""
import asyncio
import json
import logging
import time
from enum import Enum
from typing import Dict, List, Optional, Any

import httpx
import structlog
from pydantic import BaseModel

from mcp_server.config import settings
from mcp_server.models import MCPFrame, UserState, NudgeTier
from mcp_server.claude_client import claude_client, ClaudeResponse

logger = structlog.get_logger()


class TaskComplexity(Enum):
    """Task complexity levels for routing decisions."""
    SIMPLE = "simple"      # Local only
    MODERATE = "moderate"  # Local preferred  
    COMPLEX = "complex"    # Cloud recommended
    CRISIS = "crisis"      # Hard-coded only


class LLMResponse(BaseModel):
    """Response from LLM with metadata."""
    text: str
    source: str  # "local", "cloud", "hard_coded"
    confidence: float = 1.0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    model_used: str = ""


class OllamaClient:
    """Local LLM client using Ollama with optimization for ADHD use cases."""
    
    def __init__(self, model: str = "deepseek-r1:1.5b"):
        self.model = model
        self.base_url = "http://localhost:11434"
        # Optimized connection settings for ADHD response times (<3s target)
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=5.0),  # Longer timeout for reasoning models
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
            # HTTP/2 disabled for lower latency
            http2=False
        )
        self._cache: Dict[str, LLMResponse] = {}
        self._cache_max_size = 200  # Increased cache size
        self._model_warmed = False
        self._warmup_prompts = [
            "Hi",
            "Ready to help", 
            "Let's focus"
        ]
        
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        max_tokens: int = 40,  # Further reduced for ADHD quick responses
        temperature: float = 0.6  # Lower temp for faster, more focused responses
    ) -> LLMResponse:
        """Generate response using local Ollama model."""
        start_time = time.time()
        
        # Create cache key
        cache_key = f"{hash(prompt)}_{hash(system_prompt or '')}_{max_tokens}_{temperature}"
        
        # Check cache first
        if cache_key in self._cache:
            cached_response = self._cache[cache_key]
            # Return cached response with updated latency
            return LLMResponse(
                text=cached_response.text,
                source="local_cached",
                confidence=cached_response.confidence,
                latency_ms=(time.time() - start_time) * 1000,
                model_used=self.model
            )
        
        try:
            # Warm up model if not done yet
            if not self._model_warmed:
                await self._warmup_model()
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    # Ultra-optimized for sub-3s ADHD responses
                    "top_p": 0.9,     # Slightly more diverse for better responses
                    "top_k": 40,      # Larger search space for reasoning model
                    "repeat_penalty": 1.05,  # Reduce repetition
                    "seed": None,     # Allow variability for better responses
                    "num_ctx": 2048,  # Larger context for reasoning
                    "num_thread": 4,  # Optimize for Raspberry Pi
                    "num_gpu": 0,     # CPU-only for consistency
                    "stop": ["Human:", "User:", "\n\n\n"]  # Allow model to complete reasoning
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract response and clean DeepSeek R1 thinking tags
            raw_content = result["message"]["content"]
            
            # Handle DeepSeek R1 responses with <think> tags
            import re
            
            # First try to get content outside of <think> tags
            clean_content = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL)
            clean_content = clean_content.strip()
            
            # If no content outside think tags, extract from inside (DeepSeek R1 behavior)
            if not clean_content or clean_content == '<think>':
                # DeepSeek R1 may put everything in thinking - extract meaningful parts
                think_match = re.search(r'<think>(.*?)</think>', raw_content, flags=re.DOTALL)
                if think_match:
                    thinking_content = think_match.group(1).strip()
                    
                    # Extract actionable advice from the thinking
                    sentences = [s.strip() for s in thinking_content.split('.') if s.strip()]
                    
                    # Find sentences with actionable words
                    actionable_words = ['start', 'try', 'do', 'create', 'make', 'set', 'organize', 'focus', 'break']
                    actionable_sentences = []
                    
                    for sentence in sentences[:5]:  # Check first 5 sentences
                        if any(word in sentence.lower() for word in actionable_words):
                            actionable_sentences.append(sentence)
                            if len(actionable_sentences) >= 2:  # Max 2 sentences
                                break
                    
                    if actionable_sentences:
                        clean_content = '. '.join(actionable_sentences)
                        if not clean_content.endswith('.'):
                            clean_content += '.'
                    else:
                        # Take first meaningful sentence if no actionable found
                        for sentence in sentences[:3]:
                            if len(sentence) > 20 and not sentence.startswith('Okay') and not sentence.startswith('Well'):
                                clean_content = sentence + '.' if not sentence.endswith('.') else sentence
                                break
                
                elif raw_content.strip() == '<think>':  # Incomplete response
                    clean_content = "Let me break that down for you. What specific part of your morning feels most chaotic?"
            
            # Final fallback if still empty
            if not clean_content:
                clean_content = "I'm here to help! What would you like to work on?"
            
            llm_response = LLMResponse(
                text=clean_content,
                source="local",
                latency_ms=latency_ms,
                model_used=self.model
            )
            
            # Cache the response (if cache not full)
            if len(self._cache) < self._cache_max_size:
                self._cache[cache_key] = llm_response
            
            return llm_response
            
        except Exception as e:
            logger.error("Local LLM generation failed", error=str(e), exc_info=True)
            return LLMResponse(
                text="I'm having trouble thinking right now. Let me try a simpler approach.",
                source="fallback",
                confidence=0.1,
                latency_ms=(time.time() - start_time) * 1000
            )
    
    async def _warmup_model(self) -> None:
        """Warm up the model to reduce cold start latency."""
        try:
            logger.info("Warming up local LLM for faster responses")
            for prompt in self._warmup_prompts:
                await self.client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "options": {
                            "num_predict": 5,  # Very short responses for warmup
                            "temperature": 0.7
                        }
                    }
                )
            self._model_warmed = True
            logger.info("Local LLM warmed up successfully")
        except Exception as e:
            logger.warning("Model warmup failed, continuing anyway", error=str(e))
            self._model_warmed = True  # Don't block on warmup failure
    
    async def prefetch_common_responses(self) -> None:
        """Pre-generate common ADHD responses to cache them."""
        common_adhd_prompts = [
            "I'm struggling to start this task",
            "I'm feeling overwhelmed", 
            "I can't focus right now",
            "I need help breaking this down",
            "Ready to work on email"
        ]
        
        system_prompt = (
            "You are a gentle, encouraging AI assistant helping someone with ADHD. "
            "Keep responses short (1-2 sentences), positive, and actionable."
        )
        
        for prompt in common_adhd_prompts:
            try:
                await self.generate(
                    prompt, 
                    system_prompt=system_prompt,
                    max_tokens=30,
                    temperature=0.8
                )
            except Exception:
                continue  # Skip failed prefetch attempts


class SafetyMonitor:
    """Safety monitor for crisis detection and intervention."""
    
    def __init__(self):
        # Hard-coded crisis patterns (checked first, fastest)
        self.crisis_patterns = [
            r"\b(want to die|kill myself|end it all|suicide|suicidal)\b",
            r"\b(harm myself|hurt myself|self harm)\b", 
            r"\b(no point living|life isn't worth|rather be dead)\b",
            r"\b(can't go on|want to disappear|end the pain)\b"
        ]
        
        # Crisis resources
        self.crisis_resources = {
            "us": {
                "crisis_text": "988",
                "crisis_chat": "suicidepreventionlifeline.org/chat", 
                "emergency": "911"
            }
        }
    
    async def assess_risk(self, text: str, user_state: Optional[UserState] = None) -> Dict[str, Any]:
        """Assess crisis risk in user input."""
        import re
        
        # Quick pattern matching for explicit crisis language
        text_lower = text.lower()
        for pattern in self.crisis_patterns:
            if re.search(pattern, text_lower):
                logger.warning("Crisis pattern detected", pattern=pattern, text=text[:50])
                return {
                    "is_crisis": True,
                    "confidence": 1.0,
                    "crisis_type": "explicit_self_harm",
                    "source": "pattern_match"
                }
        
        # TODO: Add ML-based subtle crisis detection here
        # For now, conservative approach with pattern matching
        
        return {"is_crisis": False}
    
    def get_crisis_response(self, assessment: Dict[str, Any]) -> LLMResponse:
        """Get hard-coded crisis response."""
        return LLMResponse(
            text=(
                "I'm concerned about what you're going through. You don't have to face this alone.\n\n"
                "🆘 **Immediate Support:**\n"
                "• Crisis Text Line: Text HOME to 741741\n" 
                "• National Suicide Prevention Lifeline: 988\n"
                "• Emergency: 911\n\n"
                "These trained counselors are available 24/7 and want to help."
            ),
            source="hard_coded",
            confidence=1.0,
            model_used="safety_override"
        )


class ComplexityClassifier:
    """Classify task complexity for routing decisions."""
    
    def __init__(self):
        # Simple patterns that local LLM handles well
        self.simple_patterns = [
            r"\b(ready to|let's|time for|quick reminder)\b",
            r"\b(how are you|feeling|energy level)\b",
            r"\b(start|begin|do|tackle|work on)\b",
            r"\b(nudge|reminder|check in)\b"
        ]
        
        # Complex patterns that benefit from cloud LLM
        self.complex_patterns = [
            r"\b(help me understand|what does it mean|why do I)\b",
            r"\b(reframe|perspective|look at it differently)\b",
            r"\b(break down|plan|strategy|approach)\b",
            r"\b(feel like|makes me think|reminds me of)\b"
        ]
    
    def assess_complexity(self, text: str, context: Optional[MCPFrame] = None) -> TaskComplexity:
        """Assess task complexity for routing."""
        import re
        
        text_lower = text.lower()
        
        # Check for simple patterns
        simple_matches = sum(1 for pattern in self.simple_patterns 
                           if re.search(pattern, text_lower))
        
        # Check for complex patterns  
        complex_matches = sum(1 for pattern in self.complex_patterns
                            if re.search(pattern, text_lower))
        
        # Length-based heuristics
        word_count = len(text.split())
        
        if simple_matches > 0 and word_count < 20:
            return TaskComplexity.SIMPLE
        elif complex_matches > 0 or word_count > 50:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.MODERATE


class LLMRouter:
    """Main LLM routing system - local first with cloud enhancement."""
    
    def __init__(self):
        self.local_client = OllamaClient("deepseek-r1:1.5b")
        self.claude_client = claude_client
        self.safety_monitor = SafetyMonitor()
        self.complexity_classifier = ComplexityClassifier()
        self.cloud_client = None  # TODO: Add OpenRouter client
        self._initialized = False
        
        # Response templates for ultra-fast responses
        self._quick_responses = {
            "ready": "Let's do this! 💪 What's your first step?",
            "start": "Break it into tiny pieces. Just pick one small thing to begin with.",
            "stuck": "That's totally normal! What's the tiniest action you could take right now?",
            "overwhelmed": "Pause. Breathe. Let's focus on just one thing. What feels most important?",
            "energy_low": "Low energy is OK. What's the easiest task you could tackle?",
            "hyperfocus": "Great focus! Remember to take breaks and hydrate. 🎯"
        }
        
        # ADHD-specific system prompts
        self.adhd_system_prompts = {
            "gentle_nudge": (
                "You are a gentle, encouraging AI assistant helping someone with ADHD. "
                "Keep responses short (1-2 sentences), positive, and actionable. "
                "Use simple language and be specific about next steps."
            ),
            "accountability": (
                "You are a supportive accountability partner for someone with ADHD. "
                "Be direct but kind. Help them recognize patterns and stay on track. "
                "Keep responses brief and focused."
            ),
            "crisis": (
                "SYSTEM OVERRIDE: Crisis response protocols engaged. "
                "Provide immediate support resources only."
            )
        }
    
    async def process_request(
        self,
        user_input: str,
        context: Optional[MCPFrame] = None,
        nudge_tier: NudgeTier = NudgeTier.GENTLE
    ) -> LLMResponse:
        """Main entry point for LLM processing."""
        
        # Initialize if not done yet
        if not self._initialized:
            await self.initialize()
        
        # Step 1: Safety assessment (always first)
        # Extract user state from context if available
        user_state = None
        if context:
            for ctx_item in context.context:
                if ctx_item.type.value == "user_state":
                    user_state = ctx_item.data.get("current_state")
                    break
        
        safety_assessment = await self.safety_monitor.assess_risk(
            user_input, 
            user_state
        )
        
        if safety_assessment["is_crisis"]:
            return self.safety_monitor.get_crisis_response(safety_assessment)
        
        # Step 2: Complexity assessment
        complexity = self.complexity_classifier.assess_complexity(user_input, context)
        
        # Step 3: Route based on complexity
        if complexity == TaskComplexity.SIMPLE:
            return await self._handle_local(user_input, context, nudge_tier)
        elif complexity == TaskComplexity.MODERATE:
            # Try local first, fallback to Claude if available
            local_response = await self._handle_local(user_input, context, nudge_tier)
            
            # If local response is low confidence and Claude is available, use Claude
            if local_response.confidence < 0.7 and self.claude_client.is_available():
                return await self._handle_claude(user_input, context, nudge_tier, 'gentle_nudge')
            
            return local_response
        elif complexity == TaskComplexity.COMPLEX:
            # Use Claude if available, otherwise local with disclaimer
            if self.claude_client.is_available():
                return await self._handle_claude(user_input, context, nudge_tier, 'complex_breakdown')
            else:
                return await self._handle_local_complex(user_input, context, nudge_tier)
    
    async def _handle_local(
        self, 
        user_input: str, 
        context: Optional[MCPFrame],
        nudge_tier: NudgeTier
    ) -> LLMResponse:
        """Handle request with local LLM."""
        
        # Select system prompt based on nudge tier
        if nudge_tier == NudgeTier.GENTLE:
            system_prompt = self.adhd_system_prompts["gentle_nudge"]
        elif nudge_tier in [NudgeTier.SARCASTIC, NudgeTier.SERGEANT]:
            system_prompt = self.adhd_system_prompts["accountability"]
        else:
            system_prompt = self.adhd_system_prompts["gentle_nudge"]
        
        # Add context if available
        if context and context.task_focus:
            context_info = f"\nCurrent focus: {context.task_focus}"
            
            # Extract user state from context
            user_state = None
            for ctx_item in context.context:
                if ctx_item.type.value == "user_state":
                    user_state = ctx_item.data.get("current_state")
                    break
            
            if user_state:
                context_info += f"\nUser state: {user_state}"
            
            system_prompt += context_info
        
        # Check for ultra-quick pattern matches first
        quick_response = self._get_quick_response(user_input)
        if quick_response:
            return LLMResponse(
                text=quick_response,
                source="pattern_match",
                confidence=0.9,
                latency_ms=1.0,  # Near-instant
                model_used="quick_match"
            )
        
        return await self.local_client.generate(
            user_input,
            system_prompt=system_prompt,
            max_tokens=50,  # Shorter responses for speed
            temperature=0.8  # Slightly higher for faster generation
        )
    
    def _get_quick_response(self, user_input: str) -> Optional[str]:
        """Check for patterns that can be answered instantly."""
        text_lower = user_input.lower()
        
        # Expanded ADHD-specific quick response patterns
        if any(phrase in text_lower for phrase in ["ready", "let's go", "time to", "let's do this", "i'm ready"]):
            return self._quick_responses["ready"]
        elif any(phrase in text_lower for phrase in ["stuck", "can't start", "don't know how", "procrastinating", "avoiding"]):
            return self._quick_responses["stuck"]  
        elif any(phrase in text_lower for phrase in ["overwhelmed", "too much", "stressed", "can't cope", "everything at once"]):
            return self._quick_responses["overwhelmed"]
        elif any(phrase in text_lower for phrase in ["tired", "low energy", "exhausted", "drained", "no motivation"]):
            return self._quick_responses["energy_low"]
        elif any(phrase in text_lower for phrase in ["focused", "in the zone", "hyperfocus", "flow state", "concentrating"]):
            return self._quick_responses["hyperfocus"]
        elif any(phrase in text_lower for phrase in ["start", "begin", "first step", "how do i", "where to begin"]):
            return self._quick_responses["start"]
        elif any(phrase in text_lower for phrase in ["hello", "hi", "hey", "good morning", "good afternoon"]):
            return "Hi! I'm here to help you stay focused. What would you like to work on? 🌟"
        elif any(phrase in text_lower for phrase in ["help me focus", "need focus", "can't concentrate", "distracted", "concentrate on"]):
            return "Let's find your focus together. What's one small task you could tackle right now? 🎯"
        elif any(phrase in text_lower for phrase in ["break down", "break it down", "too big", "complex task", "project is", "task is"]):
            return "Perfect instinct! What's the absolute smallest piece of this task? Let's start tiny. 🔍"
            
        return None
    
    async def initialize(self) -> None:
        """Initialize the LLM router with minimal warmup for fast startup."""
        if self._initialized:
            return
            
        try:
            logger.info("Initializing LLM router for ADHD response times")
            
            # Check Ollama availability
            ollama_available = await self.local_client.is_available()
            
            if ollama_available:
                logger.info("✅ Ollama available - local reasoning model ready")
            else:
                logger.info("⚠️ Ollama not available - using pattern matching only")
            
            # Check if Claude is available
            if self.claude_client.is_available():
                logger.info("✅ Claude browser auth available - using for complex tasks")
            else:
                logger.info("ℹ️ Claude not authenticated - local + pattern matching mode")
            
            self._initialized = True
            logger.info("🎯 LLM router initialized - ready for <3s ADHD responses")
            
        except Exception as e:
            logger.error("LLM router initialization failed", error=str(e))
            self._initialized = True  # Continue even if initialization fails
    
    async def _handle_local_complex(
        self,
        user_input: str,
        context: Optional[MCPFrame], 
        nudge_tier: NudgeTier
    ) -> LLMResponse:
        """Handle complex request with local LLM and disclaimer."""
        
        response = await self._handle_local(user_input, context, nudge_tier)
        
        # Add disclaimer for complex requests
        if response.confidence > 0.5:  # Only if we got a reasonable response
            if self.claude_client.is_available():
                response.text += (
                    "\n\n💡 *I can provide more detailed guidance using your Claude Pro subscription if needed.*"
                )
            else:
                response.text += (
                    "\n\n💡 *For more nuanced guidance, connect your Claude Pro account via /api/auth/claude.*"
                )
        
        return response
    
    async def _handle_claude(
        self,
        user_input: str,
        context: Optional[MCPFrame],
        nudge_tier: NudgeTier,
        use_case: str = 'gentle_nudge'
    ) -> LLMResponse:
        """Handle request with Claude using browser auth."""
        
        try:
            # Build system prompt based on nudge tier and context
            system_prompt = None
            if nudge_tier == NudgeTier.GENTLE:
                system_prompt = self.adhd_system_prompts["gentle_nudge"]
            elif nudge_tier in [NudgeTier.SARCASTIC, NudgeTier.SERGEANT]:
                system_prompt = self.adhd_system_prompts["accountability"]
            
            # Add context if available
            if context and context.task_focus:
                context_info = f"\nCurrent focus: {context.task_focus}"
                
                # Extract user state from context
                user_state = None
                for ctx_item in context.context:
                    if ctx_item.type.value == "user_state":
                        user_state = ctx_item.data.get("current_state")
                        break
                
                if user_state:
                    context_info += f"\nUser state: {user_state}"
                
                if system_prompt:
                    system_prompt += context_info
            
            # Generate response with Claude
            claude_response = await self.claude_client.generate_response(
                user_input=user_input,
                system_prompt=system_prompt,
                use_case=use_case,
                max_tokens=150  # ADHD-optimized length
            )
            
            # Convert Claude response to LLMResponse
            return LLMResponse(
                text=claude_response.text,
                source="claude_browser",
                confidence=claude_response.confidence,
                latency_ms=claude_response.latency_ms,
                cost_usd=claude_response.cost_estimate_usd,
                model_used=claude_response.model
            )
            
        except Exception as e:
            logger.error("Claude request failed, falling back to local", error=str(e))
            # Fallback to local LLM
            return await self._handle_local(user_input, context, nudge_tier)


# Global router instance
llm_router = LLMRouter()