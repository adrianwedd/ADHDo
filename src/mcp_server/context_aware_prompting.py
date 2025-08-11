"""
Context-Aware Prompting System for MCP ADHD Server

This module implements sophisticated prompt engineering that leverages the full
MCP contextual framework. Instead of basic system prompts, it creates dynamic,
contextually-aware prompts that adapt to the user's cognitive state, environment,
task context, memory patterns, and personal history.

Key Features:
- Dynamic prompt assembly based on MCP frame data
- Cognitive load-aware prompt optimization
- Memory pattern integration for personalization
- Environmental context inclusion
- ADHD-specific prompt engineering patterns
- Multi-modal context synthesis
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import structlog

from mcp_server.models import MCPFrame, FrameContext, ContextType, NudgeTier, UserState

logger = structlog.get_logger()


@dataclass
class PromptContext:
    """Rich context for prompt generation."""
    cognitive_load: float
    user_energy: Optional[str] = None
    mood: Optional[str] = None
    focus_level: Optional[str] = None
    time_of_day: Optional[str] = None
    task_complexity: Optional[str] = None
    recent_patterns: List[str] = None
    environmental_factors: Dict[str, Any] = None
    memory_insights: List[str] = None
    achievement_context: List[str] = None


class ContextAwarePromptEngine:
    """
    Advanced prompt engineering system that leverages MCP contextual data.
    
    This replaces basic system prompts with dynamic, contextually-aware prompts
    that adapt to the user's full cognitive and environmental state.
    """
    
    def __init__(self):
        self.prompt_templates = self._initialize_prompt_templates()
        self.context_synthesizers = self._initialize_context_synthesizers()
        self.cognitive_load_adapters = self._initialize_cognitive_adapters()
        
    def generate_contextual_prompt(
        self,
        user_input: str,
        mcp_frame: Optional[MCPFrame],
        nudge_tier: NudgeTier,
        use_case: str = "general_support"
    ) -> Tuple[str, str, PromptContext]:
        """
        Generate sophisticated contextually-aware system and user prompts.
        
        Returns:
            Tuple of (system_prompt, enhanced_user_prompt, context_used)
        """
        
        # Step 1: Extract and synthesize context from MCP frame
        prompt_context = self._extract_prompt_context(mcp_frame)
        
        # Step 2: Build cognitive load-appropriate system prompt
        system_prompt = self._build_system_prompt(
            nudge_tier, use_case, prompt_context
        )
        
        # Step 3: Enhance user input with contextual framing
        enhanced_user_prompt = self._enhance_user_input(
            user_input, prompt_context, mcp_frame
        )
        
        logger.info(
            "Generated contextual prompt",
            cognitive_load=prompt_context.cognitive_load,
            user_energy=prompt_context.user_energy,
            context_items=len(mcp_frame.context) if mcp_frame else 0,
            use_case=use_case
        )
        
        return system_prompt, enhanced_user_prompt, prompt_context
    
    def _extract_prompt_context(self, mcp_frame: Optional[MCPFrame]) -> PromptContext:
        """Extract rich context from MCP frame for prompt engineering."""
        
        if not mcp_frame:
            return PromptContext(cognitive_load=0.5)
        
        context = PromptContext(cognitive_load=0.5)
        
        # Process each context item in the frame
        for ctx_item in mcp_frame.context:
            self._process_context_item(ctx_item, context)
        
        # Add temporal context
        current_hour = datetime.now().hour
        if current_hour < 10:
            context.time_of_day = "morning"
        elif current_hour < 14:
            context.time_of_day = "midday" 
        elif current_hour < 18:
            context.time_of_day = "afternoon"
        else:
            context.time_of_day = "evening"
        
        return context
    
    def _process_context_item(self, ctx_item: FrameContext, context: PromptContext):
        """Process individual context items from MCP frame."""
        
        if ctx_item.type == ContextType.USER_STATE:
            data = ctx_item.data
            context.user_energy = data.get("energy_level", "unknown")
            context.mood = data.get("mood", "neutral")
            context.focus_level = data.get("focus_level", "partial")
            
            # Calculate cognitive load from user state
            energy_map = {"high": 0.3, "medium": 0.5, "low": 0.8}
            focus_map = {"sharp": 0.2, "partial": 0.5, "scattered": 0.8}
            mood_map = {"happy": 0.3, "neutral": 0.5, "anxious": 0.7, "overwhelmed": 0.9}
            
            energy_load = energy_map.get(context.user_energy, 0.5)
            focus_load = focus_map.get(context.focus_level, 0.5)
            mood_load = mood_map.get(context.mood, 0.5)
            
            context.cognitive_load = (energy_load + focus_load + mood_load) / 3
            
        elif ctx_item.type == ContextType.TASK:
            data = ctx_item.data
            context.task_complexity = data.get("complexity", "unknown")
            
        elif ctx_item.type == ContextType.MEMORY_TRACE:
            data = ctx_item.data
            if context.recent_patterns is None:
                context.recent_patterns = []
            
            pattern = data.get("pattern", "")
            if pattern:
                context.recent_patterns.append(pattern)
                
            if context.memory_insights is None:
                context.memory_insights = []
                
            insight = data.get("insight", "")
            if insight:
                context.memory_insights.append(insight)
        
        elif ctx_item.type == ContextType.ENVIRONMENT:
            if context.environmental_factors is None:
                context.environmental_factors = {}
            context.environmental_factors.update(ctx_item.data)
            
        elif ctx_item.type == ContextType.ACHIEVEMENT:
            if context.achievement_context is None:
                context.achievement_context = []
            
            achievement = ctx_item.data.get("description", "")
            if achievement:
                context.achievement_context.append(achievement)
    
    def _build_system_prompt(
        self, 
        nudge_tier: NudgeTier, 
        use_case: str, 
        context: PromptContext
    ) -> str:
        """Build sophisticated system prompt based on full context."""
        
        # Base prompt foundation
        base_prompt = self._get_base_prompt(nudge_tier, use_case)
        
        # Cognitive load adaptation
        cognitive_adaptation = self._adapt_for_cognitive_load(context.cognitive_load)
        
        # User state contextualization
        state_context = self._build_user_state_context(context)
        
        # Memory pattern integration
        memory_context = self._build_memory_context(context)
        
        # Environmental awareness
        env_context = self._build_environmental_context(context)
        
        # Achievement reinforcement
        achievement_context = self._build_achievement_context(context)
        
        # Temporal awareness
        temporal_context = self._build_temporal_context(context)
        
        # Assemble comprehensive system prompt
        system_prompt = f"""{base_prompt}

## Current Context Analysis
{state_context}

## Cognitive Load Optimization
{cognitive_adaptation}

## Memory Pattern Awareness
{memory_context}

## Environmental Factors
{env_context}

## Recent Achievements
{achievement_context}

## Temporal Context
{temporal_context}

## Response Guidelines
- Keep responses concise (max 150 characters for high cognitive load)
- Use encouraging, ADHD-affirming language
- Reference specific context when relevant
- Suggest concrete, actionable next steps
- Acknowledge the user's current state empathetically
"""
        
        return system_prompt
    
    def _get_base_prompt(self, nudge_tier: NudgeTier, use_case: str) -> str:
        """Get base prompt template based on nudge tier and use case."""
        
        tier_prompts = {
            NudgeTier.GENTLE: """You are a supportive AI assistant specialized in ADHD executive function support. Your role is to provide gentle, encouraging guidance that works with ADHD brain patterns rather than against them. You understand that ADHD is a neurological difference, not a deficiency, and you help users leverage their unique cognitive strengths.""",
            
            NudgeTier.SARCASTIC: """You are an accountability buddy AI with a caring but direct communication style. You use gentle sarcasm and playful challenges to help users push through avoidance and procrastination. Your sarcasm is always loving and supportive - like a good friend who calls you out because they care about your success.""",
            
            NudgeTier.SERGEANT: """You are a firm but caring AI coach focused on helping users break through significant procrastination or avoidance. You use authoritative language and direct challenges while remaining fundamentally supportive. Your goal is to create urgency and momentum when gentler approaches haven't worked."""
        }
        
        return tier_prompts.get(nudge_tier, tier_prompts[NudgeTier.GENTLE])
    
    def _adapt_for_cognitive_load(self, cognitive_load: float) -> str:
        """Adapt response style based on cognitive load."""
        
        if cognitive_load > 0.8:
            return """HIGH COGNITIVE LOAD DETECTED:
- Use extremely simple language and short sentences
- Limit to 1-2 concrete suggestions maximum
- Avoid complex explanations or multiple options
- Focus on immediate, achievable actions
- Validate feelings without adding complexity"""
        
        elif cognitive_load > 0.6:
            return """MODERATE COGNITIVE LOAD:
- Keep responses focused and structured
- Use bullet points or numbered lists when helpful
- Limit to 2-3 suggestions
- Prioritize actionable advice over theory
- Include gentle encouragement"""
        
        else:
            return """LOW COGNITIVE LOAD - OPTIMAL PROCESSING:
- Can handle more detailed responses
- Can present multiple options if relevant
- Can include brief explanations of reasoning
- Can explore creative solutions
- Good opportunity for skill building"""
    
    def _build_user_state_context(self, context: PromptContext) -> str:
        """Build user state context section."""
        
        parts = []
        
        if context.user_energy:
            energy_insights = {
                "low": "User has low energy - suggest gentle, low-activation tasks",
                "medium": "User has moderate energy - balance challenge with support",
                "high": "User is energized - good time for challenging tasks"
            }
            parts.append(energy_insights.get(context.user_energy, ""))
        
        if context.mood:
            mood_insights = {
                "anxious": "User feeling anxious - focus on calming, grounding responses",
                "overwhelmed": "User is overwhelmed - break things down into smallest possible steps",
                "frustrated": "User is frustrated - acknowledge difficulties and offer perspective",
                "focused": "User is in good focus state - maintain momentum",
                "scattered": "User feels scattered - help with prioritization and focus"
            }
            parts.append(mood_insights.get(context.mood, ""))
        
        if context.focus_level:
            focus_insights = {
                "sharp": "User has good focus - can handle complex tasks",
                "partial": "User has some focus but may need structure",
                "scattered": "User's attention is scattered - keep responses very simple"
            }
            parts.append(focus_insights.get(context.focus_level, ""))
        
        return "\n".join(f"- {part}" for part in parts if part)
    
    def _build_memory_context(self, context: PromptContext) -> str:
        """Build memory pattern context."""
        
        parts = []
        
        if context.recent_patterns:
            parts.append("RECENT PATTERNS:")
            for pattern in context.recent_patterns[-3:]:  # Last 3 patterns
                parts.append(f"- {pattern}")
        
        if context.memory_insights:
            parts.append("MEMORY INSIGHTS:")
            for insight in context.memory_insights[-2:]:  # Last 2 insights
                parts.append(f"- {insight}")
        
        return "\n".join(parts) if parts else "No significant recent patterns identified."
    
    def _build_environmental_context(self, context: PromptContext) -> str:
        """Build environmental context."""
        
        if not context.environmental_factors:
            return "Environmental context not available."
        
        parts = []
        env = context.environmental_factors
        
        if "distractions" in env:
            distraction_level = env["distractions"]
            if distraction_level == "high":
                parts.append("High distraction environment - suggest focus strategies")
            elif distraction_level == "low":
                parts.append("Low distraction environment - good for deep work")
        
        if "music" in env:
            if env["music"] == "off":
                parts.append("No background music - consider suggesting focus music if appropriate")
            else:
                parts.append(f"Music playing: {env['music']} - factor into focus recommendations")
        
        return "\n".join(f"- {part}" for part in parts) if parts else "Environmental factors optimal."
    
    def _build_achievement_context(self, context: PromptContext) -> str:
        """Build achievement context for motivation."""
        
        if not context.achievement_context:
            return "Look for opportunities to acknowledge any progress or effort."
        
        parts = ["RECENT ACHIEVEMENTS TO REFERENCE:"]
        for achievement in context.achievement_context[-3:]:  # Last 3 achievements
            parts.append(f"- {achievement}")
        
        parts.append("Use these achievements to reinforce capability and build momentum.")
        
        return "\n".join(parts)
    
    def _build_temporal_context(self, context: PromptContext) -> str:
        """Build temporal awareness context."""
        
        if not context.time_of_day:
            return "Time context not available."
        
        time_insights = {
            "morning": "Morning energy patterns - may be optimal for planning and prioritization",
            "midday": "Midday period - good for sustained work, but watch for post-lunch dips",
            "afternoon": "Afternoon energy - may need motivation boost or task switching",
            "evening": "Evening period - good for reflection, lighter tasks, and preparation"
        }
        
        return time_insights.get(context.time_of_day, "")
    
    def _enhance_user_input(
        self, 
        user_input: str, 
        context: PromptContext, 
        mcp_frame: Optional[MCPFrame]
    ) -> str:
        """Enhance user input with contextual framing."""
        
        # Start with original input
        enhanced_input = user_input
        
        # Add contextual framing
        context_frame = []
        
        if mcp_frame and mcp_frame.task_focus:
            context_frame.append(f"Current task focus: {mcp_frame.task_focus}")
        
        if context.user_energy and context.mood:
            context_frame.append(f"User state: {context.user_energy} energy, {context.mood} mood")
        
        if context.recent_patterns:
            recent_pattern = context.recent_patterns[-1]  # Most recent
            context_frame.append(f"Recent pattern: {recent_pattern}")
        
        # Add context frame if we have meaningful context
        if context_frame:
            context_section = "\n\nContextual Information:\n" + "\n".join(f"- {item}" for item in context_frame)
            enhanced_input += context_section
        
        return enhanced_input
    
    def _initialize_prompt_templates(self) -> Dict[str, Dict[str, str]]:
        """Initialize prompt templates by category."""
        return {
            "task_breakdown": {
                "high_complexity": "This appears to be a complex, multi-step task that may benefit from decomposition...",
                "medium_complexity": "This task has several components that we can organize...",
                "low_complexity": "This is a straightforward task we can tackle directly..."
            },
            "motivation": {
                "low_energy": "When energy is low, the key is finding the smallest possible starting point...",
                "medium_energy": "With moderate energy, we can build momentum strategically...",
                "high_energy": "Great energy levels! Let's channel this into focused action..."
            },
            "focus": {
                "scattered": "When attention feels scattered, external structure becomes crucial...",
                "partial": "With partial focus, we can work with your attention patterns...",
                "sharp": "Your focus is good right now - let's make the most of it..."
            }
        }
    
    def _initialize_context_synthesizers(self) -> Dict[str, callable]:
        """Initialize context synthesis functions."""
        return {
            "urgency_calculator": lambda ctx: self._calculate_urgency(ctx),
            "energy_optimizer": lambda ctx: self._optimize_for_energy(ctx),
            "pattern_predictor": lambda ctx: self._predict_patterns(ctx)
        }
    
    def _initialize_cognitive_adapters(self) -> Dict[str, callable]:
        """Initialize cognitive load adaptation functions."""
        return {
            "high_load": lambda: self._high_cognitive_load_adaptation(),
            "medium_load": lambda: self._medium_cognitive_load_adaptation(),
            "low_load": lambda: self._low_cognitive_load_adaptation()
        }


# Global instance
context_aware_prompting = ContextAwarePromptEngine()