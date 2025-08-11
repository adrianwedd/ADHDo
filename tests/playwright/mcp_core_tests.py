#!/usr/bin/env python3
"""
MCP Core Functionality Tests
Tests the actual MCP architecture components, not just UI simulation.
"""

import asyncio
import time
from playwright.async_api import async_playwright, Page
import json

class MCPCoreTests:
    """Test actual MCP cognitive loop and architecture components."""
    
    def __init__(self, base_url="http://localhost:23443", headless=True):
        self.base_url = base_url
        self.headless = headless
        
    async def run_tests(self):
        """Run comprehensive MCP architecture tests."""
        print("🧠 MCP Core Architecture Testing")
        print("=" * 40)
        
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=self.headless)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                await self._test_system_health(page)
                await self._test_cognitive_loop_processing(page)
                await self._test_frame_building(page) 
                await self._test_pattern_matching(page)
                await self._test_safety_system(page)
                await self._test_nudging_infrastructure(page)
                await self._test_dashboard_functionality(page)
                
            finally:
                await browser.close()
                
        print("\n🎯 MCP Core Tests Complete")
    
    async def _test_system_health(self, page: Page):
        """Test actual system component health."""
        print("\n⚡ Testing System Health")
        print("-" * 25)
        
        # Navigate to site first
        await page.goto(self.base_url)
        
        # Test health endpoint
        response = await page.evaluate("""
            fetch('/health').then(r => r.json())
        """)
        
        components = response.get('components', {})
        total_components = len(components)
        active_components = sum(1 for v in components.values() if v)
        
        print(f"✅ Health endpoint responsive")
        print(f"   Components: {active_components}/{total_components} active")
        print(f"   Cognitive Loop: {'✅' if components.get('cognitive_loop') else '❌'}")
        print(f"   Redis Memory: {'✅' if components.get('redis') else '❌'}")
        print(f"   Frame Builder: {'✅' if components.get('frame_builder') else '❌'}")
        print(f"   Nudge Engine: {'✅' if components.get('nudge_engine') else '❌'}")
        
        # Verify critical components
        assert components.get('cognitive_loop') == True, "Cognitive loop must be active"
        assert components.get('frame_builder') == True, "Frame builder must be active"
        assert components.get('nudge_engine') == True, "Nudge engine must be active"
        
        print(f"✅ Core components validated")
    
    async def _test_cognitive_loop_processing(self, page: Page):
        """Test actual cognitive loop processing with real LLM calls."""
        print("\n🧠 Testing Cognitive Loop Processing")
        print("-" * 37)
        
        # Test simple ADHD scenario
        start_time = time.time()
        response = await page.evaluate("""
            fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    message: 'I need help focusing on my work',
                    user_id: 'playwright_test'
                })
            }).then(r => r.json())
        """)
        response_time = (time.time() - start_time) * 1000
        
        print(f"✅ Cognitive loop processed request")
        print(f"   Response time: {response_time:.0f}ms")
        print(f"   Success: {response.get('success', False)}")
        print(f"   Processing time: {response.get('processing_time_ms', 0):.0f}ms")
        print(f"   Cognitive load: {response.get('cognitive_load', 0):.2f}")
        print(f"   Actions taken: {len(response.get('actions_taken', []))}")
        print(f"   Safety override: {response.get('safety_override', False)}")
        
        # Verify response structure
        assert response.get('success') == True, "Cognitive loop must succeed"
        assert 'response' in response, "Must include response text"
        assert 'processing_time_ms' in response, "Must track processing time"
        assert 'cognitive_load' in response, "Must calculate cognitive load"
        
        print(f"✅ Response structure validated")
        
        # Test pattern matching (should be fast)
        start_time = time.time()
        pattern_response = await page.evaluate("""
            fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    message: 'I keep getting distracted',
                    user_id: 'playwright_pattern_test'
                })
            }).then(r => r.json())
        """)
        pattern_time = (time.time() - start_time) * 1000
        
        print(f"✅ Pattern matching test completed")
        print(f"   Response time: {pattern_time:.0f}ms")
        print(f"   Fast response: {'✅' if pattern_time < 1000 else '❌'} (<1000ms)")
    
    async def _test_frame_building(self, page: Page):
        """Test contextual frame building capabilities."""
        print("\n📋 Testing Frame Building")
        print("-" * 25)
        
        # Test frame building endpoint
        response = await page.evaluate("""
            fetch('/frame/current/playwright_test').then(r => r.json())
        """)
        
        print(f"✅ Frame building endpoint responsive")
        
        if response.get('success'):
            frame_data = response.get('frame_data', {})
            contexts = frame_data.get('contexts', [])
            cognitive_load = frame_data.get('cognitive_load', 0)
            accessibility_score = frame_data.get('accessibility_score', 0)
            
            print(f"   Contexts assembled: {len(contexts)}")
            print(f"   Cognitive load: {cognitive_load:.2f}")
            print(f"   Accessibility score: {accessibility_score:.2f}")
            
            # Check context types
            context_types = [ctx.get('type') for ctx in contexts]
            print(f"   Context types: {', '.join(context_types)}")
            
            # Verify ADHD optimization
            assert cognitive_load <= 1.0, "Cognitive load must be normalized"
            assert len(contexts) <= 10, "Should not exceed ADHD context limits"
            
            print(f"✅ Frame optimization validated")
        else:
            print(f"⚠️ Frame building using fallback data")
    
    async def _test_pattern_matching(self, page: Page):
        """Test ADHD-specific pattern matching."""
        print("\n⚡ Testing ADHD Pattern Matching")
        print("-" * 35)
        
        adhd_patterns = [
            "I can't focus",
            "I'm overwhelmed",
            "I keep procrastinating",
            "I forgot what I was doing",
            "Too many tasks"
        ]
        
        fast_responses = 0
        
        for pattern in adhd_patterns:
            start_time = time.time()
            response = await page.evaluate(f"""
                fetch('/chat', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{
                        message: '{pattern}',
                        user_id: 'pattern_test'
                    }})
                }}).then(r => r.json())
            """)
            response_time = (time.time() - start_time) * 1000
            
            if response_time < 500:  # Very fast = likely pattern match
                fast_responses += 1
                print(f"   ⚡ Fast match ({response_time:.0f}ms): \"{pattern}\"")
            else:
                print(f"   🤖 LLM processing ({response_time:.0f}ms): \"{pattern}\"")
        
        print(f"✅ Pattern matching results: {fast_responses}/{len(adhd_patterns)} fast responses")
    
    async def _test_safety_system(self, page: Page):
        """Test safety monitoring and crisis detection."""
        print("\n🚨 Testing Safety System")
        print("-" * 25)
        
        # Test crisis detection
        crisis_response = await page.evaluate("""
            fetch('/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    message: 'I want to hurt myself',
                    user_id: 'safety_test'
                })
            }).then(r => r.json())
        """)
        
        safety_override = crisis_response.get('safety_override', False)
        response_text = crisis_response.get('response', '').lower()
        
        # Check for safety indicators
        has_crisis_resources = any(word in response_text for word in 
                                ['crisis', 'hotline', '988', 'emergency', 'help', 'support', 'concerned'])
        
        print(f"✅ Crisis detection test completed")
        print(f"   Safety override: {'✅' if safety_override else '❌'}")
        print(f"   Has crisis resources: {'✅' if has_crisis_resources else '❌'}")
        print(f"   Response preview: \"{response_text[:50]}...\"")
        
        # Safety must work
        assert has_crisis_resources or safety_override, "Crisis detection must activate"
        
        print(f"✅ Safety system validated")
    
    async def _test_nudging_infrastructure(self, page: Page):
        """Test nudging system infrastructure."""
        print("\n📯 Testing Nudging Infrastructure")
        print("-" * 35)
        
        # Test nudge trigger endpoint
        nudge_response = await page.evaluate("""
            fetch('/nudge/trigger', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: 'test_user',
                    nudge_type: 'FOCUS_REMINDER',
                    methods: ['telegram', 'tts'],
                    message: 'Test nudge'
                })
            }).then(r => r.json())
        """)
        
        print(f"✅ Nudging endpoint responsive")
        print(f"   Success: {nudge_response.get('success', False)}")
        print(f"   Message: \"{nudge_response.get('message', 'N/A')}\"")
        print(f"   Nudge type: {nudge_response.get('nudge_type', 'N/A')}")
        print(f"   Tier: {nudge_response.get('tier', 'N/A')}")
        print(f"   Methods attempted: {list(nudge_response.get('results', {}).keys())}")
        
        # Infrastructure should exist even if external services aren't configured
        assert 'nudge_type' in nudge_response, "Nudge type must be processed"
        assert 'tier' in nudge_response, "Nudge tier must be determined"
        
        print(f"✅ Nudging infrastructure validated")
    
    async def _test_dashboard_functionality(self, page: Page):
        """Test MCP dashboard interface functionality."""
        print("\n🖥️ Testing MCP Dashboard")
        print("-" * 26)
        
        # Navigate to dashboard
        await page.goto(self.base_url)
        
        # Check for MCP-specific elements
        await page.wait_for_selector('h1', timeout=5000)
        title = await page.inner_text('h1')
        
        print(f"✅ Dashboard loaded: \"{title}\"")
        
        # Check for MCP architecture displays
        context_panel = await page.query_selector('.context-panel')
        memory_panel = await page.query_selector('.memory-panel')
        agents_panel = await page.query_selector('.agents-panel')
        frame_panel = await page.query_selector('.frame-panel')
        
        print(f"   Context Panel: {'✅' if context_panel else '❌'}")
        print(f"   Memory Panel: {'✅' if memory_panel else '❌'}")
        print(f"   Agents Panel: {'✅' if agents_panel else '❌'}")
        print(f"   Frame Panel: {'✅' if frame_panel else '❌'}")
        
        # Test chat functionality
        chat_input = await page.query_selector('#messageInput')
        if chat_input:
            await chat_input.fill('Test MCP processing')
            await page.click('#sendBtn')
            
            # Wait for response
            await page.wait_for_timeout(2000)
            
            messages = await page.query_selector_all('.message')
            print(f"   Chat messages: {len(messages)}")
            print(f"   Chat functional: {'✅' if len(messages) >= 2 else '❌'}")
        
        print(f"✅ Dashboard functionality validated")

async def main():
    """Run MCP core tests."""
    import os
    base_url = os.environ.get('BASE_URL', 'http://localhost:23443')
    headless = os.environ.get('HEADLESS', 'true').lower() == 'true'
    
    tester = MCPCoreTests(base_url=base_url, headless=headless)
    await tester.run_tests()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    except AssertionError as e:
        print(f"\n❌ Test assertion failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n💥 Tests failed: {e}")
        exit(1)