#!/usr/bin/env python3
"""
Comprehensive System Test Suite for MCP ADHD Server
Tests all components and reports what's working/broken
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime
from typing import Dict, List, Tuple

BASE_URL = "http://localhost:23443"

class SystemTester:
    def __init__(self):
        self.results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }
        
    async def run_all_tests(self):
        """Run comprehensive test suite."""
        print("🧪 MCP ADHD SERVER - COMPREHENSIVE SYSTEM TEST")
        print("=" * 60)
        
        tests = [
            ("Health Check", self.test_health),
            ("Music System Initialization", self.test_music_init),
            ("Music Playback Commands", self.test_music_playback),
            ("Cognitive Loop - Basic Chat", self.test_basic_chat),
            ("Cognitive Loop - Music Intent", self.test_music_intent),
            ("Cognitive Loop - Action Execution", self.test_action_execution),
            ("Dashboard UI Components", self.test_dashboard),
            ("Context Building", self.test_context_building),
            ("LLM Response Quality", self.test_llm_quality),
            ("Performance Metrics", self.test_performance),
        ]
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            for test_name, test_func in tests:
                print(f"\n📋 Testing: {test_name}")
                print("-" * 40)
                try:
                    success, details = await test_func()
                    if success:
                        self.results["passed"].append((test_name, details))
                        print(f"✅ PASSED: {details}")
                    else:
                        self.results["failed"].append((test_name, details))
                        print(f"❌ FAILED: {details}")
                except Exception as e:
                    self.results["failed"].append((test_name, str(e)))
                    print(f"💥 ERROR: {e}")
        
        self.print_summary()
        return self.results
    
    async def test_health(self) -> Tuple[bool, str]:
        """Test system health endpoint."""
        async with self.session.get(f"{BASE_URL}/health") as resp:
            if resp.status == 200:
                data = await resp.json()
                components = data.get("components", {})
                working = [k for k, v in components.items() if v]
                not_working = [k for k, v in components.items() if not v]
                
                if not_working:
                    self.results["warnings"].append(f"Components offline: {', '.join(not_working)}")
                
                return True, f"System healthy. Working: {len(working)}, Offline: {len(not_working)}"
            return False, f"Health check failed: {resp.status}"
    
    async def test_music_init(self) -> Tuple[bool, str]:
        """Test music system initialization."""
        async with self.session.post(f"{BASE_URL}/music/initialize") as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("success"):
                    return True, "Music system initialized successfully"
                return False, f"Music init failed: {data.get('message', 'Unknown error')}"
            return False, f"Music init endpoint error: {resp.status}"
    
    async def test_music_playback(self) -> Tuple[bool, str]:
        """Test music playback commands."""
        failures = []
        
        # Test status
        async with self.session.get(f"{BASE_URL}/music/status") as resp:
            if resp.status != 200:
                failures.append("Status check failed")
            else:
                data = await resp.json()
                if not data.get("available"):
                    failures.append("Music system not available")
        
        # Test play focus
        async with self.session.post(f"{BASE_URL}/music/focus") as resp:
            if resp.status == 200:
                data = await resp.json()
                if not data.get("success"):
                    failures.append(f"Focus music failed: {data.get('message')}")
            else:
                failures.append(f"Focus endpoint error: {resp.status}")
        
        if failures:
            return False, f"Music issues: {'; '.join(failures)}"
        return True, "All music endpoints functional"
    
    async def test_basic_chat(self) -> Tuple[bool, str]:
        """Test basic chat functionality."""
        payload = {
            "message": "Hello, how are you?",
            "task_focus": "Testing",
            "nudge_tier": 0
        }
        
        async with self.session.post(f"{BASE_URL}/chat", json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("success") and data.get("response"):
                    response_time = data.get("processing_time_ms", 0)
                    if response_time > 30000:  # 30 seconds
                        self.results["warnings"].append(f"Slow response: {response_time}ms")
                    return True, f"Chat working. Response time: {response_time:.0f}ms"
                return False, "Chat returned no response"
            return False, f"Chat endpoint error: {resp.status}"
    
    async def test_music_intent(self) -> Tuple[bool, str]:
        """Test music intent recognition in cognitive loop."""
        payload = {
            "message": "play me some music",
            "task_focus": "Testing music",
            "nudge_tier": 0
        }
        
        async with self.session.post(f"{BASE_URL}/chat", json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                actions = data.get("actions_taken", [])
                
                if any("music" in action for action in actions):
                    return True, f"Music intent recognized. Actions: {actions}"
                else:
                    return False, f"Music intent not recognized. Actions: {actions}"
            return False, f"Chat endpoint error: {resp.status}"
    
    async def test_action_execution(self) -> Tuple[bool, str]:
        """Test if actions are actually executed."""
        payload = {
            "message": "play focus music please",
            "task_focus": "Deep work",
            "nudge_tier": 0
        }
        
        async with self.session.post(f"{BASE_URL}/chat", json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                actions = data.get("actions_taken", [])
                
                if actions:
                    return True, f"Actions executed: {actions}"
                else:
                    self.results["warnings"].append("Intent recognized but no actions executed")
                    return False, "No actions executed despite intent"
            return False, f"Chat endpoint error: {resp.status}"
    
    async def test_dashboard(self) -> Tuple[bool, str]:
        """Test dashboard UI availability."""
        async with self.session.get(f"{BASE_URL}/") as resp:
            if resp.status == 200:
                html = await resp.text()
                
                required_components = [
                    "Cognitive Loop Interface",
                    "Now Playing",
                    "Context RAM",
                    "Active Agents"
                ]
                
                missing = [comp for comp in required_components if comp not in html]
                
                if missing:
                    return False, f"Missing UI components: {', '.join(missing)}"
                return True, "All dashboard components present"
            return False, f"Dashboard not accessible: {resp.status}"
    
    async def test_context_building(self) -> Tuple[bool, str]:
        """Test context building in cognitive loop."""
        payload = {
            "message": "I need to focus on my project",
            "task_focus": "Project work",
            "nudge_tier": 0
        }
        
        async with self.session.post(f"{BASE_URL}/chat", json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                cognitive_load = data.get("cognitive_load", 0)
                
                if 0.3 <= cognitive_load <= 0.8:
                    return True, f"Context building working. Load: {cognitive_load:.2f}"
                else:
                    return False, f"Unexpected cognitive load: {cognitive_load}"
            return False, f"Chat endpoint error: {resp.status}"
    
    async def test_llm_quality(self) -> Tuple[bool, str]:
        """Test LLM response quality."""
        test_prompts = [
            "I'm feeling overwhelmed",
            "Help me start this task",
            "I can't focus"
        ]
        
        issues = []
        for prompt in test_prompts:
            payload = {"message": prompt, "task_focus": "Testing", "nudge_tier": 0}
            
            async with self.session.post(f"{BASE_URL}/chat", json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    response = data.get("response", "")
                    
                    # Check for common issues
                    if "I'm having trouble thinking" in response:
                        issues.append(f"Fallback response for: '{prompt}'")
                    elif len(response) < 10:
                        issues.append(f"Too short response for: '{prompt}'")
                    elif "<think>" in response:
                        issues.append(f"Thinking tags leaked for: '{prompt}'")
        
        if issues:
            return False, f"LLM issues: {'; '.join(issues)}"
        return True, "LLM responses appropriate"
    
    async def test_performance(self) -> Tuple[bool, str]:
        """Test system performance metrics."""
        # Quick response test
        payload = {
            "message": "ready to work",
            "task_focus": "Testing",
            "nudge_tier": 0
        }
        
        start = datetime.now()
        async with self.session.post(f"{BASE_URL}/chat", json=payload) as resp:
            elapsed = (datetime.now() - start).total_seconds() * 1000
            
            if resp.status == 200:
                data = await resp.json()
                reported_time = data.get("processing_time_ms", 0)
                
                if elapsed < 3000:  # Under 3 seconds
                    return True, f"Good performance: {elapsed:.0f}ms total, {reported_time:.0f}ms processing"
                else:
                    return False, f"Slow performance: {elapsed:.0f}ms total"
            return False, f"Performance test failed: {resp.status}"
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total = len(self.results["passed"]) + len(self.results["failed"])
        pass_rate = (len(self.results["passed"]) / total * 100) if total > 0 else 0
        
        print(f"\n✅ Passed: {len(self.results['passed'])}/{total} ({pass_rate:.1f}%)")
        print(f"❌ Failed: {len(self.results['failed'])}/{total}")
        print(f"⚠️  Warnings: {len(self.results['warnings'])}")
        
        if self.results["failed"]:
            print("\n🔴 FAILED TESTS:")
            for test_name, details in self.results["failed"]:
                print(f"  - {test_name}: {details}")
        
        if self.results["warnings"]:
            print("\n⚠️ WARNINGS:")
            for warning in self.results["warnings"]:
                print(f"  - {warning}")
        
        print("\n📋 GITHUB ISSUES TO CREATE/UPDATE:")
        if any("music" in str(f).lower() for f in self.results["failed"]):
            print("  - Music System Integration Issues")
        if any("action" in str(f).lower() for f in self.results["failed"]):
            print("  - Action Execution Pipeline Issues")
        if any("llm" in str(f).lower() or "response" in str(f).lower() for f in self.results["failed"]):
            print("  - LLM Response Quality Issues")
        
        return pass_rate >= 70  # Consider successful if 70% pass


async def main():
    tester = SystemTester()
    results = await tester.run_all_tests()
    
    # Return exit code based on results
    passed = len(results["passed"])
    failed = len(results["failed"])
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    elif passed > failed:
        print("\n⚠️ PARTIAL SUCCESS - Some issues to fix")
        return 1
    else:
        print("\n❌ CRITICAL ISSUES - Major fixes needed")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)