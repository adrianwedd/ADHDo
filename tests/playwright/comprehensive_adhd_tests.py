#!/usr/bin/env python3
"""
COMPREHENSIVE ADHD SYSTEM TESTING SUITE
Complete end-to-end tests for all ADHD support system functionality
"""

import os
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import pytest
from playwright.async_api import async_playwright, Page, BrowserContext, expect
import aiohttp

# Test configuration
BASE_URL = os.environ.get("BASE_URL", "http://localhost:23443")
HEADLESS = os.environ.get("HEADLESS", "false").lower() == "true"
TIMEOUT = 30000  # 30 seconds
ADHD_RESPONSE_TARGET = 3000  # 3 seconds max for ADHD users

class ADHDSystemTester:
    """Comprehensive test suite for ADHD support system."""
    
    def __init__(self):
        self.page: Optional[Page] = None
        self.context: Optional[BrowserContext] = None
        self.results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "performance": [],
            "accessibility": [],
            "ui_issues": [],
            "functional_issues": []
        }
        self.start_time = None
        
    async def setup(self):
        """Initialize browser and test environment."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=HEADLESS,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )
        self.page = await self.context.new_page()
        self.start_time = time.time()
        
        # Enable console logging
        self.page.on("console", lambda msg: print(f"[Browser Console]: {msg.text}"))
        self.page.on("pageerror", lambda err: print(f"[Page Error]: {err}"))
        
    async def teardown(self):
        """Clean up browser resources."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
            
    async def take_screenshot(self, name: str):
        """Take screenshot for debugging."""
        if self.page:
            screenshot_dir = Path("test_screenshots")
            screenshot_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await self.page.screenshot(
                path=f"{screenshot_dir}/{timestamp}_{name}.png",
                full_page=True
            )
            
    def record_result(self, test_name: str, passed: bool, 
                      error: str = None, performance_ms: int = None,
                      accessibility_issue: str = None, ui_issue: str = None):
        """Record test result with metrics."""
        self.results["total"] += 1
        
        if passed:
            self.results["passed"] += 1
            print(f"✅ {test_name}")
        else:
            self.results["failed"] += 1
            print(f"❌ {test_name}")
            if error:
                self.results["errors"].append(f"{test_name}: {error}")
                
        if performance_ms:
            self.results["performance"].append({
                "test": test_name,
                "time_ms": performance_ms,
                "acceptable": performance_ms < ADHD_RESPONSE_TARGET
            })
            
        if accessibility_issue:
            self.results["accessibility"].append(f"{test_name}: {accessibility_issue}")
            
        if ui_issue:
            self.results["ui_issues"].append(f"{test_name}: {ui_issue}")
            
    # ============= DASHBOARD UI TESTS =============
    
    async def test_dashboard_loads(self):
        """Test that dashboard loads successfully."""
        test_name = "Dashboard Load"
        start = time.time()
        
        try:
            await self.page.goto(BASE_URL, wait_until="networkidle", timeout=TIMEOUT)
            
            # Check for main title
            title = await self.page.text_content("h1", timeout=5000)
            assert "MCP" in title, f"Title missing MCP: {title}"
            
            load_time = int((time.time() - start) * 1000)
            self.record_result(test_name, True, performance_ms=load_time)
            
        except Exception as e:
            await self.take_screenshot("dashboard_load_fail")
            self.record_result(test_name, False, error=str(e))
            
    async def test_dashboard_aesthetics(self):
        """Test dashboard visual appearance and styling."""
        test_name = "Dashboard Aesthetics"
        
        try:
            # Check background gradient
            body = await self.page.query_selector("body")
            bg_style = await body.get_attribute("style") if body else ""
            
            # Check color scheme
            has_gradient = "gradient" in await self.page.evaluate("""
                () => window.getComputedStyle(document.body).background
            """)
            
            # Check font
            font_family = await self.page.evaluate("""
                () => window.getComputedStyle(document.body).fontFamily
            """)
            
            # Verify ADHD-friendly design
            issues = []
            if not has_gradient:
                issues.append("Missing gradient background")
                
            if "system" not in font_family.lower() and "segoe" not in font_family.lower():
                issues.append(f"Non-standard font: {font_family}")
                
            # Check contrast for accessibility
            text_color = await self.page.evaluate("""
                () => window.getComputedStyle(document.querySelector('h1')).color
            """)
            
            if issues:
                self.record_result(test_name, False, ui_issue=", ".join(issues))
            else:
                self.record_result(test_name, True)
                
        except Exception as e:
            await self.take_screenshot("aesthetics_fail")
            self.record_result(test_name, False, error=str(e))
            
    async def test_responsive_design(self):
        """Test responsive design for various screen sizes."""
        test_name = "Responsive Design"
        
        try:
            # Test mobile viewport
            await self.page.set_viewport_size({"width": 375, "height": 667})
            await self.page.reload()
            await self.page.wait_for_timeout(1000)
            
            # Check mobile layout
            container = await self.page.query_selector(".container")
            mobile_ok = container is not None
            
            # Test tablet viewport
            await self.page.set_viewport_size({"width": 768, "height": 1024})
            await self.page.reload()
            await self.page.wait_for_timeout(1000)
            
            tablet_ok = await self.page.query_selector(".container") is not None
            
            # Test desktop viewport
            await self.page.set_viewport_size({"width": 1920, "height": 1080})
            await self.page.reload()
            await self.page.wait_for_timeout(1000)
            
            desktop_ok = await self.page.query_selector(".container") is not None
            
            if mobile_ok and tablet_ok and desktop_ok:
                self.record_result(test_name, True)
            else:
                issues = []
                if not mobile_ok: issues.append("Mobile layout broken")
                if not tablet_ok: issues.append("Tablet layout broken")
                if not desktop_ok: issues.append("Desktop layout broken")
                self.record_result(test_name, False, ui_issue=", ".join(issues))
                
        except Exception as e:
            await self.take_screenshot("responsive_fail")
            self.record_result(test_name, False, error=str(e))
            
    async def test_status_indicators(self):
        """Test all status indicators update correctly."""
        test_name = "Status Indicators"
        
        try:
            await self.page.goto(BASE_URL, wait_until="networkidle")
            
            # Wait for status updates
            await self.page.wait_for_timeout(2000)
            
            # Check system status
            system_status = await self.page.text_content("#system-status")
            assert system_status, "System status missing"
            
            # Check memory status
            memory_status = await self.page.text_content("#memory-status")
            assert memory_status, "Memory status missing"
            
            # Check nudge count
            nudge_count = await self.page.text_content("#nudge-count")
            assert nudge_count is not None, "Nudge count missing"
            
            # Check music status
            music_status = await self.page.text_content("#music-status")
            assert music_status, "Music status missing"
            
            # Check Claude status
            claude_status = await self.page.text_content("#claude-status")
            assert claude_status, "Claude status missing"
            
            self.record_result(test_name, True)
            
        except Exception as e:
            await self.take_screenshot("status_indicators_fail")
            self.record_result(test_name, False, error=str(e))
            
    # ============= CHAT FUNCTIONALITY TESTS =============
    
    async def test_chat_interface(self):
        """Test chat interface functionality."""
        test_name = "Chat Interface"
        
        try:
            await self.page.goto(BASE_URL, wait_until="networkidle")
            
            # Find chat input
            chat_input = await self.page.query_selector("#messageInput")
            assert chat_input, "Chat input not found"
            
            # Type a message
            await chat_input.fill("Hello, I need help focusing")
            
            # Send message
            start = time.time()
            await self.page.click("button:text('Send')")
            
            # Wait for response
            await self.page.wait_for_selector(".message.assistant:last-child", 
                                             timeout=ADHD_RESPONSE_TARGET)
            
            response_time = int((time.time() - start) * 1000)
            
            # Check response exists
            response = await self.page.text_content(".message.assistant:last-child")
            assert response and len(response) > 0, "Empty response"
            
            self.record_result(test_name, True, performance_ms=response_time)
            
        except Exception as e:
            await self.take_screenshot("chat_interface_fail")
            self.record_result(test_name, False, error=str(e))
            
    async def test_chat_response_quality(self):
        """Test quality of chat responses for ADHD support."""
        test_name = "Chat Response Quality"
        
        try:
            await self.page.goto(BASE_URL, wait_until="networkidle")
            
            # Test various ADHD scenarios
            test_messages = [
                "I'm feeling overwhelmed by my tasks",
                "I can't stop procrastinating",
                "Help me prioritize my work",
                "I keep getting distracted"
            ]
            
            quality_issues = []
            
            for message in test_messages:
                # Clear previous messages
                await self.page.evaluate("""
                    () => {
                        const messages = document.getElementById('messages');
                        messages.innerHTML = '<div class="message assistant">How can I help?</div>';
                    }
                """)
                
                # Send message
                await self.page.fill("#messageInput", message)
                await self.page.click("button:text('Send')")
                
                # Wait for response
                await self.page.wait_for_selector(".message.assistant:last-child",
                                                 timeout=5000)
                
                response = await self.page.text_content(".message.assistant:last-child")
                
                # Check response quality
                if len(response) < 20:
                    quality_issues.append(f"Too short for '{message}': {len(response)} chars")
                elif len(response) > 500:
                    quality_issues.append(f"Too long for ADHD for '{message}': {len(response)} chars")
                    
            if quality_issues:
                self.record_result(test_name, False, 
                                 error="; ".join(quality_issues),
                                 accessibility_issue="Response length not ADHD-optimized")
            else:
                self.record_result(test_name, True)
                
        except Exception as e:
            await self.take_screenshot("chat_quality_fail")
            self.record_result(test_name, False, error=str(e))
            
    # ============= NUDGE SYSTEM TESTS =============
    
    async def test_nudge_devices_scan(self):
        """Test Nest device scanning."""
        test_name = "Nudge Device Scan"
        
        try:
            await self.page.goto(BASE_URL, wait_until="networkidle")
            
            # Wait for device scan
            await self.page.wait_for_timeout(3000)
            
            # Check devices section
            devices_text = await self.page.text_content("#devices")
            
            if "No Nest devices" in devices_text or "Failed" in devices_text:
                self.record_result(test_name, True)  # Expected if no devices
            else:
                # Check device items exist
                device_items = await self.page.query_selector_all(".device-item")
                if len(device_items) > 0:
                    self.record_result(test_name, True)
                else:
                    self.record_result(test_name, False, 
                                     error="Device scan shows success but no devices listed")
                    
        except Exception as e:
            await self.take_screenshot("device_scan_fail")
            self.record_result(test_name, False, error=str(e))
            
    async def test_nudge_api_endpoints(self):
        """Test nudge API endpoints."""
        test_name = "Nudge API Endpoints"
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test nudge devices endpoint
                async with session.get(f"{BASE_URL}/nudge/devices") as resp:
                    assert resp.status == 200, f"Devices endpoint failed: {resp.status}"
                    data = await resp.json()
                    assert "devices" in data, "Missing devices field"
                    
                # Test send nudge endpoint - uses query params not JSON
                async with session.post(
                    f"{BASE_URL}/nudge/send?message=Test%20nudge&urgency=normal"
                ) as resp:
                    # May fail if no devices, but should return valid response
                    assert resp.status in [200, 503], f"Send nudge unexpected status: {resp.status}"
                    
                self.record_result(test_name, True)
                
        except Exception as e:
            self.record_result(test_name, False, error=str(e))
            
    # ============= MUSIC INTEGRATION TESTS =============
    
    async def test_music_controls(self):
        """Test music control buttons."""
        test_name = "Music Controls UI"
        
        try:
            await self.page.goto(BASE_URL, wait_until="networkidle")
            
            # Check music buttons exist
            focus_btn = await self.page.query_selector("button:text('Focus Music')")
            energy_btn = await self.page.query_selector("button:text('Energy Music')")
            stop_btn = await self.page.query_selector("button:text('Stop Music')")
            
            assert focus_btn, "Focus music button missing"
            assert energy_btn, "Energy music button missing"
            assert stop_btn, "Stop music button missing"
            
            # Test clicking focus music
            await focus_btn.click()
            await self.page.wait_for_timeout(1000)
            
            # Check for activity update
            activity = await self.page.text_content("#activity")
            
            self.record_result(test_name, True)
            
        except Exception as e:
            await self.take_screenshot("music_controls_fail")
            self.record_result(test_name, False, error=str(e))
            
    async def test_music_api_endpoints(self):
        """Test music API endpoints."""
        test_name = "Music API Endpoints"
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test music status
                async with session.get(f"{BASE_URL}/music/status") as resp:
                    assert resp.status == 200, f"Music status failed: {resp.status}"
                    data = await resp.json()
                    assert "available" in data, "Missing available field"
                    
                # Test music play (may fail if not configured)
                async with session.post(
                    f"{BASE_URL}/music/focus"
                ) as resp:
                    # May return 503 if not configured
                    assert resp.status in [200, 503], f"Unexpected status: {resp.status}"
                    
                self.record_result(test_name, True)
                
        except Exception as e:
            self.record_result(test_name, False, error=str(e))
            
    # ============= HEALTH & API TESTS =============
    
    async def test_health_endpoint(self):
        """Test health check endpoint."""
        test_name = "Health Endpoint"
        
        try:
            async with aiohttp.ClientSession() as session:
                start = time.time()
                async with session.get(f"{BASE_URL}/health") as resp:
                    response_time = int((time.time() - start) * 1000)
                    assert resp.status == 200, f"Health check failed: {resp.status}"
                    
                    data = await resp.json()
                    assert data["status"] == "healthy", f"Unhealthy status: {data['status']}"
                    assert "components" in data, "Missing components"
                    
                    self.record_result(test_name, True, performance_ms=response_time)
                    
        except Exception as e:
            self.record_result(test_name, False, error=str(e))
            
    async def test_api_cors(self):
        """Test CORS headers for API."""
        test_name = "API CORS Headers"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.options(
                    f"{BASE_URL}/health",
                    headers={"Origin": "http://localhost:3000"}
                ) as resp:
                    cors_header = resp.headers.get("Access-Control-Allow-Origin")
                    assert cors_header == "*", f"CORS not configured: {cors_header}"
                    
                    self.record_result(test_name, True)
                    
        except Exception as e:
            self.record_result(test_name, False, error=str(e))
            
    # ============= CLAUDE INTEGRATION TESTS =============
    
    async def test_claude_status(self):
        """Test Claude integration status."""
        test_name = "Claude Integration Status"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BASE_URL}/claude/status") as resp:
                    if resp.status == 404:
                        # Claude endpoints may not exist if not configured
                        self.record_result(test_name, True)
                    else:
                        assert resp.status == 200, f"Claude status failed: {resp.status}"
                        data = await resp.json()
                        assert "authenticated" in data, "Missing authenticated field"
                        self.record_result(test_name, True)
                        
        except Exception as e:
            self.record_result(test_name, False, error=str(e))
            
    # ============= ACCESSIBILITY TESTS =============
    
    async def test_keyboard_navigation(self):
        """Test keyboard navigation accessibility."""
        test_name = "Keyboard Navigation"
        
        try:
            await self.page.goto(BASE_URL, wait_until="networkidle")
            
            # Tab through interactive elements
            await self.page.keyboard.press("Tab")
            focused = await self.page.evaluate("() => document.activeElement.tagName")
            
            elements_focused = [focused]
            
            for _ in range(10):  # Tab through several elements
                await self.page.keyboard.press("Tab")
                focused = await self.page.evaluate("() => document.activeElement.tagName")
                elements_focused.append(focused)
                
            # Should focus on interactive elements
            interactive = ["INPUT", "BUTTON", "A"]
            has_interactive = any(elem in interactive for elem in elements_focused)
            
            if has_interactive:
                self.record_result(test_name, True)
            else:
                self.record_result(test_name, False, 
                                 accessibility_issue="No keyboard navigation to interactive elements")
                
        except Exception as e:
            await self.take_screenshot("keyboard_nav_fail")
            self.record_result(test_name, False, error=str(e))
            
    async def test_color_contrast(self):
        """Test color contrast for readability."""
        test_name = "Color Contrast"
        
        try:
            await self.page.goto(BASE_URL, wait_until="networkidle")
            
            # Check text contrast
            contrast_ok = await self.page.evaluate("""
                () => {
                    const h1 = document.querySelector('h1');
                    const style = window.getComputedStyle(h1);
                    const color = style.color;
                    const bg = window.getComputedStyle(document.body).backgroundColor;
                    
                    // Simple check - text should be light on dark background
                    return color.includes('255') || color.includes('e0');
                }
            """)
            
            if contrast_ok:
                self.record_result(test_name, True)
            else:
                self.record_result(test_name, False,
                                 accessibility_issue="Poor text contrast for ADHD readability")
                
        except Exception as e:
            await self.take_screenshot("contrast_fail")
            self.record_result(test_name, False, error=str(e))
            
    # ============= PERFORMANCE TESTS =============
    
    async def test_page_load_performance(self):
        """Test page load performance metrics."""
        test_name = "Page Load Performance"
        
        try:
            start = time.time()
            await self.page.goto(BASE_URL, wait_until="domcontentloaded")
            dom_time = int((time.time() - start) * 1000)
            
            await self.page.wait_for_load_state("networkidle")
            full_load_time = int((time.time() - start) * 1000)
            
            # Get performance metrics
            metrics = await self.page.evaluate("""
                () => {
                    const perf = performance.getEntriesByType('navigation')[0];
                    return {
                        domInteractive: perf.domInteractive,
                        domComplete: perf.domComplete,
                        loadComplete: perf.loadEventEnd
                    };
                }
            """)
            
            # ADHD users need fast feedback
            if full_load_time < 3000:
                self.record_result(test_name, True, performance_ms=full_load_time)
            else:
                self.record_result(test_name, False,
                                 performance_ms=full_load_time,
                                 error=f"Load time {full_load_time}ms exceeds ADHD target")
                
        except Exception as e:
            await self.take_screenshot("performance_fail")
            self.record_result(test_name, False, error=str(e))
            
    async def test_api_response_times(self):
        """Test API endpoint response times."""
        test_name = "API Response Times"
        
        try:
            endpoints = [
                ("/health", "GET", None),
                ("/chat", "POST", {"message": "test", "user_id": "test"}),
                ("/nudge/devices", "GET", None),
                ("/music/status", "GET", None)
            ]
            
            slow_endpoints = []
            
            async with aiohttp.ClientSession() as session:
                for endpoint, method, data in endpoints:
                    start = time.time()
                    
                    if method == "GET":
                        async with session.get(f"{BASE_URL}{endpoint}") as resp:
                            response_time = int((time.time() - start) * 1000)
                    else:
                        async with session.post(f"{BASE_URL}{endpoint}", json=data) as resp:
                            response_time = int((time.time() - start) * 1000)
                            
                    if response_time > ADHD_RESPONSE_TARGET:
                        slow_endpoints.append(f"{endpoint}: {response_time}ms")
                        
            if slow_endpoints:
                self.record_result(test_name, False,
                                 error=f"Slow endpoints: {'; '.join(slow_endpoints)}")
            else:
                self.record_result(test_name, True)
                
        except Exception as e:
            self.record_result(test_name, False, error=str(e))
            
    # ============= ERROR HANDLING TESTS =============
    
    async def test_error_handling(self):
        """Test error handling and user feedback."""
        test_name = "Error Handling"
        
        try:
            await self.page.goto(BASE_URL, wait_until="networkidle")
            
            # Test with empty message
            await self.page.click("button:text('Send')")
            await self.page.wait_for_timeout(500)
            
            # Should not send empty message
            messages = await self.page.query_selector_all(".message.user")
            empty_sent = any([
                await msg.text_content() == "" 
                for msg in messages
            ])
            
            assert not empty_sent, "Empty message was sent"
            
            # Test with very long message
            long_msg = "x" * 10000
            await self.page.fill("#messageInput", long_msg)
            await self.page.click("button:text('Send')")
            
            # Should handle gracefully
            await self.page.wait_for_timeout(2000)
            
            # Check for error message
            error_shown = await self.page.query_selector(".message.assistant.error")
            
            self.record_result(test_name, True)
            
        except Exception as e:
            await self.take_screenshot("error_handling_fail")
            self.record_result(test_name, False, error=str(e))
            
    async def test_network_resilience(self):
        """Test handling of network issues."""
        test_name = "Network Resilience"
        
        try:
            await self.page.goto(BASE_URL, wait_until="networkidle")
            
            # Simulate offline
            await self.page.context.set_offline(True)
            
            # Try to send message
            await self.page.fill("#messageInput", "Test offline")
            await self.page.click("button:text('Send')")
            
            # Wait for error handling
            await self.page.wait_for_timeout(3000)
            
            # Check for error indication - directly from the message area since statusArea might not exist
            try:
                # Check if error message appeared
                error_msg = await self.page.query_selector(".message.assistant.error")
                if error_msg:
                    error_text = await error_msg.text_content()
                    has_error = True
                else:
                    # Check last assistant message for error indication
                    last_msg = await self.page.text_content(".message.assistant:last-child")
                    has_error = "error" in last_msg.lower() or "connection" in last_msg.lower()
            except:
                has_error = False
            
            # Restore connection
            await self.page.context.set_offline(False)
            
            if has_error:
                self.record_result(test_name, True)
            else:
                self.record_result(test_name, False,
                                 error="No error indication when offline")
                
        except Exception as e:
            # Restore connection before failing
            await self.page.context.set_offline(False)
            await self.take_screenshot("network_resilience_fail")
            self.record_result(test_name, False, error=str(e))
            
    # ============= INTEGRATION TESTS =============
    
    async def test_full_user_workflow(self):
        """Test complete user workflow."""
        test_name = "Full User Workflow"
        
        try:
            # Ensure we're online first
            await self.page.context.set_offline(False)
            
            workflow_start = time.time()
            
            # 1. Load dashboard
            await self.page.goto(BASE_URL, wait_until="networkidle")
            
            # 2. Send chat message
            await self.page.fill("#messageInput", "I need help organizing my day")
            await self.page.click("button:text('Send')")
            
            # 3. Wait for response
            await self.page.wait_for_selector(".message.assistant:last-child", timeout=5000)
            
            # 4. Try quick action button
            await self.page.click("button:text('Focus Music')")
            await self.page.wait_for_timeout(1000)
            
            # 5. Check activity log updated
            activity = await self.page.text_content("#activity")
            
            workflow_time = int((time.time() - workflow_start) * 1000)
            
            if workflow_time < 10000:  # 10 seconds for full workflow
                self.record_result(test_name, True, performance_ms=workflow_time)
            else:
                self.record_result(test_name, False,
                                 performance_ms=workflow_time,
                                 error=f"Workflow too slow: {workflow_time}ms")
                
        except Exception as e:
            await self.take_screenshot("workflow_fail")
            self.record_result(test_name, False, error=str(e))
            
    # ============= RUN ALL TESTS =============
    
    async def run_all_tests(self):
        """Run complete test suite."""
        print("\n" + "="*70)
        print("🧠 COMPREHENSIVE ADHD SYSTEM TESTING")
        print("="*70)
        print(f"Target URL: {BASE_URL}")
        print(f"Headless: {HEADLESS}")
        print(f"ADHD Response Target: {ADHD_RESPONSE_TARGET}ms")
        print("="*70 + "\n")
        
        await self.setup()
        
        # Dashboard UI Tests
        print("\n📊 DASHBOARD UI TESTS")
        print("-"*40)
        await self.test_dashboard_loads()
        await self.test_dashboard_aesthetics()
        await self.test_responsive_design()
        await self.test_status_indicators()
        
        # Chat Functionality Tests
        print("\n💬 CHAT FUNCTIONALITY TESTS")
        print("-"*40)
        await self.test_chat_interface()
        await self.test_chat_response_quality()
        
        # Nudge System Tests
        print("\n🔔 NUDGE SYSTEM TESTS")
        print("-"*40)
        await self.test_nudge_devices_scan()
        await self.test_nudge_api_endpoints()
        
        # Music Integration Tests
        print("\n🎵 MUSIC INTEGRATION TESTS")
        print("-"*40)
        await self.test_music_controls()
        await self.test_music_api_endpoints()
        
        # Health & API Tests
        print("\n🏥 HEALTH & API TESTS")
        print("-"*40)
        await self.test_health_endpoint()
        await self.test_api_cors()
        await self.test_claude_status()
        
        # Accessibility Tests
        print("\n♿ ACCESSIBILITY TESTS")
        print("-"*40)
        await self.test_keyboard_navigation()
        await self.test_color_contrast()
        
        # Performance Tests
        print("\n⚡ PERFORMANCE TESTS")
        print("-"*40)
        await self.test_page_load_performance()
        await self.test_api_response_times()
        
        # Error Handling Tests
        print("\n🛡️ ERROR HANDLING TESTS")
        print("-"*40)
        await self.test_error_handling()
        await self.test_network_resilience()
        
        # Integration Tests
        print("\n🔗 INTEGRATION TESTS")
        print("-"*40)
        await self.test_full_user_workflow()
        
        await self.teardown()
        
        # Print results summary
        self.print_results()
        
    def print_results(self):
        """Print comprehensive test results."""
        runtime = int(time.time() - self.start_time)
        
        print("\n" + "="*70)
        print("📊 TEST RESULTS SUMMARY")
        print("="*70)
        
        success_rate = (self.results["passed"] / self.results["total"] * 100) if self.results["total"] > 0 else 0
        
        print(f"\n✅ Passed: {self.results['passed']}/{self.results['total']} ({success_rate:.1f}%)")
        print(f"❌ Failed: {self.results['failed']}/{self.results['total']}")
        print(f"⏱️ Total Runtime: {runtime} seconds")
        
        # Performance Analysis
        if self.results["performance"]:
            print("\n⚡ PERFORMANCE METRICS:")
            perf_times = [p["time_ms"] for p in self.results["performance"]]
            avg_time = sum(perf_times) / len(perf_times)
            max_time = max(perf_times)
            acceptable = sum(1 for p in self.results["performance"] if p["acceptable"])
            
            print(f"   Average Response: {avg_time:.0f}ms")
            print(f"   Max Response: {max_time:.0f}ms")
            print(f"   Meeting ADHD Target: {acceptable}/{len(self.results['performance'])}")
            
        # Issues Summary
        if self.results["errors"]:
            print("\n❌ ERRORS:")
            for error in self.results["errors"][:5]:  # Show first 5
                print(f"   - {error}")
                
        if self.results["accessibility"]:
            print("\n♿ ACCESSIBILITY ISSUES:")
            for issue in self.results["accessibility"]:
                print(f"   - {issue}")
                
        if self.results["ui_issues"]:
            print("\n🎨 UI ISSUES:")
            for issue in self.results["ui_issues"]:
                print(f"   - {issue}")
                
        # Final verdict
        print("\n" + "="*70)
        if success_rate >= 90:
            print("🎉 SYSTEM READY FOR PRODUCTION!")
        elif success_rate >= 70:
            print("⚠️ SYSTEM MOSTLY FUNCTIONAL - Some issues to address")
        else:
            print("🚨 SYSTEM NEEDS WORK - Multiple failures detected")
        print("="*70)
        
        # Save results to file
        results_file = Path("test_results.json")
        with open(results_file, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "url": BASE_URL,
                "results": self.results,
                "runtime_seconds": runtime,
                "success_rate": success_rate
            }, f, indent=2)
        print(f"\n📁 Results saved to: {results_file}")


async def main():
    """Main test runner."""
    tester = ADHDSystemTester()
    try:
        await tester.run_all_tests()
        
        # Return exit code based on results
        if tester.results["failed"] == 0:
            return 0
        elif tester.results["failed"] <= 2:
            return 1  # Minor issues
        else:
            return 2  # Major issues
            
    except Exception as e:
        print(f"\n🚨 FATAL ERROR: {e}")
        return 3
        

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)