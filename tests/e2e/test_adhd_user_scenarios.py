"""
END-TO-END TESTS: ADHD User Journey Scenarios

These tests validate complete user journeys through realistic ADHD scenarios:
- Executive dysfunction support patterns
- Hyperfocus session management
- Task switching and context management
- Overwhelm detection and intervention
- Crisis intervention with safety priority
- Energy management and timing optimization
- Procrastination breakthrough techniques

ADHD USER JOURNEY REQUIREMENTS:
- System must adapt to user's current executive function state
- Responses must account for working memory limitations
- Time-based patterns must align with ADHD energy cycles
- Safety interventions must work regardless of user state
- System must learn and improve from interaction patterns
"""
import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List, Tuple

from mcp_server.cognitive_loop import cognitive_loop
from mcp_server.models import NudgeTier, UserState
from mcp_server.auth import AuthManager, RegistrationRequest, LoginRequest


class TestExecutiveDysfunctionSupport:
    """Test support for executive dysfunction scenarios."""
    
    @pytest.mark.asyncio
    async def test_task_initiation_difficulty_journey(self):
        """Test complete journey for user struggling with task initiation."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            user_id = "task_initiation_user"
            
            # Mock frame builder to recognize task initiation struggles
            def create_frame_for_input(user_input):
                mock_frame = Mock()
                mock_frame.frame = Mock()
                mock_frame.frame.context = []
                
                if "can't start" in user_input.lower() or "procrastinating" in user_input.lower():
                    mock_frame.cognitive_load = 0.8
                    mock_frame.frame.context.append(
                        Mock(type=Mock(value="user_state"), data={"current_state": "stuck"})
                    )
                elif "tiny step" in user_input.lower() or "just" in user_input.lower():
                    mock_frame.cognitive_load = 0.4
                    mock_frame.frame.context.append(
                        Mock(type=Mock(value="user_state"), data={"current_state": "engaging"})
                    )
                else:
                    mock_frame.cognitive_load = 0.6
                
                mock_frame.accessibility_score = 0.7
                mock_frame.recommended_action = None
                return mock_frame
            
            mock_frame_builder.build_frame = AsyncMock(side_effect=lambda **kwargs: create_frame_for_input(kwargs.get('user_input', '')))
            
            # Mock LLM responses appropriate to executive dysfunction
            def create_llm_response(user_input, context, **kwargs):
                mock_response = Mock()
                mock_response.source = "local"
                mock_response.confidence = 0.8
                
                if "can't start" in user_input.lower():
                    mock_response.text = "That's totally normal! What's the tiniest first step you could take? Just opening the file counts as progress. 🌟"
                elif "tiny step" in user_input.lower():
                    mock_response.text = "Perfect! You're already making progress. What feels like the next small step?"
                elif "finished" in user_input.lower():
                    mock_response.text = "Amazing work! You broke through the initiation barrier. How does it feel to be in motion? 💪"
                else:
                    mock_response.text = "I'm here to help you get unstuck. Let's break this down together."
                
                return mock_response
            
            mock_llm_router.process_request = AsyncMock(side_effect=create_llm_response)
            
            # Journey: Task initiation difficulty → breakdown → action → momentum
            journey_steps = [
                {
                    "input": "I need to write this report but I can't start. I've been procrastinating for hours.",
                    "expected_patterns": ["stuck", "procrastination"],
                    "expected_actions": ["cognitive_load_warning"],
                    "max_response_time": 2000
                },
                {
                    "input": "Okay, what's a tiny step I can take right now?",
                    "expected_patterns": ["task_breakdown_request"],
                    "expected_response_contains": ["tiny", "small", "first step"],
                    "max_response_time": 1500
                },
                {
                    "input": "I just opened the document and wrote the title",
                    "expected_patterns": ["progress_acknowledgment"],
                    "expected_response_contains": ["progress", "good", "amazing"],
                    "max_response_time": 1000
                },
                {
                    "input": "That felt good! I finished the first paragraph",
                    "expected_patterns": ["momentum_building"],
                    "expected_response_contains": ["momentum", "motion", "work"],
                    "max_response_time": 1000
                }
            ]
            
            for i, step in enumerate(journey_steps):
                print(f"Step {i+1}: {step['input'][:50]}...")
                
                start_time = time.perf_counter()
                result = await cognitive_loop.process_user_input(
                    user_id=user_id,
                    user_input=step["input"],
                    task_focus="Report writing"
                )
                response_time = (time.perf_counter() - start_time) * 1000
                
                # Validate response
                assert result.success is True, f"Step {i+1} failed: {result.error}"
                assert response_time < step["max_response_time"], \
                    f"Step {i+1} took {response_time}ms, exceeds {step['max_response_time']}ms"
                
                # Check expected response content
                if "expected_response_contains" in step:
                    response_text = result.response.text.lower()
                    for expected_phrase in step["expected_response_contains"]:
                        assert expected_phrase in response_text, \
                            f"Step {i+1} missing expected phrase '{expected_phrase}' in response"
                
                # Check expected actions
                if "expected_actions" in step:
                    for expected_action in step["expected_actions"]:
                        assert expected_action in result.actions_taken, \
                            f"Step {i+1} missing expected action '{expected_action}'"
                
                # Validate cognitive load progression (should decrease as user gains momentum)
                if i == 0:
                    assert result.cognitive_load > 0.7, "Initial cognitive load should be high"
                elif i == len(journey_steps) - 1:
                    assert result.cognitive_load < 0.5, "Final cognitive load should be lower"
    
    @pytest.mark.asyncio
    async def test_working_memory_overload_journey(self):
        """Test journey for user experiencing working memory overload."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            user_id = "memory_overload_user"
            
            # Mock high cognitive load scenario
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.frame.context = [
                Mock(type=Mock(value="user_state"), data={"current_state": "overwhelmed"})
            ]
            mock_frame.cognitive_load = 0.9  # Very high
            mock_frame.accessibility_score = 0.3  # Low due to overwhelm
            mock_frame.recommended_action = "simplify_context"
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            # Mock simplification responses
            def create_simplifying_response(user_input, context, **kwargs):
                mock_response = Mock()
                mock_response.source = "local"
                mock_response.confidence = 0.9
                mock_response.text = "Let's focus on just ONE thing. Pick the most important item. Everything else can wait. 🎯"
                return mock_response
            
            mock_llm_router.process_request = AsyncMock(side_effect=create_simplifying_response)
            
            # Journey: Overwhelm → Simplification → Focus
            result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="I have 15 tasks due today, 3 meetings, 20 emails, and my brain is fried. I can't think straight.",
                task_focus="Priority management"
            )
            
            assert result.success is True
            assert result.cognitive_load >= 0.9, "Should recognize high cognitive load"
            assert "context_simplification" in result.actions_taken
            assert "accessibility_adjustment" in result.actions_taken
            
            # Response should be simplified for overwhelmed state
            assert len(result.response.text) < 200, "Response too long for overwhelmed user"
            assert "one" in result.response.text.lower(), "Should focus on singular priority"
    
    @pytest.mark.asyncio
    async def test_decision_paralysis_breakthrough(self):
        """Test breakthrough journey for decision paralysis."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            user_id = "decision_paralysis_user"
            
            # Mock decision paralysis context
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.frame.context = [
                Mock(type=Mock(value="user_state"), data={"current_state": "stuck"})
            ]
            mock_frame.cognitive_load = 0.7
            mock_frame.accessibility_score = 0.5
            mock_frame.recommended_action = "clarify_focus"
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            # Mock decision-making support response
            mock_response = Mock()
            mock_response.source = "local"
            mock_response.confidence = 0.8
            mock_response.text = "Let's use the 2-minute rule: pick the option you'd choose if you only had 2 minutes to decide. Trust your gut! ⚡"
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="I need to pick a framework for my project but there are so many options. I've been researching for 3 days and I'm more confused than when I started.",
                task_focus="Framework selection"
            )
            
            assert result.success is True
            assert "focus_clarification" in result.actions_taken
            assert "2-minute" in result.response.text or "gut" in result.response.text
            
            # Should provide concrete decision-making strategy
            response_text = result.response.text.lower()
            decision_keywords = ["choose", "pick", "decide", "trust", "rule"]
            assert any(keyword in response_text for keyword in decision_keywords)


class TestHyperfocusSessionManagement:
    """Test hyperfocus session detection and management."""
    
    @pytest.mark.asyncio
    async def test_hyperfocus_detection_and_break_reminders(self):
        """Test detection of hyperfocus and appropriate break reminders."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            user_id = "hyperfocus_user"
            
            # Mock hyperfocus pattern recognition
            session_count = 0
            
            def create_hyperfocus_frame(**kwargs):
                nonlocal session_count
                session_count += 1
                
                mock_frame = Mock()
                mock_frame.frame = Mock()
                
                if session_count > 10:  # After sustained activity
                    mock_frame.frame.context = [
                        Mock(type=Mock(value="user_state"), data={"current_state": "hyperfocus"}),
                        Mock(type=Mock(value="session_duration"), data={"minutes": 120})
                    ]
                    mock_frame.cognitive_load = 0.3  # Low load during hyperfocus
                else:
                    mock_frame.frame.context = [
                        Mock(type=Mock(value="user_state"), data={"current_state": "focused"})
                    ]
                    mock_frame.cognitive_load = 0.4
                
                mock_frame.accessibility_score = 0.8
                mock_frame.recommended_action = None
                return mock_frame
            
            mock_frame_builder.build_frame = AsyncMock(side_effect=create_hyperfocus_frame)
            
            # Mock appropriate responses for hyperfocus
            def create_hyperfocus_response(user_input, context, **kwargs):
                mock_response = Mock()
                mock_response.source = "local"
                mock_response.confidence = 0.9
                
                # Check if user is in hyperfocus based on context
                hyperfocus_detected = any(
                    hasattr(item, 'data') and item.data.get('current_state') == 'hyperfocus'
                    for item in context.context if hasattr(context, 'context')
                ) if context else False
                
                if hyperfocus_detected:
                    mock_response.text = "You're in great flow! 🎯 Quick reminder: hydrate and stretch. Your brain needs fuel to keep this momentum going."
                else:
                    mock_response.text = "Great focus! Keep up the momentum."
                
                return mock_response
            
            mock_llm_router.process_request = AsyncMock(side_effect=create_hyperfocus_response)
            
            # Simulate sustained focused activity
            for i in range(15):
                result = await cognitive_loop.process_user_input(
                    user_id=user_id,
                    user_input=f"Making good progress on section {i+1}",
                    task_focus="Deep work project"
                )
                
                assert result.success is True
                
                # After sustained activity, should get hyperfocus management
                if i > 10:
                    response_text = result.response.text.lower()
                    health_reminders = ["hydrate", "stretch", "break", "fuel", "rest"]
                    assert any(reminder in response_text for reminder in health_reminders), \
                        "Should provide health reminders during hyperfocus"
    
    @pytest.mark.asyncio
    async def test_hyperfocus_crash_recovery(self):
        """Test recovery support after hyperfocus crash."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            user_id = "hyperfocus_crash_user"
            
            # Mock post-hyperfocus exhaustion
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.frame.context = [
                Mock(type=Mock(value="user_state"), data={"current_state": "exhausted"}),
                Mock(type=Mock(value="previous_state"), data={"state": "hyperfocus", "duration": 240})
            ]
            mock_frame.cognitive_load = 0.8  # High load due to exhaustion
            mock_frame.accessibility_score = 0.4  # Low due to fatigue
            mock_frame.recommended_action = "rest_and_recover"
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            # Mock recovery-focused response
            mock_response = Mock()
            mock_response.source = "local"
            mock_response.confidence = 0.9
            mock_response.text = "Hyperfocus crash is totally normal! 💙 Your brain did amazing work. Rest now - gentle tasks only. You've earned it."
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="I was super focused for 4 hours but now I'm completely drained and can barely think",
                task_focus="Recovery"
            )
            
            assert result.success is True
            assert result.cognitive_load > 0.7, "Should recognize high cognitive load during crash"
            
            # Should provide recovery-focused support
            response_text = result.response.text.lower()
            recovery_keywords = ["normal", "rest", "gentle", "earned", "crash"]
            assert any(keyword in response_text for keyword in recovery_keywords)


class TestTaskSwitchingAndContextManagement:
    """Test task switching scenarios common in ADHD."""
    
    @pytest.mark.asyncio
    async def test_context_switching_journey(self):
        """Test smooth context switching between tasks."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            user_id = "context_switch_user"
            
            # Mock context-aware frame building
            def create_context_frame(task_focus=None, **kwargs):
                mock_frame = Mock()
                mock_frame.frame = Mock()
                mock_frame.frame.task_focus = task_focus
                mock_frame.frame.context = [
                    Mock(type=Mock(value="previous_task"), data={"task": task_focus})
                ]
                mock_frame.cognitive_load = 0.5
                mock_frame.accessibility_score = 0.7
                mock_frame.recommended_action = None
                return mock_frame
            
            mock_frame_builder.build_frame = AsyncMock(side_effect=create_context_frame)
            
            # Mock context-aware responses
            def create_context_response(user_input, context, **kwargs):
                mock_response = Mock()
                mock_response.source = "local"
                mock_response.confidence = 0.8
                
                if "switching to" in user_input.lower():
                    mock_response.text = "Context switch noted! Let me help you transition smoothly. What's your first step with this new task?"
                elif "where was I" in user_input.lower():
                    mock_response.text = "Let me help you rebuild context. You were working on your previous task - what was the last thing you remember?"
                else:
                    mock_response.text = "I'm tracking your task context to help with smooth transitions."
                
                return mock_response
            
            mock_llm_router.process_request = AsyncMock(side_effect=create_context_response)
            
            # Task switching journey
            tasks = [
                ("email", "Processing urgent emails"),
                ("project", "Working on main project deliverable"), 
                ("meeting", "Preparing for 2pm meeting"),
                ("email", "Back to email processing")
            ]
            
            for i, (task_type, task_description) in enumerate(tasks):
                if i == 0:
                    user_input = f"Starting work on {task_description.lower()}"
                else:
                    user_input = f"Switching to {task_description.lower()}"
                
                result = await cognitive_loop.process_user_input(
                    user_id=user_id,
                    user_input=user_input,
                    task_focus=task_type
                )
                
                assert result.success is True
                assert result.context_frame.task_focus == task_type
                
                if "switching to" in user_input.lower():
                    assert "transition" in result.response.text.lower() or \
                           "switch" in result.response.text.lower()
            
            # Test context recovery
            result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="Wait, where was I with the project work?",
                task_focus="project"
            )
            
            assert result.success is True
            assert "context" in result.response.text.lower() or \
                   "remember" in result.response.text.lower()
    
    @pytest.mark.asyncio
    async def test_interrupted_task_recovery(self):
        """Test recovery when returning to interrupted tasks."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            user_id = "interrupted_task_user"
            task_history = []
            
            # Mock frame building with task history
            def create_history_frame(user_input=None, task_focus=None, **kwargs):
                nonlocal task_history
                
                if task_focus:
                    task_history.append(task_focus)
                
                mock_frame = Mock()
                mock_frame.frame = Mock()
                mock_frame.frame.task_focus = task_focus
                mock_frame.frame.context = [
                    Mock(type=Mock(value="task_history"), data={"recent_tasks": task_history[-3:]})
                ]
                mock_frame.cognitive_load = 0.6
                mock_frame.accessibility_score = 0.6
                mock_frame.recommended_action = None
                return mock_frame
            
            mock_frame_builder.build_frame = AsyncMock(side_effect=create_history_frame)
            
            # Mock recovery assistance
            mock_response = Mock()
            mock_response.source = "local"
            mock_response.confidence = 0.8
            mock_response.text = "Let me help you pick up where you left off. Based on your recent work, you were making progress on the analysis section."
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            # Simulate interrupted task flow
            # 1. Start task
            await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="Working on data analysis for the quarterly report",
                task_focus="quarterly_report"
            )
            
            # 2. Interruption
            await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="Urgent call came in, had to switch to client issue",
                task_focus="client_support"
            )
            
            # 3. Return to original task
            result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="Okay, back to the quarterly report. What was I doing?",
                task_focus="quarterly_report"
            )
            
            assert result.success is True
            response_text = result.response.text.lower()
            recovery_indicators = ["pick up", "left off", "progress", "recent", "analysis"]
            assert any(indicator in response_text for indicator in recovery_indicators)


class TestOverwhelmDetectionAndIntervention:
    """Test overwhelm detection and intervention scenarios."""
    
    @pytest.mark.asyncio
    async def test_overwhelm_escalation_and_deescalation(self):
        """Test complete overwhelm escalation and deescalation journey."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            user_id = "overwhelm_journey_user"
            overwhelm_level = 0.3  # Start moderate
            
            def create_overwhelm_frame(user_input=None, **kwargs):
                nonlocal overwhelm_level
                
                # Detect overwhelm escalation in user input
                if any(word in user_input.lower() for word in ["too much", "can't handle", "overwhelmed", "panic"]):
                    overwhelm_level = min(0.95, overwhelm_level + 0.2)
                elif any(word in user_input.lower() for word in ["better", "calmer", "one thing", "focus"]):
                    overwhelm_level = max(0.2, overwhelm_level - 0.3)
                
                mock_frame = Mock()
                mock_frame.frame = Mock()
                mock_frame.frame.context = [
                    Mock(type=Mock(value="user_state"), data={
                        "current_state": "overwhelmed" if overwhelm_level > 0.7 else "moderate",
                        "overwhelm_level": overwhelm_level
                    })
                ]
                mock_frame.cognitive_load = overwhelm_level
                mock_frame.accessibility_score = max(0.2, 1.0 - overwhelm_level)
                mock_frame.recommended_action = "simplify_context" if overwhelm_level > 0.7 else None
                return mock_frame
            
            mock_frame_builder.build_frame = AsyncMock(side_effect=create_overwhelm_frame)
            
            # Mock graduated response based on overwhelm level
            def create_overwhelm_response(user_input, context, **kwargs):
                mock_response = Mock()
                mock_response.source = "local"
                mock_response.confidence = 0.9
                
                current_overwhelm = 0.5  # Default
                if context and hasattr(context, 'context'):
                    for item in context.context:
                        if hasattr(item, 'data') and 'overwhelm_level' in item.data:
                            current_overwhelm = item.data['overwhelm_level']
                            break
                
                if current_overwhelm > 0.8:
                    mock_response.text = "Stop. Breathe. You're safe. Pick ONE tiny thing. Everything else can wait. 🛡️"
                elif current_overwhelm > 0.6:
                    mock_response.text = "I see you're feeling overwhelmed. Let's slow down and focus on just the most important thing."
                else:
                    mock_response.text = "Good work managing the overwhelm. You're finding your balance again."
                
                return mock_response
            
            mock_llm_router.process_request = AsyncMock(side_effect=create_overwhelm_response)
            
            # Overwhelm journey: escalation → intervention → deescalation
            journey = [
                {
                    "input": "I have 12 things due today and my boss just added 3 more urgent items",
                    "expected_state": "building_overwhelm",
                    "max_cognitive_load": 0.8
                },
                {
                    "input": "I can't handle this! Everything is too much and I'm starting to panic",
                    "expected_state": "overwhelmed",
                    "expected_actions": ["context_simplification", "cognitive_load_warning"],
                    "response_should_contain": ["stop", "breathe", "one"]
                },
                {
                    "input": "Okay, I'm trying to breathe. What's the one most important thing?",
                    "expected_state": "seeking_guidance", 
                    "response_should_contain": ["important", "focus"]
                },
                {
                    "input": "I focused on just the client presentation and finished it. Feeling better.",
                    "expected_state": "recovering",
                    "response_should_contain": ["good", "balance", "managing"]
                }
            ]
            
            for i, step in enumerate(journey):
                print(f"Overwhelm step {i+1}: {step['input'][:50]}...")
                
                result = await cognitive_loop.process_user_input(
                    user_id=user_id,
                    user_input=step["input"]
                )
                
                assert result.success is True
                
                # Check cognitive load progression
                if "max_cognitive_load" in step:
                    assert result.cognitive_load <= step["max_cognitive_load"]
                
                # Check expected actions
                if "expected_actions" in step:
                    for expected_action in step["expected_actions"]:
                        assert expected_action in result.actions_taken
                
                # Check response content
                if "response_should_contain" in step:
                    response_text = result.response.text.lower()
                    for expected_word in step["response_should_contain"]:
                        assert expected_word in response_text, \
                            f"Response missing expected word '{expected_word}': {result.response.text}"
    
    @pytest.mark.asyncio
    async def test_time_pressure_overwhelm(self):
        """Test overwhelm specifically from time pressure."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            user_id = "time_pressure_user"
            
            # Mock time pressure context
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.frame.context = [
                Mock(type=Mock(value="time_context"), data={"deadline": "in 2 hours", "task_complexity": "high"}),
                Mock(type=Mock(value="user_state"), data={"current_state": "time_pressured"})
            ]
            mock_frame.cognitive_load = 0.85
            mock_frame.accessibility_score = 0.3
            mock_frame.recommended_action = "time_management_support"
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            # Mock time management response
            mock_response = Mock()
            mock_response.source = "local"
            mock_response.confidence = 0.9
            mock_response.text = "Time crunch mode! Let's triage: what's the MINIMUM viable version you can deliver? Perfect is the enemy of done. ⏰"
            mock_llm_router.process_request = AsyncMock(return_value=mock_response)
            
            result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="I have 2 hours to finish this presentation and it's nowhere near ready. I'm freaking out!"
            )
            
            assert result.success is True
            assert result.cognitive_load > 0.8, "Should recognize high time pressure load"
            
            response_text = result.response.text.lower()
            time_management_keywords = ["minimum", "triage", "viable", "done"]
            assert any(keyword in response_text for keyword in time_management_keywords)


class TestCrisisInterventionInContext:
    """Test crisis intervention within ADHD user journeys."""
    
    @pytest.mark.asyncio
    async def test_crisis_during_overwhelm_escalation(self):
        """Test crisis intervention when overwhelm escalates to crisis."""
        with patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            user_id = "crisis_overwhelm_user"
            
            # Mock crisis detection in LLM router
            def crisis_aware_response(user_input, context, **kwargs):
                if "kill myself" in user_input.lower() or "want to die" in user_input.lower():
                    mock_response = Mock()
                    mock_response.source = "hard_coded"
                    mock_response.confidence = 1.0
                    mock_response.text = ("I'm concerned about what you're going through. You don't have to face this alone.\n\n"
                                        "🆘 **Immediate Support:**\n"
                                        "• Crisis Text Line: Text HOME to 741741\n"
                                        "• National Suicide Prevention Lifeline: 988\n"
                                        "• Emergency: 911")
                    mock_response.model_used = "safety_override"
                    return mock_response
                else:
                    mock_response = Mock()
                    mock_response.source = "local"
                    mock_response.confidence = 0.8
                    mock_response.text = "I understand you're overwhelmed. Let's take this one step at a time."
                    return mock_response
            
            mock_llm_router.process_request = AsyncMock(side_effect=crisis_aware_response)
            
            # Journey: overwhelm → crisis → safety intervention
            # 1. Initial overwhelm
            result1 = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="My ADHD is making everything impossible. I can't keep up with anything."
            )
            assert result1.success is True
            assert result1.response.source == "local"
            
            # 2. Crisis escalation
            start_time = time.perf_counter()
            result2 = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="I can't handle my ADHD anymore. Maybe everyone would be better off if I just kill myself."
            )
            crisis_response_time = (time.perf_counter() - start_time) * 1000
            
            # CRITICAL: Must be crisis response
            assert result2.success is True
            assert result2.response.source == "hard_coded"
            assert "988" in result2.response.text
            assert "911" in result2.response.text
            assert "safety_override" in result2.actions_taken
            
            # CRITICAL: Crisis response must be ultra-fast even in context of overwhelm
            assert crisis_response_time < 200, f"Crisis response took {crisis_response_time}ms, must be <200ms"
    
    @pytest.mark.asyncio
    async def test_crisis_during_hyperfocus_crash(self):
        """Test crisis intervention during post-hyperfocus vulnerability."""
        with patch('mcp_server.llm_client.llm_router') as mock_llm_router:
            
            user_id = "crisis_hyperfocus_user"
            
            # Mock crisis response
            def hyperfocus_crisis_response(user_input, context, **kwargs):
                if "harm myself" in user_input.lower():
                    mock_response = Mock()
                    mock_response.source = "hard_coded"
                    mock_response.confidence = 1.0
                    mock_response.text = "I'm concerned about what you're going through. Crisis support is available 24/7."
                    mock_response.model_used = "safety_override"
                    return mock_response
                else:
                    mock_response = Mock()
                    mock_response.source = "local"
                    mock_response.text = "Hyperfocus crash is exhausting. Be gentle with yourself."
                    return mock_response
            
            mock_llm_router.process_request = AsyncMock(side_effect=hyperfocus_crisis_response)
            
            # Context: user in vulnerable post-hyperfocus state
            result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input="I crashed so hard after that 6-hour hyperfocus session. I hate my brain. I want to harm myself."
            )
            
            assert result.success is True
            assert result.response.source == "hard_coded"
            assert "safety_override" in result.actions_taken


class TestEnergyManagementAndTimingOptimization:
    """Test energy management and timing optimization features."""
    
    @pytest.mark.asyncio
    async def test_energy_aware_task_suggestions(self):
        """Test system provides energy-appropriate task suggestions."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            user_id = "energy_management_user"
            
            # Test different energy levels
            energy_scenarios = [
                {
                    "energy_level": 0.9,
                    "time": "09:00",
                    "input": "I'm feeling really energized this morning!",
                    "expected_suggestions": ["complex", "challenging", "deep work", "important"]
                },
                {
                    "energy_level": 0.3,
                    "time": "15:00", 
                    "input": "I'm pretty tired after lunch",
                    "expected_suggestions": ["simple", "easy", "organize", "admin"]
                },
                {
                    "energy_level": 0.1,
                    "time": "17:00",
                    "input": "I'm completely drained",
                    "expected_suggestions": ["rest", "gentle", "tomorrow", "recharge"]
                }
            ]
            
            for scenario in energy_scenarios:
                # Mock frame with energy context
                mock_frame = Mock()
                mock_frame.frame = Mock()
                mock_frame.frame.context = [
                    Mock(type=Mock(value="user_state"), data={
                        "current_state": "low" if scenario["energy_level"] < 0.4 else "energized",
                        "energy_level": scenario["energy_level"]
                    }),
                    Mock(type=Mock(value="time_context"), data={"current_time": scenario["time"]})
                ]
                mock_frame.cognitive_load = 1.0 - scenario["energy_level"]  # Inverse relationship
                mock_frame.accessibility_score = 0.8
                mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
                
                # Mock energy-aware response
                def create_energy_response(user_input, context, **kwargs):
                    mock_response = Mock()
                    mock_response.source = "local"
                    mock_response.confidence = 0.8
                    
                    energy = scenario["energy_level"]
                    if energy > 0.7:
                        mock_response.text = "High energy detected! Perfect time for your most challenging deep work. What important project needs your best focus? 🚀"
                    elif energy < 0.4:
                        mock_response.text = "Low energy is normal. Time for gentle tasks: organize files, clear small items, or rest. Your brain needs recovery. 🌱"
                    else:
                        mock_response.text = "Moderate energy - good for routine tasks and planning."
                    
                    return mock_response
                
                mock_llm_router.process_request = AsyncMock(side_effect=create_energy_response)
                
                result = await cognitive_loop.process_user_input(
                    user_id=user_id,
                    user_input=scenario["input"]
                )
                
                assert result.success is True
                
                # Verify energy-appropriate suggestions
                response_text = result.response.text.lower()
                suggestion_found = any(
                    suggestion in response_text 
                    for suggestion in scenario["expected_suggestions"]
                )
                assert suggestion_found, f"No appropriate suggestion for energy level {scenario['energy_level']}: {result.response.text}"


class TestProcrastinationBreakthroughTechniques:
    """Test procrastination breakthrough and momentum building."""
    
    @pytest.mark.asyncio
    async def test_procrastination_pattern_interruption(self):
        """Test detection and interruption of procrastination patterns."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            user_id = "procrastination_user"
            
            # Mock procrastination pattern recognition
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.frame.context = [
                Mock(type=Mock(value="behavior_pattern"), data={"pattern": "procrastination", "duration": "3 hours"}),
                Mock(type=Mock(value="user_state"), data={"current_state": "stuck"})
            ]
            mock_frame.cognitive_load = 0.7
            mock_frame.accessibility_score = 0.5
            mock_frame.recommended_action = "procrastination_intervention"
            mock_frame_builder.build_frame = AsyncMock(return_value=mock_frame)
            
            # Mock procrastination intervention techniques
            def create_intervention_response(user_input, context, **kwargs):
                mock_response = Mock()
                mock_response.source = "local"
                mock_response.confidence = 0.9
                
                intervention_techniques = [
                    "Let's use the 2-minute rule: if it takes less than 2 minutes, do it now!",
                    "Time for the 'Swiss cheese' method: poke holes in the task by doing random small parts.",
                    "Let's try 'temptation bundling': pair this boring task with something you enjoy.",
                    "How about the 'next smallest step'? What's literally the tiniest thing you could do?"
                ]
                
                # Cycle through techniques based on input
                technique_index = len(user_input) % len(intervention_techniques)
                mock_response.text = intervention_techniques[technique_index]
                
                return mock_response
            
            mock_llm_router.process_request = AsyncMock(side_effect=create_intervention_response)
            
            # Test various procrastination interventions
            procrastination_inputs = [
                "I've been putting off this task for 3 hours and just scrolling social media",
                "I know what I need to do but I just can't start",
                "Every time I think about the task I feel resistance and do something else",
                "I'm avoiding this because it feels too big and overwhelming"
            ]
            
            for user_input in procrastination_inputs:
                result = await cognitive_loop.process_user_input(
                    user_id=user_id,
                    user_input=user_input
                )
                
                assert result.success is True
                
                # Should provide specific procrastination intervention technique
                response_text = result.response.text.lower()
                technique_indicators = [
                    "2-minute rule", "swiss cheese", "temptation bundling", 
                    "smallest step", "rule", "method", "technique"
                ]
                assert any(indicator in response_text for indicator in technique_indicators), \
                    f"No clear intervention technique in response: {result.response.text}"
    
    @pytest.mark.asyncio
    async def test_momentum_building_sequence(self):
        """Test momentum building from initial action to sustained progress."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory'):
            
            user_id = "momentum_user"
            progress_count = 0
            
            def create_momentum_frame(user_input=None, **kwargs):
                nonlocal progress_count
                
                # Track progress mentions
                if user_input and any(word in user_input.lower() for word in ["did", "finished", "completed", "done"]):
                    progress_count += 1
                
                mock_frame = Mock()
                mock_frame.frame = Mock()
                mock_frame.frame.context = [
                    Mock(type=Mock(value="momentum"), data={
                        "progress_count": progress_count,
                        "momentum_state": "building" if progress_count > 0 else "stuck"
                    })
                ]
                mock_frame.cognitive_load = max(0.2, 0.8 - (progress_count * 0.2))  # Load decreases with momentum
                mock_frame.accessibility_score = min(0.9, 0.4 + (progress_count * 0.1))  # Accessibility improves
                return mock_frame
            
            mock_frame_builder.build_frame = AsyncMock(side_effect=create_momentum_frame)
            
            # Mock momentum-building responses
            def create_momentum_response(user_input, context, **kwargs):
                mock_response = Mock()
                mock_response.source = "local"
                mock_response.confidence = 0.9
                
                if progress_count == 0:
                    mock_response.text = "Great! You're taking action. That first step breaks the inertia. What feels good to tackle next?"
                elif progress_count < 3:
                    mock_response.text = f"Momentum is building! 🚀 You're {progress_count} steps in. Keep the energy flowing - what's next?"
                else:
                    mock_response.text = "You're in full flow mode! 🌟 This is the sweet spot. Ride this wave as long as it feels good."
                
                return mock_response
            
            mock_llm_router.process_request = AsyncMock(side_effect=create_momentum_response)
            
            # Momentum building sequence
            momentum_sequence = [
                "I finally opened the document and wrote a title",
                "I finished the first paragraph!",
                "Just completed the introduction section", 
                "Done with section 2 and feeling good",
                "On a roll - finished section 3 and starting 4"
            ]
            
            for i, progress_input in enumerate(momentum_sequence):
                result = await cognitive_loop.process_user_input(
                    user_id=user_id,
                    user_input=progress_input
                )
                
                assert result.success is True
                
                # Cognitive load should decrease as momentum builds
                if i == 0:
                    initial_load = result.cognitive_load
                elif i == len(momentum_sequence) - 1:
                    assert result.cognitive_load < initial_load, "Cognitive load should decrease with momentum"
                
                # Response should acknowledge and reinforce momentum
                response_text = result.response.text.lower()
                momentum_indicators = ["momentum", "flow", "energy", "great", "building", "wave"]
                assert any(indicator in response_text for indicator in momentum_indicators), \
                    f"Response doesn't acknowledge momentum: {result.response.text}"


class TestLongTermPatternLearning:
    """Test long-term pattern learning and personalization."""
    
    @pytest.mark.asyncio
    async def test_pattern_recognition_and_adaptation(self):
        """Test system learns user patterns and adapts responses."""
        with patch('frames.builder.frame_builder') as mock_frame_builder, \
             patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
             patch('traces.memory.trace_memory') as mock_trace_memory:
            
            user_id = "pattern_learning_user"
            interaction_history = []
            
            # Mock trace memory that tracks patterns
            async def store_trace_with_learning(trace):
                interaction_history.append({
                    "user_input": trace.event_data.get("user_input", ""),
                    "response": trace.event_data.get("llm_response", ""),
                    "timestamp": datetime.utcnow()
                })
            
            mock_trace_memory.store_trace = AsyncMock(side_effect=store_trace_with_learning)
            
            # Mock frame building that incorporates learned patterns
            def create_pattern_aware_frame(user_input=None, **kwargs):
                mock_frame = Mock()
                mock_frame.frame = Mock()
                
                # After several interactions, start recognizing patterns
                if len(interaction_history) > 3:
                    morning_struggles = sum(1 for interaction in interaction_history 
                                          if "morning" in interaction["user_input"].lower() 
                                          and "struggle" in interaction["user_input"].lower())
                    
                    if morning_struggles >= 2:
                        mock_frame.frame.context = [
                            Mock(type=Mock(value="learned_pattern"), data={
                                "pattern": "morning_struggles",
                                "frequency": morning_struggles,
                                "confidence": 0.8
                            })
                        ]
                    else:
                        mock_frame.frame.context = []
                else:
                    mock_frame.frame.context = []
                
                mock_frame.cognitive_load = 0.5
                mock_frame.accessibility_score = 0.7
                return mock_frame
            
            mock_frame_builder.build_frame = AsyncMock(side_effect=create_pattern_aware_frame)
            
            # Mock adaptive responses based on learned patterns
            def create_pattern_adapted_response(user_input, context, **kwargs):
                mock_response = Mock()
                mock_response.source = "local"
                mock_response.confidence = 0.8
                
                # Check for learned patterns in context
                has_morning_pattern = False
                if context and hasattr(context, 'context'):
                    for item in context.context:
                        if (hasattr(item, 'data') and 
                            item.data.get('pattern') == 'morning_struggles'):
                            has_morning_pattern = True
                            break
                
                if has_morning_pattern and "morning" in user_input.lower():
                    mock_response.text = "I've noticed mornings are tough for you. Let's start with your usual gentle warm-up routine. ☀️"
                    mock_response.confidence = 0.9  # Higher confidence with pattern recognition
                else:
                    mock_response.text = "How can I help you today?"
                
                return mock_response
            
            mock_llm_router.process_request = AsyncMock(side_effect=create_pattern_adapted_response)
            
            # Simulate repeated pattern to establish learning
            morning_struggle_inputs = [
                "I'm struggling to get started this morning",
                "Another rough morning, can't seem to focus",
                "Morning brain fog is hitting hard again",
                "Today's morning is particularly difficult"
            ]
            
            # Process interactions to build pattern recognition
            for i, user_input in enumerate(morning_struggle_inputs):
                result = await cognitive_loop.process_user_input(
                    user_id=user_id,
                    user_input=user_input
                )
                
                assert result.success is True
                
                # After establishing pattern, responses should be personalized
                if i >= 2:  # After seeing the pattern multiple times
                    response_text = result.response.text.lower()
                    personalization_indicators = ["noticed", "usual", "routine", "for you"]
                    if any(indicator in response_text for indicator in personalization_indicators):
                        # Pattern was recognized and response adapted
                        assert result.response.confidence >= 0.9, "Confidence should increase with pattern recognition"
                        break
            
            # Verify pattern learning occurred
            assert len(interaction_history) > 0, "Interactions should be stored for pattern learning"
            
            morning_interactions = sum(1 for interaction in interaction_history 
                                     if "morning" in interaction["user_input"].lower())
            assert morning_interactions >= 3, "Should have tracked morning pattern interactions"


@pytest.mark.asyncio
async def test_complete_adhd_user_day_journey():
    """Integration test: Complete ADHD user day from morning to evening."""
    with patch('frames.builder.frame_builder') as mock_frame_builder, \
         patch('mcp_server.llm_client.llm_router') as mock_llm_router, \
         patch('traces.memory.trace_memory'):
        
        user_id = "full_day_user"
        day_energy = 0.3  # Start low (morning struggle)
        current_hour = 8
        
        # Mock dynamic frame building based on time and energy
        def create_time_aware_frame(user_input=None, **kwargs):
            nonlocal day_energy, current_hour
            
            # Energy patterns typical for ADHD
            if 9 <= current_hour <= 11:  # Morning peak
                day_energy = min(0.9, day_energy + 0.3)
            elif 12 <= current_hour <= 14:  # Afternoon dip
                day_energy = max(0.2, day_energy - 0.4) 
            elif 15 <= current_hour <= 17:  # Second wind
                day_energy = min(0.8, day_energy + 0.2)
            else:  # Evening decline
                day_energy = max(0.1, day_energy - 0.2)
            
            mock_frame = Mock()
            mock_frame.frame = Mock()
            mock_frame.frame.context = [
                Mock(type=Mock(value="time_context"), data={"hour": current_hour}),
                Mock(type=Mock(value="user_state"), data={
                    "energy_level": day_energy,
                    "current_state": "low" if day_energy < 0.4 else "energized"
                })
            ]
            mock_frame.cognitive_load = 1.0 - day_energy
            mock_frame.accessibility_score = day_energy
            return mock_frame
        
        mock_frame_builder.build_frame = AsyncMock(side_effect=create_time_aware_frame)
        
        # Mock time and energy aware responses
        def create_time_response(user_input, context, **kwargs):
            mock_response = Mock()
            mock_response.source = "local"
            mock_response.confidence = 0.8
            
            if day_energy < 0.4:
                mock_response.text = f"Energy is low at {current_hour}:00. Perfect time for gentle tasks or a recharge break. 🌱"
            elif day_energy > 0.7:
                mock_response.text = f"Great energy at {current_hour}:00! Time to tackle your most important work. 🚀"
            else:
                mock_response.text = f"Moderate energy at {current_hour}:00. Good for routine tasks and planning."
            
            return mock_response
        
        mock_llm_router.process_request = AsyncMock(side_effect=create_time_response)
        
        # Full day journey
        day_interactions = [
            (8, "Struggling to get started this morning, brain feels foggy"),
            (10, "Feeling more awake now, ready to tackle something important"),
            (12, "Energy is dipping, lunch time crash hitting"),
            (15, "Second wind kicking in, feeling productive again"),
            (18, "Getting tired, but want to finish up the day well")
        ]
        
        daily_results = []
        
        for hour, interaction in day_interactions:
            current_hour = hour
            
            result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input=interaction
            )
            
            assert result.success is True
            daily_results.append((hour, result.cognitive_load, result.response.text))
        
        # Verify energy-appropriate responses throughout the day
        morning_load = daily_results[0][1]  # 8am
        peak_load = daily_results[1][1]     # 10am  
        evening_load = daily_results[4][1]  # 6pm
        
        # Cognitive load should follow inverse energy pattern
        assert peak_load < morning_load, "Peak time should have lower cognitive load"
        assert evening_load > peak_load, "Evening should have higher cognitive load than peak"
        
        # Responses should be contextually appropriate
        for hour, load, response in daily_results:
            response_lower = response.lower()
            
            if hour == 8:  # Morning struggle
                assert "gentle" in response_lower or "recharge" in response_lower
            elif hour == 10:  # Peak energy
                assert "important" in response_lower or "tackle" in response_lower
            elif hour == 18:  # Evening
                assert "tired" in response_lower or "finish" in response_lower
        
        print("Full day ADHD journey test completed successfully!")
        for hour, load, response in daily_results:
            print(f"{hour}:00 - Load: {load:.2f} - {response[:60]}...")