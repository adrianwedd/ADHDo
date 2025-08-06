"""
End-to-end tests for complete user workflows.

Tests realistic user journeys and ADHD-optimized interactions.
"""
import pytest
import asyncio
import time
from datetime import datetime, timedelta


class TestUserOnboardingWorkflow:
    """Test complete user onboarding workflow."""

    @pytest.mark.e2e
    @pytest.mark.adhd
    async def test_new_user_complete_onboarding(self, async_client, performance_thresholds):
        """Test complete new user onboarding process."""
        # Step 1: Create new user account
        user_data = {
            "name": "Alex Thompson",
            "email": "alex.thompson@example.com",
            "timezone": "America/New_York",
            "preferred_nudge_methods": ["web", "telegram"],
            "energy_patterns": {
                "peak_hours": [9, 10, 11, 14, 15, 16],
                "low_hours": [12, 13, 17, 18, 19]
            },
            "hyperfocus_indicators": ["long_sessions", "delayed_responses"],
            "nudge_timing_preferences": {
                "morning": "09:30",
                "afternoon": "14:30",
                "evening": "18:00"
            }
        }
        
        start_time = time.time()
        user_response = await async_client.post("/api/users", json=user_data)
        assert user_response.status_code == 201
        
        user_id = user_response.json()["user_id"]
        registration_time = (time.time() - start_time) * 1000
        assert registration_time < performance_thresholds['max_response_time_ms']
        
        # Step 2: Create API key for ongoing access
        api_key_data = {
            "name": "Alex's Main API Key",
            "permissions": ["chat", "tasks", "users", "context"]
        }
        
        key_response = await async_client.post(f"/api/users/{user_id}/api-keys", json=api_key_data)
        assert key_response.status_code == 201
        
        api_key = key_response.json()["api_key"]
        headers = {"Authorization": f"Bearer {api_key}"}
        
        # Step 3: Create initial session
        session_data = {
            "duration_hours": 8,  # Work day session
            "user_agent": "Alex's ADHD Assistant/1.0"
        }
        
        session_response = await async_client.post(
            f"/api/users/{user_id}/sessions", 
            json=session_data, 
            headers=headers
        )
        assert session_response.status_code == 201
        
        # Step 4: Add first tasks to get started
        initial_tasks = [
            {
                "title": "Set up ADHD workspace",
                "description": "Organize desk and remove distractions",
                "priority": 3,
                "energy_required": "medium",
                "estimated_focus_time": 30,
                "tags": ["setup", "environment"]
            },
            {
                "title": "Review today's priorities",
                "description": "Go through task list and set daily focus",
                "priority": 5,
                "energy_required": "low",
                "estimated_focus_time": 15,
                "tags": ["planning", "daily"]
            },
            {
                "title": "Complete project proposal",
                "description": "Finish the Q1 project proposal draft",
                "priority": 4,
                "energy_required": "high",
                "estimated_focus_time": 90,
                "tags": ["work", "writing"],
                "hyperfocus_compatible": True
            }
        ]
        
        created_tasks = []
        for task_data in initial_tasks:
            task_data["user_id"] = user_id
            task_response = await async_client.post("/api/tasks", json=task_data, headers=headers)
            assert task_response.status_code == 201
            created_tasks.append(task_response.json())
        
        # Step 5: Test initial chat interaction
        welcome_chat = {
            "message": "Hi! I'm new here and feeling a bit overwhelmed. Can you help me get started?",
            "user_id": user_id,
            "context": {
                "is_new_user": True,
                "current_tasks": len(created_tasks),
                "energy_level": "medium"
            }
        }
        
        chat_response = await async_client.post("/api/chat", json=welcome_chat, headers=headers)
        assert chat_response.status_code == 200
        
        chat_data = chat_response.json()
        assert "response" in chat_data
        assert "suggestions" in chat_data
        
        # Response should be welcoming and not overwhelming
        assert len(chat_data["response"]) < 500  # Keep it concise for ADHD
        
        # Cognitive load should be managed for new user
        cognitive_load = float(chat_response.headers["X-Cognitive-Load"])
        assert cognitive_load < 0.7  # Moderate cognitive load for onboarding
        
        # Step 6: Get task suggestion for first activity
        suggestion_response = await async_client.get(
            f"/api/tasks/suggest?user_id={user_id}&current_energy=medium", 
            headers=headers
        )
        assert suggestion_response.status_code == 200
        
        suggestion_data = suggestion_response.json()
        if suggestion_data["suggested_task"]:
            suggested_task = suggestion_data["suggested_task"]
            # Should suggest appropriate task for medium energy new user
            assert suggested_task["energy_required"] in ["low", "medium"]
        
        # Verify complete onboarding workflow completed successfully
        assert len(created_tasks) == 3
        assert all(task["dopamine_reward_tier"] > 0 for task in created_tasks)


class TestDailyProductivityWorkflow:
    """Test typical daily productivity workflow."""

    @pytest.mark.e2e
    @pytest.mark.adhd
    @pytest.mark.slow
    async def test_full_day_adhd_workflow(self, async_client, adhd_helpers, performance_thresholds):
        """Test complete daily workflow for ADHD user."""
        # Setup: Create user and authenticate
        user_data = {
            "name": "Daily Workflow User",
            "email": "daily@workflow.example.com",
            "energy_patterns": {
                "peak_hours": [9, 10, 11, 15, 16],
                "low_hours": [12, 13, 14, 17, 18]
            }
        }
        
        user_response = await async_client.post("/api/users", json=user_data)
        user_id = user_response.json()["user_id"]
        
        # Morning session: High energy start
        morning_tasks = [
            {"title": "Review daily goals", "priority": 4, "energy_required": "medium", "estimated_focus_time": 15},
            {"title": "Deep work: Code review", "priority": 5, "energy_required": "high", "estimated_focus_time": 90},
            {"title": "Team standup meeting", "priority": 3, "energy_required": "low", "estimated_focus_time": 30}
        ]
        
        morning_task_ids = []
        for task_data in morning_tasks:
            task_data["user_id"] = user_id
            task_response = await async_client.post("/api/tasks", json=task_data)
            morning_task_ids.append(task_response.json()["task_id"])
        
        # Morning chat: High energy, ready to work
        morning_chat = {
            "message": "Good morning! I'm feeling energized and ready to tackle my day. What should I focus on?",
            "user_id": user_id,
            "context": {"time_of_day": "morning", "energy_level": "high", "focus_state": "ready"}
        }
        
        start_time = time.time()
        morning_response = await async_client.post("/api/chat", json=morning_chat)
        morning_time = (time.time() - start_time) * 1000
        
        assert morning_response.status_code == 200
        assert morning_time < performance_thresholds['max_response_time_ms']
        
        morning_cognitive_load = float(morning_response.headers["X-Cognitive-Load"])
        assert morning_cognitive_load < 0.5  # Low cognitive load when ready
        
        # Get morning task suggestion
        morning_suggestion = await async_client.get(
            f"/api/tasks/suggest?user_id={user_id}&current_energy=high&time_of_day=morning"
        )
        assert morning_suggestion.status_code == 200
        
        # Complete high-priority morning task
        if morning_suggestion.json()["suggested_task"]:
            suggested_task_id = morning_suggestion.json()["suggested_task"]["task_id"]
            complete_response = await async_client.post(f"/api/tasks/{suggested_task_id}/complete")
            assert complete_response.status_code == 200
            
            reward = complete_response.json()["reward"]
            assert reward["points"] > 0
        
        # Midday session: Energy dip, potential overwhelm
        midday_chat = {
            "message": "I'm hitting the afternoon slump and have so many things on my plate. Feeling scattered.",
            "user_id": user_id,
            "context": {"time_of_day": "afternoon", "energy_level": "low", "focus_state": "scattered"}
        }
        
        midday_response = await async_client.post("/api/chat", json=midday_chat)
        assert midday_response.status_code == 200
        
        midday_cognitive_load = float(midday_response.headers["X-Cognitive-Load"])
        assert midday_cognitive_load > 0.6  # Higher cognitive load when scattered
        
        # System should suggest break or low-energy task
        midday_suggestion = await async_client.get(
            f"/api/tasks/suggest?user_id={user_id}&current_energy=low&time_of_day=afternoon"
        )
        
        if midday_suggestion.json()["suggested_task"]:
            suggested_task = midday_suggestion.json()["suggested_task"]
            assert suggested_task["energy_required"] == "low"
        
        # Evening session: Winding down, planning tomorrow
        evening_tasks = [
            {"title": "Plan tomorrow's priorities", "priority": 2, "energy_required": "low", "estimated_focus_time": 20},
            {"title": "Quick email cleanup", "priority": 1, "energy_required": "low", "estimated_focus_time": 15}
        ]
        
        for task_data in evening_tasks:
            task_data["user_id"] = user_id
            await async_client.post("/api/tasks", json=task_data)
        
        evening_chat = {
            "message": "Wrapping up my day. I got some things done but could have been more focused. Any tips?",
            "user_id": user_id,
            "context": {"time_of_day": "evening", "energy_level": "medium", "focus_state": "reflective"}
        }
        
        evening_response = await async_client.post("/api/chat", json=evening_chat)
        assert evening_response.status_code == 200
        
        # Get user context at end of day
        context_response = await async_client.get(f"/api/users/{user_id}/context")
        assert context_response.status_code == 200
        
        context_data = context_response.json()
        assert "recent_interactions" in context_data
        assert "active_task_count" in context_data
        assert context_data["active_task_count"] > 0  # Should have remaining tasks


class TestTaskManagementWorkflow:
    """Test complete task management workflow."""

    @pytest.mark.e2e
    @pytest.mark.adhd
    async def test_task_lifecycle_with_adhd_features(self, async_client):
        """Test complete task lifecycle with ADHD-specific features."""
        # Setup user
        user_data = {"name": "Task Manager", "email": "tasks@example.com"}
        user_response = await async_client.post("/api/users", json=user_data)
        user_id = user_response.json()["user_id"]
        
        # Create complex task with ADHD features
        complex_task = {
            "title": "Write quarterly report",
            "description": "Comprehensive Q4 performance report with analysis and recommendations",
            "priority": 4,
            "energy_required": "high",
            "estimated_focus_time": 180,  # 3 hours
            "hyperfocus_compatible": True,
            "tags": ["writing", "analysis", "quarterly", "important"],
            "context_triggers": ["quiet_environment", "morning_energy", "deadline_pressure"],
            "preferred_time_blocks": ["morning"],
            "user_id": user_id
        }
        
        task_response = await async_client.post("/api/tasks", json=complex_task)
        assert task_response.status_code == 201
        
        task_data = task_response.json()
        task_id = task_data["task_id"]
        
        # Verify ADHD optimizations were applied
        assert task_data["dopamine_reward_tier"] == 4  # Matches priority
        assert task_data["hyperfocus_compatible"] is True
        assert task_data["estimated_focus_time"] == 180
        
        # Simulate task work session - user starts task
        start_work_chat = {
            "message": f"Starting work on task: {complex_task['title']}. I'm in the zone and ready to focus!",
            "user_id": user_id,
            "context": {
                "current_task_id": task_id,
                "focus_state": "entering_hyperfocus",
                "energy_level": "high"
            }
        }
        
        start_response = await async_client.post("/api/chat", json=start_work_chat)
        assert start_response.status_code == 200
        
        # Cognitive load should be manageable when focused
        start_cognitive_load = float(start_response.headers["X-Cognitive-Load"])
        assert start_cognitive_load < 0.6
        
        # Record trace of focus session start
        focus_trace = {
            "trace_type": "hyperfocus_start",
            "content": {
                "task_id": task_id,
                "focus_intensity": "high",
                "environment": "quiet_home_office"
            },
            "processing_time_ms": 25.0,
            "cognitive_load": 0.3,
            "was_successful": True,
            "source": "web"
        }
        
        trace_response = await async_client.post(f"/api/users/{user_id}/traces", json=focus_trace)
        assert trace_response.status_code == 201
        
        # Simulate mid-session check-in
        midsession_chat = {
            "message": "Making good progress on the report. About 60% done. Should I keep going or take a break?",
            "user_id": user_id,
            "context": {
                "current_task_id": task_id,
                "completion_estimate": 0.6,
                "session_duration_minutes": 90,
                "energy_level": "medium"
            }
        }
        
        mid_response = await async_client.post("/api/chat", json=midsession_chat)
        assert mid_response.status_code == 200
        
        # Complete the task
        completion_response = await async_client.post(f"/api/tasks/{task_id}/complete")
        assert completion_response.status_code == 200
        
        completion_data = completion_response.json()
        assert completion_data["status"] == "completed"
        assert completion_data["completion_percentage"] == 1.0
        
        # Verify dopamine reward
        reward = completion_data["reward"]
        assert reward["points"] == 40  # 4 (priority) * 10
        assert reward["celebration_level"] == 4
        assert "message" in reward
        
        # Post-completion reflection
        completion_chat = {
            "message": "Just finished the quarterly report! Feeling accomplished. That was a good focus session.",
            "user_id": user_id,
            "context": {
                "completed_task_id": task_id,
                "session_duration_minutes": 180,
                "satisfaction_level": "high"
            }
        }
        
        final_response = await async_client.post("/api/chat", json=completion_chat)
        assert final_response.status_code == 200
        
        # Record completion trace
        completion_trace = {
            "trace_type": "task_completion",
            "content": {
                "task_id": task_id,
                "completion_time_minutes": 180,
                "satisfaction": "high",
                "dopamine_reward": reward
            },
            "processing_time_ms": 30.0,
            "cognitive_load": 0.2,  # Low load after completion
            "was_successful": True,
            "source": "web"
        }
        
        final_trace_response = await async_client.post(f"/api/users/{user_id}/traces", json=completion_trace)
        assert final_trace_response.status_code == 201


class TestCrisisInterventionWorkflow:
    """Test crisis intervention and overwhelm management workflow."""

    @pytest.mark.e2e
    @pytest.mark.adhd
    async def test_overwhelm_detection_and_intervention(self, async_client):
        """Test system response to user overwhelm and crisis intervention."""
        # Setup user with high task load
        user_data = {"name": "Overwhelmed User", "email": "overwhelm@example.com"}
        user_response = await async_client.post("/api/users", json=user_data)
        user_id = user_response.json()["user_id"]
        
        # Create overwhelming task load (many high-priority tasks)
        overwhelming_tasks = [
            {"title": f"Urgent task {i}", "priority": 5, "energy_required": "high", "estimated_focus_time": 60}
            for i in range(8)
        ]
        
        for task_data in overwhelming_tasks:
            task_data["user_id"] = user_id
            await async_client.post("/api/tasks", json=task_data)
        
        # User expresses overwhelm
        overwhelm_chat = {
            "message": "I can't handle this anymore! I have 8 urgent tasks, 3 deadlines today, "
                      "and I don't know where to start. I'm completely overwhelmed and paralyzed.",
            "user_id": user_id,
            "context": {
                "stress_level": "critical",
                "task_count": 8,
                "deadlines_today": 3,
                "emotional_state": "overwhelmed"
            }
        }
        
        crisis_response = await async_client.post("/api/chat", json=overwhelm_chat)
        assert crisis_response.status_code == 200
        
        crisis_data = crisis_response.json()
        
        # System should detect high cognitive load
        crisis_cognitive_load = float(crisis_response.headers["X-Cognitive-Load"])
        assert crisis_cognitive_load >= 0.8  # Very high cognitive load
        
        # Response should include crisis intervention suggestions
        assert "suggestions" in crisis_data
        suggestions = crisis_data["suggestions"]
        
        # Should suggest specific interventions
        suggestion_types = [s.get("type", "") for s in suggestions]
        assert any("break" in stype for stype in suggestion_types)
        assert any("prioritize" in stype for stype in suggestion_types)
        
        # Record overwhelm detection
        overwhelm_trace = {
            "trace_type": "overwhelm_detection",
            "content": {
                "trigger": "high_task_count",
                "severity": 0.9,
                "task_count": 8,
                "emotional_indicators": ["paralyzed", "overwhelmed"]
            },
            "processing_time_ms": 100.0,
            "cognitive_load": 0.9,
            "was_successful": True,
            "source": "web"
        }
        
        trace_response = await async_client.post(f"/api/users/{user_id}/traces", json=overwhelm_trace)
        assert trace_response.status_code == 201
        
        # System suggests taking a break
        break_chat = {
            "message": "Ok, I'll try to take a 5-minute break like you suggested.",
            "user_id": user_id,
            "context": {
                "following_suggestion": True,
                "break_type": "micro",
                "duration_minutes": 5
            }
        }
        
        break_response = await async_client.post("/api/chat", json=break_chat)
        assert break_response.status_code == 200
        
        # After break, ask for prioritization help
        priority_chat = {
            "message": "I took the break. Now I need help prioritizing these 8 tasks. "
                      "What should I tackle first?",
            "user_id": user_id,
            "context": {
                "post_break": True,
                "energy_level": "medium",
                "needs_prioritization": True
            }
        }
        
        priority_response = await async_client.post("/api/chat", json=priority_chat)
        assert priority_response.status_code == 200
        
        # System should suggest manageable next step
        priority_data = priority_response.json()
        assert "suggestions" in priority_data
        
        # Cognitive load should be lower after intervention
        priority_cognitive_load = float(priority_response.headers["X-Cognitive-Load"])
        assert priority_cognitive_load < crisis_cognitive_load
        
        # Get task suggestion with overwhelm context
        recovery_suggestion = await async_client.get(
            f"/api/tasks/suggest?user_id={user_id}&current_energy=medium&context=post_overwhelm"
        )
        assert recovery_suggestion.status_code == 200
        
        if recovery_suggestion.json()["suggested_task"]:
            suggested_task = recovery_suggestion.json()["suggested_task"]
            # Should suggest manageable task to build confidence
            assert suggested_task["energy_required"] in ["low", "medium"]


class TestHyperfocusWorkflow:
    """Test hyperfocus session management workflow."""

    @pytest.mark.e2e
    @pytest.mark.adhd
    async def test_hyperfocus_session_management(self, async_client):
        """Test hyperfocus detection, support, and transition management."""
        # Setup user
        user_data = {
            "name": "Hyperfocus User",
            "email": "hyperfocus@example.com",
            "hyperfocus_indicators": ["long_sessions", "delayed_responses", "deep_engagement"]
        }
        user_response = await async_client.post("/api/users", json=user_data)
        user_id = user_response.json()["user_id"]
        
        # Create hyperfocus-compatible task
        hyperfocus_task = {
            "title": "Build new feature prototype",
            "description": "Create working prototype of the new dashboard feature",
            "priority": 5,
            "energy_required": "high",
            "estimated_focus_time": 240,  # 4 hours
            "hyperfocus_compatible": True,
            "tags": ["development", "creative", "complex"],
            "user_id": user_id
        }
        
        task_response = await async_client.post("/api/tasks", json=hyperfocus_task)
        task_id = task_response.json()["task_id"]
        
        # User indicates entering hyperfocus
        hyperfocus_entry = {
            "message": "I'm really excited about this prototype project. I want to dive deep and "
                      "work on it for several hours without interruption.",
            "user_id": user_id,
            "context": {
                "current_task_id": task_id,
                "focus_intention": "deep_work",
                "estimated_session_hours": 4,
                "interruption_preference": "minimal"
            }
        }
        
        entry_response = await async_client.post("/api/chat", json=hyperfocus_entry)
        assert entry_response.status_code == 200
        
        entry_data = entry_response.json()
        
        # System should recognize hyperfocus intention
        entry_suggestions = entry_data.get("suggestions", [])
        hyperfocus_support = any("hyperfocus" in str(s) for s in entry_suggestions)
        
        # Record hyperfocus session start
        hyperfocus_start_trace = {
            "trace_type": "hyperfocus_start",
            "content": {
                "task_id": task_id,
                "estimated_duration_hours": 4,
                "focus_intensity": "high",
                "environment_setup": "optimized"
            },
            "processing_time_ms": 20.0,
            "cognitive_load": 0.3,  # Low load when in flow
            "was_successful": True,
            "source": "web"
        }
        
        start_trace_response = await async_client.post(f"/api/users/{user_id}/traces", json=hyperfocus_start_trace)
        assert start_trace_response.status_code == 201
        
        # Simulate 2-hour check (mid-session)
        mid_session_chat = {
            "message": "Been working for 2 hours straight. Making amazing progress but haven't "
                      "taken any breaks. Should I continue?",
            "user_id": user_id,
            "context": {
                "current_task_id": task_id,
                "session_duration_hours": 2,
                "progress_feeling": "excellent",
                "break_count": 0
            }
        }
        
        mid_response = await async_client.post("/api/chat", json=mid_session_chat)
        assert mid_response.status_code == 200
        
        mid_data = mid_response.json()
        
        # System should balance hyperfocus support with health
        assert "suggestions" in mid_data
        
        # Simulate hyperfocus end (4 hours later)
        hyperfocus_end = {
            "message": "Just finished! Got so much done on the prototype. Feeling amazing but also "
                      "completely drained now.",
            "user_id": user_id,
            "context": {
                "completed_task_id": task_id,
                "session_duration_hours": 4,
                "satisfaction_level": "very_high",
                "energy_level": "depleted"
            }
        }
        
        end_response = await async_client.post("/api/chat", json=hyperfocus_end)
        assert end_response.status_code == 200
        
        end_data = end_response.json()
        
        # System should provide post-hyperfocus support
        assert "suggestions" in end_data
        end_suggestions = end_data["suggestions"]
        
        # Should suggest recovery activities
        recovery_suggestions = any("rest" in str(s) or "break" in str(s) for s in end_suggestions)
        
        # Complete the task with high satisfaction
        completion_response = await async_client.post(f"/api/tasks/{task_id}/complete")
        assert completion_response.status_code == 200
        
        reward_data = completion_response.json()["reward"]
        assert reward_data["points"] == 50  # High reward for high-priority task
        
        # Record hyperfocus session end
        hyperfocus_end_trace = {
            "trace_type": "hyperfocus_end",
            "content": {
                "task_id": task_id,
                "actual_duration_hours": 4,
                "completion_status": "completed",
                "satisfaction": "very_high",
                "energy_depletion": "high"
            },
            "processing_time_ms": 25.0,
            "cognitive_load": 0.8,  # High load post-hyperfocus
            "was_successful": True,
            "source": "web"
        }
        
        end_trace_response = await async_client.post(f"/api/users/{user_id}/traces", json=hyperfocus_end_trace)
        assert end_trace_response.status_code == 201


class TestSystemPerformanceWorkflow:
    """Test system performance under realistic usage."""

    @pytest.mark.e2e
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_concurrent_user_performance(self, async_client, performance_thresholds):
        """Test system performance with multiple concurrent users."""
        import asyncio
        
        async def single_user_simulation(user_index):
            """Simulate a single user's typical workflow."""
            # Create user
            user_data = {
                "name": f"Concurrent User {user_index}",
                "email": f"user{user_index}@concurrent.test"
            }
            
            user_response = await async_client.post("/api/users", json=user_data)
            if user_response.status_code != 201:
                return {"user_index": user_index, "success": False, "error": "user_creation_failed"}
            
            user_id = user_response.json()["user_id"]
            
            # Simulate typical user actions
            actions = [
                # Create a task
                async_client.post("/api/tasks", json={
                    "title": f"User {user_index} Task",
                    "user_id": user_id,
                    "priority": 3
                }),
                
                # Chat interaction
                async_client.post("/api/chat", json={
                    "message": "I need help staying focused today.",
                    "user_id": user_id
                }),
                
                # Get task suggestions
                async_client.get(f"/api/tasks/suggest?user_id={user_id}&current_energy=medium"),
                
                # Check health
                async_client.get("/health")
            ]
            
            start_time = time.time()
            results = await asyncio.gather(*actions, return_exceptions=True)
            total_time = (time.time() - start_time) * 1000
            
            # Check results
            success_count = 0
            for result in results:
                if not isinstance(result, Exception) and hasattr(result, 'status_code'):
                    if result.status_code in [200, 201]:
                        success_count += 1
            
            return {
                "user_index": user_index,
                "success": success_count >= 3,  # At least 3 out of 4 actions successful
                "total_time_ms": total_time,
                "success_rate": success_count / len(actions)
            }
        
        # Run 5 concurrent user simulations
        user_count = 5
        tasks = [single_user_simulation(i) for i in range(user_count)]
        results = await asyncio.gather(*tasks)
        
        # Analyze results
        successful_users = [r for r in results if r["success"]]
        total_times = [r["total_time_ms"] for r in results if r["success"]]
        
        # Performance assertions
        assert len(successful_users) >= 4  # At least 80% success rate
        
        if total_times:
            avg_time = sum(total_times) / len(total_times)
            max_time = max(total_times)
            
            # Should handle concurrent load reasonably
            assert avg_time < performance_thresholds['max_response_time_ms'] * 2  # Allow 2x for concurrency
            assert max_time < performance_thresholds['max_response_time_ms'] * 3   # Allow 3x for worst case


class TestDataConsistencyWorkflow:
    """Test data consistency across the system."""

    @pytest.mark.e2e
    @pytest.mark.database
    async def test_cross_endpoint_data_consistency(self, async_client):
        """Test data consistency between different API endpoints."""
        # Create user
        user_data = {"name": "Consistency Test User", "email": "consistency@test.com"}
        user_response = await async_client.post("/api/users", json=user_data)
        assert user_response.status_code == 201
        
        user_id = user_response.json()["user_id"]
        
        # Create task
        task_data = {
            "title": "Consistency Test Task",
            "user_id": user_id,
            "priority": 4,
            "energy_required": "medium"
        }
        
        task_response = await async_client.post("/api/tasks", json=task_data)
        assert task_response.status_code == 201
        
        task_id = task_response.json()["task_id"]
        
        # Get user profile - should reflect task creation
        profile_response = await async_client.get(f"/api/users/{user_id}")
        assert profile_response.status_code == 200
        
        # Get task list - should include created task
        tasks_response = await async_client.get(f"/api/tasks?user_id={user_id}")
        assert tasks_response.status_code == 200
        
        tasks_data = tasks_response.json()
        task_found = False
        for task in tasks_data.get("tasks", []):
            if task["task_id"] == task_id:
                task_found = True
                assert task["title"] == task_data["title"]
                assert task["priority"] == task_data["priority"]
                break
        
        assert task_found, "Created task should appear in task list"
        
        # Update task progress
        progress_update = {"completion_percentage": 0.5}
        update_response = await async_client.put(f"/api/tasks/{task_id}/progress", json=progress_update)
        
        if update_response.status_code == 200:
            # Verify update is reflected across endpoints
            updated_task_response = await async_client.get(f"/api/tasks/{task_id}")
            if updated_task_response.status_code == 200:
                updated_task = updated_task_response.json()
                assert updated_task["completion_percentage"] == 0.5
        
        # Complete task
        complete_response = await async_client.post(f"/api/tasks/{task_id}/complete")
        assert complete_response.status_code == 200
        
        # Verify completion is consistent across endpoints
        final_task_response = await async_client.get(f"/api/tasks/{task_id}")
        if final_task_response.status_code == 200:
            final_task = final_task_response.json()
            assert final_task["status"] == "completed"
            assert final_task["completion_percentage"] == 1.0