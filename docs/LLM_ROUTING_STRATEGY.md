# MCP ADHD Server - LLM Routing Strategy

> **Intelligent Local-First with Cloud Enhancement via OpenRouter**

## 🎯 **Core Philosophy**

**"Local by default, cloud by consent, always with user control"**

- **90% of interactions**: Handled by local DeepSeek-R1:1.5B via Ollama
- **10% complex tasks**: Routed to Claude/GPT-4o via OpenRouter with user consent
- **0% crisis situations**: Hard-coded responses, no LLM involvement

## 🧠 **Routing Decision Matrix**

| Task Type | Complexity | Local Capability | Routing Decision | Rationale |
|-----------|------------|------------------|------------------|-----------|
| **Simple Nudge** | Low | ✅ Excellent | Local Only | "Ready to tackle that task?" |
| **Crisis Detection** | N/A | ⚠️ Not Used | Hard-coded | Safety requires deterministic response |
| **Pattern Recognition** | Medium | ✅ Good | Local First | Daily pattern analysis |
| **Therapeutic Reflection** | High | ⚠️ Limited | Cloud (Consent) | Nuanced therapeutic language |
| **Complex Planning** | High | ⚠️ Limited | Cloud (Consent) | Multi-step project breakdown |
| **Narrative Reframing** | High | ⚠️ Limited | Cloud (Consent) | Sophisticated reauthoring conversations |

## ⚡ **Implementation Architecture**

### **LLM Router Class**

```python
from enum import Enum
from typing import Optional, Dict, Any
import asyncio

class TaskComplexity(Enum):
    SIMPLE = "simple"      # Local only
    MODERATE = "moderate"  # Local preferred
    COMPLEX = "complex"    # Cloud recommended
    CRISIS = "crisis"      # Hard-coded only

class LLMRouter:
    def __init__(self):
        self.local_client = OllamaClient("deepseek-r1:1.5b")
        self.cloud_client = OpenRouterClient()
        self.complexity_classifier = ComplexityClassifier()
        self.safety_monitor = SafetyMonitor()
        
    async def route_request(
        self, 
        user_input: str, 
        context: MCPFrame,
        user_preferences: UserPreferences
    ) -> LLMResponse:
        
        # Step 1: Safety check (always first)
        safety_assessment = await self.safety_monitor.assess_risk(
            user_input, context.user_state
        )
        
        if safety_assessment.is_crisis:
            return self._handle_crisis(safety_assessment)
        
        # Step 2: Complexity assessment
        complexity = await self.complexity_classifier.assess(
            user_input, context
        )
        
        # Step 3: Route based on complexity and user preferences
        if complexity == TaskComplexity.SIMPLE:
            return await self._handle_local(user_input, context)
            
        elif complexity == TaskComplexity.MODERATE:
            # Try local first, fallback to cloud if needed
            local_response = await self._handle_local(user_input, context)
            
            if self._is_response_adequate(local_response):
                return local_response
            elif user_preferences.allow_cloud_fallback:
                return await self._handle_cloud(user_input, context)
            else:
                return local_response  # Best effort local
                
        elif complexity == TaskComplexity.COMPLEX:
            if user_preferences.allow_cloud_for_complex:
                return await self._handle_cloud(user_input, context)
            else:
                # Inform user about limitation, offer local best-effort
                return await self._handle_local_with_disclaimer(
                    user_input, context
                )
    
    def _handle_crisis(self, assessment: SafetyAssessment) -> LLMResponse:
        """Hard-coded crisis response - no LLM involved"""
        return LLMResponse(
            text=CRISIS_RESPONSES[assessment.crisis_type],
            source="hard_coded",
            actions=[
                ActionItem(
                    type="display_resources",
                    data={"resources": CRISIS_RESOURCES}
                )
            ]
        )
```

### **Complexity Classification**

```python
class ComplexityClassifier:
    def __init__(self):
        self.simple_patterns = [
            r"ready to (start|begin|do)",
            r"let's (get|go)",
            r"time for",
            r"quick reminder",
            r"how are you feeling"
        ]
        
        self.complex_patterns = [
            r"help me understand why",
            r"what does it mean that",
            r"can you help me reframe",
            r"break down this project",
            r"create a plan for"
        ]
    
    async def assess(self, user_input: str, context: MCPFrame) -> TaskComplexity:
        # Quick pattern matching for obvious cases
        if any(re.search(pattern, user_input.lower()) 
               for pattern in self.simple_patterns):
            return TaskComplexity.SIMPLE
            
        if any(re.search(pattern, user_input.lower()) 
               for pattern in self.complex_patterns):
            return TaskComplexity.COMPLEX
        
        # Use local classifier for edge cases
        features = self._extract_features(user_input, context)
        complexity_score = self._classify_complexity(features)
        
        if complexity_score < 0.3:
            return TaskComplexity.SIMPLE
        elif complexity_score < 0.7:
            return TaskComplexity.MODERATE
        else:
            return TaskComplexity.COMPLEX
    
    def _extract_features(self, user_input: str, context: MCPFrame) -> Dict:
        return {
            "input_length": len(user_input.split()),
            "question_words": len([w for w in user_input.split() 
                                 if w.lower() in ["what", "why", "how", "when"]]),
            "context_complexity": len(context.context),
            "emotional_words": self._count_emotional_words(user_input),
            "task_indicators": self._count_task_indicators(user_input)
        }
```

## 🌐 **OpenRouter Integration**

### **Cloud LLM Configuration**

```python
class OpenRouterClient:
    def __init__(self):
        self.client = openai.AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
        )
        
        # Model preferences for different task types
        self.model_routing = {
            TaskType.THERAPEUTIC_REFLECTION: "anthropic/claude-3.5-sonnet",
            TaskType.COMPLEX_PLANNING: "openai/gpt-4o",
            TaskType.CREATIVE_REFRAMING: "anthropic/claude-3.5-sonnet",
            TaskType.ANALYTICAL_BREAKDOWN: "openai/gpt-4o-mini",
        }
    
    async def generate_response(
        self, 
        prompt: str, 
        context: MCPFrame,
        task_type: TaskType
    ) -> LLMResponse:
        
        # Select optimal model for task type
        model = self.model_routing.get(
            task_type, 
            "anthropic/claude-3.5-sonnet"  # Default
        )
        
        # Anonymize context for privacy
        anonymized_context = self._anonymize_context(context)
        
        # Build therapeutic-appropriate system prompt
        system_prompt = self._build_therapeutic_prompt(
            task_type, anonymized_context
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,  # Keep responses concise for ADHD
                temperature=0.7,
                timeout=10  # Fail fast to local fallback
            )
            
            return LLMResponse(
                text=response.choices[0].message.content,
                source=f"cloud_{model.split('/')[-1]}",
                cost=self._calculate_cost(response.usage),
                latency=response.response_time
            )
            
        except Exception as e:
            logger.warning(f"Cloud LLM failed: {e}")
            # Fallback to local
            return await self.local_client.generate_response(prompt, context)
    
    def _anonymize_context(self, context: MCPFrame) -> Dict:
        """Strip all PII, keep behavioral patterns only"""
        return {
            "psychological_state": context.user_state,
            "recent_pattern_type": context.get_pattern_category(),
            "intervention_history": context.get_anonymized_outcomes(),
            "energy_level": context.get_energy_level(),
            "time_context": context.get_time_category()  # morning/afternoon/evening
        }
```

### **Cost Management**

```python
class CostManager:
    def __init__(self):
        self.monthly_budget = 15.00  # $15/month per user
        self.cost_per_model = {
            "anthropic/claude-3.5-sonnet": 0.015,  # per 1k tokens
            "openai/gpt-4o": 0.005,
            "openai/gpt-4o-mini": 0.0015,
        }
    
    async def check_budget(self, user_id: str, estimated_tokens: int) -> bool:
        current_usage = await self.get_monthly_usage(user_id)
        estimated_cost = (estimated_tokens / 1000) * 0.015  # Assume Claude
        
        return (current_usage + estimated_cost) < self.monthly_budget
    
    async def suggest_alternative(self, user_id: str) -> str:
        """When budget exceeded, suggest local alternatives"""
        return (
            "You've reached your monthly cloud AI budget. "
            "I'll use my local reasoning for this request, "
            "or you can upgrade for unlimited access."
        )
```

## 🛡️ **Safety & Privacy**

### **Privacy-Preserving Cloud Requests**

```python
class PrivacyManager:
    def prepare_cloud_request(self, context: MCPFrame) -> Dict:
        """Ensure zero PII in cloud requests"""
        return {
            # Behavioral patterns only - no personal details
            "state_summary": self._categorize_state(context.user_state),
            "task_pattern": self._categorize_task(context.task_focus),
            "intervention_effectiveness": self._summarize_outcomes(context),
            "contextual_factors": {
                "time_of_day": self._get_time_category(),
                "energy_level": context.energy_level,
                "recent_completions": len(context.recent_successes)
            }
        }
    
    def _categorize_state(self, state: UserState) -> str:
        """Convert specific state to general category"""
        mapping = {
            UserState.ENERGIZED: "high_energy",
            UserState.LOW: "low_energy", 
            UserState.ANXIOUS: "heightened_arousal",
            UserState.FOCUSED: "optimal_state",
            UserState.FRAGMENTED: "scattered_attention"
        }
        return mapping.get(state, "neutral")
```

### **Local Safety Monitor**

```python
class SafetyMonitor:
    def __init__(self):
        # Local BERT classifier for crisis detection
        self.crisis_classifier = pipeline(
            "text-classification",
            model="distilbert-base-uncased-finetuned-crisis",
            device=0 if torch.cuda.is_available() else -1
        )
        
        # Hard-coded safety patterns (always checked first)
        self.crisis_patterns = [
            r"want to (die|kill myself|end it)",
            r"suicide|suicidal",
            r"harm myself|hurt myself",
            r"no point (in )?living"
        ]
    
    async def assess_risk(self, text: str, user_state: UserState) -> SafetyAssessment:
        # Step 1: Immediate pattern matching (< 1ms)
        for pattern in self.crisis_patterns:
            if re.search(pattern, text.lower()):
                return SafetyAssessment(
                    is_crisis=True,
                    confidence=1.0,
                    crisis_type="explicit_self_harm",
                    source="pattern_match"
                )
        
        # Step 2: ML classification for subtle cases
        result = self.crisis_classifier(text)[0]
        
        if result['label'] == 'CRISIS' and result['score'] > 0.8:
            return SafetyAssessment(
                is_crisis=True,
                confidence=result['score'],
                crisis_type="implicit_distress",
                source="ml_classifier"
            )
        
        return SafetyAssessment(is_crisis=False)
```

## 📊 **Performance Metrics**

### **Target Performance**

| Metric | Local (DeepSeek) | Cloud (Claude) | Safety Override |
|--------|------------------|----------------|-----------------|
| **Latency** | <500ms | <2s | <100ms |
| **Accuracy** | 85% | 95% | 100% |
| **Cost** | $0 | $0.10-0.50 | $0 |
| **Privacy** | 100% local | Anonymized | 100% local |

### **Usage Distribution Goals**

```python
USAGE_TARGETS = {
    "local_simple": 0.70,      # 70% simple nudges, local only
    "local_moderate": 0.15,    # 15% moderate tasks, local first  
    "cloud_complex": 0.10,     # 10% complex tasks, cloud enhanced
    "cloud_fallback": 0.04,    # 4% local failed, cloud rescue
    "safety_override": 0.01,   # 1% crisis, hard-coded response
}
```

## 🎯 **Implementation Timeline**

### **Week 1: Local Foundation**
- [x] Ollama setup with DeepSeek-R1:1.5B
- [x] Basic routing logic
- [x] Safety monitor with pattern matching

### **Week 2: Cloud Integration**  
- [ ] OpenRouter client implementation
- [ ] Privacy-preserving context anonymization
- [ ] Cost tracking and budget management

### **Week 3: Intelligence Layer**
- [ ] Complexity classification
- [ ] User preference management
- [ ] Performance monitoring

### **Week 4: Optimization**
- [ ] Response quality assessment
- [ ] Fallback strategies
- [ ] Usage analytics and optimization

This routing strategy gives you **the best of both worlds**: privacy-preserving local processing for 90% of interactions, with intelligent cloud enhancement for complex therapeutic work - all while maintaining user control and clinical safety! 🚀