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
        # Keep connection alive to reduce latency
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=2)
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
        max_tokens: int = 75,  # Reduced for faster generation
        temperature: float = 0.7
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
                    # Optimized for speed - ADHD needs quick responses
                    "top_p": 0.9,     # Faster sampling
                    "top_k": 30,      # Smaller search space
                    "repeat_penalty": 1.05,  # Lower penalty for speed
                    "seed": 42,       # Consistent seed for caching
                    "num_ctx": 2048,  # Smaller context window for speed
                    "stop": ["Human:", "User:", "\n\n\n", "\n\n"]
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            latency_ms = (time.time() - start_time) * 1000
            
            llm_response = LLMResponse(
                text=result["message"]["content"].strip(),
                source="local",
                latency_ms=latency_ms,
                model_used=self.model
            )
            
            # Cache the response (if cache not full)
            if len(self._cache) < self._cache_max_size:
                self._cache[cache_key] = llm_response
            
            return llm_response
            
        except Exception as e:
            logger.error("Local LLM generation failed", error=str(e))
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
            # Try local first, could fallback to cloud later
            return await self._handle_local(user_input, context, nudge_tier)
        elif complexity == TaskComplexity.COMPLEX:
            # For now, use local with disclaimer
            # TODO: Add cloud routing with user consent
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
        
        if any(word in text_lower for word in ["ready", "let's go", "time to"]):
            return self._quick_responses["ready"]
        elif any(word in text_lower for word in ["stuck", "can't start", "don't know how"]):
            return self._quick_responses["stuck"]  
        elif any(word in text_lower for word in ["overwhelmed", "too much", "stressed"]):
            return self._quick_responses["overwhelmed"]
        elif any(word in text_lower for word in ["tired", "low energy", "exhausted"]):
            return self._quick_responses["energy_low"]
        elif any(word in text_lower for word in ["focused", "in the zone", "hyperfocus"]):
            return self._quick_responses["hyperfocus"]
        elif any(word in text_lower for word in ["start", "begin", "first step"]):
            return self._quick_responses["start"]
            
        return None
    
    async def initialize(self) -> None:
        """Initialize the LLM router with model warmup and prefetching."""
        if self._initialized:
            return
            
        try:
            logger.info("Initializing LLM router for optimal performance")
            
            # Warm up local model and prefetch common responses
            await asyncio.gather(
                self.local_client._warmup_model(),
                self.local_client.prefetch_common_responses(),
                return_exceptions=True
            )
            
            self._initialized = True
            logger.info("LLM router initialized successfully")
            
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
            response.text += (
                "\n\n💡 *For more nuanced guidance, I could use cloud AI "
                "with your permission (fully anonymized).*"
            )
        
        return response


# Global router instance
llm_router = LLMRouter()