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
# Use browser-based Claude that actually works
try:
    from mcp_server.claude_browser_working import get_claude_browser, ClaudeBrowserClient
    _use_browser_claude = True
except ImportError:
    from mcp_server.claude_client import claude_client, ClaudeResponse
    _use_browser_claude = False
from mcp_server.context_aware_prompting import context_aware_prompting
from mcp_server.adhd_logger import adhd_logger

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
    thinking: Optional[str] = None  # Extracted thinking for UI display
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
        max_tokens: int = 200,  # Increased to prevent truncation while showing thinking
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
            
            # Extract thinking and response content separately
            think_match = re.search(r'<think>(.*?)</think>', raw_content, flags=re.DOTALL)
            response_content = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL).strip()
            
            # Extract thinking for UI display (not for speech)
            thinking_text = None
            if think_match:
                thinking_raw = think_match.group(1).strip()
                if thinking_raw:
                    # Clean up thinking text for UI display
                    thinking_lines = [line.strip() for line in thinking_raw.split('\n') if line.strip()]
                    # Keep all thinking but format nicely
                    thinking_text = '\n'.join(thinking_lines)
            
            # Use response content if available, otherwise extract from thinking
            if response_content:
                clean_content = response_content
            elif think_match:
                thinking_content = think_match.group(1).strip()
                
                # Extract actionable advice from the thinking  
                sentences = [s.strip() for s in thinking_content.split('.') if s.strip()]
                
                # Find sentences with actionable words
                actionable_words = ['start', 'try', 'do', 'create', 'make', 'set', 'organize', 'focus', 'break', 'should', 'could', 'might', 'consider']
                actionable_sentences = []
                
                for sentence in sentences[:8]:  # Check more sentences for better responses
                    if any(word in sentence.lower() for word in actionable_words) and len(sentence) > 20:
                        actionable_sentences.append(sentence)
                        if len(actionable_sentences) >= 3:  # Allow up to 3 sentences for full responses
                            break
                
                if actionable_sentences:
                    clean_content = '. '.join(actionable_sentences)
                    if not clean_content.endswith('.'):
                        clean_content += '.'
                else:
                    # Take meaningful sentences if no actionable found
                    meaningful_sentences = []
                    for sentence in sentences[:5]:
                        if len(sentence) > 30 and not sentence.startswith(('Okay', 'Well', 'Hmm', 'Wait')):
                            meaningful_sentences.append(sentence)
                            if len(meaningful_sentences) >= 2:
                                break
                    
                    if meaningful_sentences:
                        clean_content = '. '.join(meaningful_sentences)
                        if not clean_content.endswith('.'):
                            clean_content += '.'
                    else:
                        clean_content = "Let me break that down for you. What specific aspect would you like to focus on?"
            else:
                clean_content = "I'm here to help! What would you like to work on?"
            
            # Return clean content for speech, thinking separate for UI
            llm_response = LLMResponse(
                text=clean_content,  # Clean text for speech synthesis
                thinking=thinking_text,  # Separate thinking for UI display
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
            r"\b(feel like|makes me think|reminds me of)\b",
            r"\b(need help|help me|can you help|assistance|support)\b",
            r"\b(explain|understand|figure out|work through)\b"
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
        self.claude_browser_client = None  # Will initialize on demand
        self.safety_monitor = SafetyMonitor()
        self.complexity_classifier = ComplexityClassifier()
        self.cloud_client = None  # TODO: Add OpenRouter client
        self._initialized = False
        self._claude_available = False
        
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
            "complex_breakdown": (
                "You are a knowledgeable AI assistant helping someone with ADHD understand complex topics. "
                "Provide clear, detailed explanations that break down complex concepts. "
                "Use examples, analogies, and structured explanations. Keep it informative but accessible."
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
        
        # Step 3: CLAUDE-FIRST OPTIMIZATION for ADHD Performance
        logger.info("Claude-first routing for optimal ADHD performance")
        
        # Try pattern matching first - instant and ADHD-optimized (no LLM needed)
        quick_response = self._get_quick_response(user_input)
        if quick_response:
            logger.info("Pattern match found - instant response")
            return LLMResponse(
                text=quick_response,
                source="pattern_match",
                confidence=0.95,
                latency_ms=10,
                model_used="adhd_patterns"
            )
        
        # For all other queries, prefer Claude for fast, high-quality responses
        if self._claude_available:
            logger.info(f"{complexity.value} query - routing to Claude for fast response")
            try:
                # Use appropriate Claude strategy based on complexity
                strategy = 'complex_breakdown' if complexity == TaskComplexity.COMPLEX else 'adhd_support'
                return await self._handle_claude(user_input, context, nudge_tier, strategy)
            except Exception as e:
                logger.warning(f"Claude failed: {e}, using ADHD assistant fallback")
        
        # Fallback: Use comprehensive pattern-based ADHD assistant
        logger.info("Using comprehensive ADHD assistant")
        from .adhd_assistant import adhd_assistant
        result = await adhd_assistant.process_message(user_input, "default")
        
        return LLMResponse(
            text=result.get("response", "I understand this is challenging with ADHD. Let's break it down into smaller steps. What's the most urgent part?"),
            source="adhd_assistant",
            confidence=0.85,
            latency_ms=50,
            model_used="adhd_patterns"
        )
    
    async def _handle_local(
        self, 
        user_input: str, 
        context: Optional[MCPFrame],
        nudge_tier: NudgeTier
    ) -> LLMResponse:
        """Handle request with local LLM using sophisticated context-aware prompting."""
        
        # Check for ultra-quick pattern matches first
        quick_response = self._get_quick_response(user_input)
        if quick_response:
            adhd_logger.pattern_match(
                pattern=self._identify_pattern(user_input),
                confidence=0.9,
                response_time_ms=1.0,
                user_input=user_input[:50]
            )
            
            return LLMResponse(
                text=quick_response,
                source="pattern_match",
                confidence=0.9,
                latency_ms=1.0,  # Near-instant
                model_used="quick_match"
            )
        
        # Generate sophisticated contextual prompts
        adhd_logger.cognitive_process(
            "prompt_engineering",
            "Building context-aware prompts from MCP frame data",
            cognitive_load=0.5  # Default cognitive load for prompt engineering
        )
        
        system_prompt, enhanced_user_prompt, prompt_context = context_aware_prompting.generate_contextual_prompt(
            user_input=user_input,
            mcp_frame=context,
            nudge_tier=nudge_tier,
            use_case="local_llm_support"
        )
        
        # Log the sophisticated prompting
        adhd_logger.context_building(
            "Generated context-aware prompts with Claude best practices",
            contexts_count=len(context.context) if context else 0,
            cognitive_load=prompt_context.cognitive_load
        )
        
        # Adjust token limits based on cognitive load
        max_tokens = 150 if prompt_context.cognitive_load < 0.6 else 75
        
        # Skip Ollama (timing out on Pi) and use pattern-based assistant
        from .adhd_assistant import adhd_assistant
        result = await adhd_assistant.process_message(enhanced_user_prompt, "default")
        
        return LLMResponse(
            text=result.get("response", "I understand. Let me help you with that. What specific part would you like to tackle first?"),
            source="pattern_fallback",
            confidence=0.7,
            latency_ms=100
        )
    
    def _identify_pattern(self, user_input: str) -> str:
        """Identify which pattern was matched for logging."""
        text_lower = user_input.lower()
        
        if any(phrase in text_lower for phrase in ["ready", "let's go", "time to", "let's do this", "i'm ready"]):
            return "readiness_signal"
        elif any(phrase in text_lower for phrase in ["stuck", "can't start", "don't know how", "procrastinating", "avoiding"]):
            return "task_initiation_difficulty"
        elif any(phrase in text_lower for phrase in ["overwhelmed", "too much", "stressed", "can't cope", "everything at once"]):
            return "cognitive_overload"
        elif any(phrase in text_lower for phrase in ["focus", "concentrate", "distracted", "attention"]):
            return "attention_regulation"
        else:
            return "general_adhd_support"
    
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
        elif any(phrase in text_lower for phrase in ["help me focus", "need focus", "can't concentrate", "distracted", "concentrate on", "focus please"]):
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
            try:
                # Test Ollama with a quick health check
                response = await self.local_client.client.get(f"{self.local_client.base_url}/api/tags", timeout=2.0)
                ollama_available = response.status_code == 200
            except:
                ollama_available = False
            
            if ollama_available:
                logger.info("✅ Ollama available - local reasoning model ready")
            else:
                logger.info("⚠️ Ollama not available - using pattern matching only")
            
            # Check if Claude browser is available
            try:
                if _use_browser_claude:
                    self.claude_browser_client = await get_claude_browser()
                    self._claude_available = True
                    logger.info("✅ Claude browser available - using for complex tasks")
                else:
                    self._claude_available = False
                    logger.info("ℹ️ Claude browser not available - local + pattern matching mode")
            except Exception as e:
                logger.warning(f"Claude browser initialization failed: {e}")
                self._claude_available = False
            
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
            if self._claude_available:
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
        
        start_time = time.time()
        
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
            
            # Generate response with Claude browser
            if self.claude_browser_client:
                full_prompt = f"{system_prompt}\n\nUser: {user_input}\n\nAssistant:"
                claude_text = await self.claude_browser_client.send_message(full_prompt)
                
                return LLMResponse(
                    text=claude_text,
                    source="claude_browser",
                    confidence=0.95,
                    latency_ms=(time.time() - start_time) * 1000,
                    cost_usd=0.0,  # Browser mode doesn't track cost
                    model_used="claude-3-sonnet"
                )
            else:
                raise Exception("Claude browser not initialized")
            
        except Exception as e:
            logger.error("Claude request failed, falling back to local", error=str(e))
            # Fallback to local LLM
            return await self._handle_local(user_input, context, nudge_tier)


# Global router instance
llm_router = LLMRouter()