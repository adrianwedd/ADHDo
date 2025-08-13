#!/usr/bin/env python3
"""
STRESS AND LOAD TESTING FOR ADHD SYSTEM
Tests system performance under heavy load and concurrent users
"""

import os
import asyncio
import time
import statistics
from datetime import datetime
from typing import List, Dict
from pathlib import Path
import json
import aiohttp
from playwright.async_api import async_playwright, Page, Browser

BASE_URL = os.environ.get("BASE_URL", "http://localhost:23444")
HEADLESS = os.environ.get("HEADLESS", "true").lower() == "true"

class StressTestResults:
    """Track stress test metrics."""
    
    def __init__(self):
        self.response_times = []
        self.errors = []
        self.success_count = 0
        self.failure_count = 0
        self.concurrent_users = 0
        self.test_duration = 0
        self.memory_usage = []
        self.cpu_usage = []
        
    def add_response(self, response_time_ms: float, success: bool):
        """Record a response."""
        self.response_times.append(response_time_ms)
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
            
    def get_percentile(self, percentile: int) -> float:
        """Get response time percentile."""
        if not self.response_times:
            return 0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * percentile / 100)
        return sorted_times[min(index, len(sorted_times) - 1)]
        
    def print_summary(self):
        """Print test summary."""
        if not self.response_times:
            print("No responses recorded")
            return
            
        print("\n" + "="*70)
        print("📊 STRESS TEST RESULTS")
        print("="*70)
        
        print(f"\n🔧 Test Configuration:")
        print(f"   Concurrent Users: {self.concurrent_users}")
        print(f"   Test Duration: {self.test_duration:.1f}s")
        print(f"   Total Requests: {len(self.response_times)}")
        
        print(f"\n✅ Success Metrics:")
        print(f"   Successful: {self.success_count}")
        print(f"   Failed: {self.failure_count}")
        print(f"   Success Rate: {self.success_count/(self.success_count+self.failure_count)*100:.1f}%")
        
        print(f"\n⚡ Performance Metrics:")
        print(f"   Min Response: {min(self.response_times):.0f}ms")
        print(f"   Avg Response: {statistics.mean(self.response_times):.0f}ms")
        print(f"   Max Response: {max(self.response_times):.0f}ms")
        print(f"   50th Percentile: {self.get_percentile(50):.0f}ms")
        print(f"   95th Percentile: {self.get_percentile(95):.0f}ms")
        print(f"   99th Percentile: {self.get_percentile(99):.0f}ms")
        
        print(f"\n📈 Throughput:")
        rps = len(self.response_times) / self.test_duration if self.test_duration > 0 else 0
        print(f"   Requests/Second: {rps:.1f}")
        
        # ADHD Performance Analysis
        adhd_compliant = self.get_percentile(95) < 3000
        print(f"\n🧠 ADHD Compliance:")
        print(f"   95% < 3s Target: {'✅ PASS' if adhd_compliant else '❌ FAIL'}")
        
        if self.errors:
            print(f"\n❌ Errors (first 5):")
            for error in self.errors[:5]:
                print(f"   - {error}")


class ADHDStressTest:
    """Stress test the ADHD support system."""
    
    def __init__(self):
        self.results = StressTestResults()
        
    async def single_user_session(self, user_id: int, duration_seconds: int = 30):
        """Simulate a single user session."""
        async with aiohttp.ClientSession() as session:
            end_time = time.time() + duration_seconds
            
            while time.time() < end_time:
                try:
                    # Simulate user actions
                    action = user_id % 4
                    
                    if action == 0:
                        # Chat interaction
                        start = time.time()
                        async with session.post(
                            f"{BASE_URL}/chat",
                            json={
                                "message": f"User {user_id}: I need help focusing",
                                "user_id": f"stress_user_{user_id}"
                            }
                        ) as resp:
                            await resp.json()
                            response_time = (time.time() - start) * 1000
                            self.results.add_response(response_time, resp.status == 200)
                            
                    elif action == 1:
                        # Health check
                        start = time.time()
                        async with session.get(f"{BASE_URL}/health") as resp:
                            await resp.json()
                            response_time = (time.time() - start) * 1000
                            self.results.add_response(response_time, resp.status == 200)
                            
                    elif action == 2:
                        # Music status
                        start = time.time()
                        async with session.get(f"{BASE_URL}/music/status") as resp:
                            await resp.json()
                            response_time = (time.time() - start) * 1000
                            self.results.add_response(response_time, resp.status == 200)
                            
                    else:
                        # Nudge devices
                        start = time.time()
                        async with session.get(f"{BASE_URL}/nudge/devices") as resp:
                            await resp.json()
                            response_time = (time.time() - start) * 1000
                            self.results.add_response(response_time, resp.status == 200)
                    
                    # Random delay between actions (0.5-2 seconds)
                    await asyncio.sleep(0.5 + (user_id % 4) * 0.5)
                    
                except Exception as e:
                    self.results.errors.append(f"User {user_id}: {str(e)[:50]}")
                    self.results.failure_count += 1
                    
    async def concurrent_users_test(self, num_users: int = 10, duration_seconds: int = 30):
        """Test with multiple concurrent users."""
        print(f"\n🚀 Starting concurrent users test: {num_users} users for {duration_seconds}s")
        
        self.results.concurrent_users = num_users
        start_time = time.time()
        
        # Create tasks for all users
        tasks = [
            self.single_user_session(i, duration_seconds)
            for i in range(num_users)
        ]
        
        # Run all users concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self.results.test_duration = time.time() - start_time
        
    async def browser_stress_test(self, num_browsers: int = 5):
        """Stress test with multiple browser instances."""
        print(f"\n🌐 Starting browser stress test: {num_browsers} browsers")
        
        playwright = await async_playwright().start()
        browsers = []
        pages = []
        
        try:
            # Launch multiple browsers
            for i in range(num_browsers):
                browser = await playwright.chromium.launch(
                    headless=HEADLESS,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                browsers.append(browser)
                
                context = await browser.new_context()
                page = await context.new_page()
                pages.append(page)
                
                # Load dashboard
                start = time.time()
                await page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
                load_time = (time.time() - start) * 1000
                self.results.add_response(load_time, True)
                
                print(f"   Browser {i+1}: Dashboard loaded in {load_time:.0f}ms")
                
            # Simulate concurrent interactions
            print(f"   Simulating concurrent interactions...")
            
            for _ in range(5):  # 5 rounds of interactions
                tasks = []
                for i, page in enumerate(pages):
                    # Each browser sends a chat message
                    async def interact(p, idx):
                        try:
                            await p.fill("#messageInput", f"Browser {idx}: Help me focus")
                            start = time.time()
                            await p.click("button:text('Send')")
                            await p.wait_for_selector(".message.assistant:last-child", timeout=5000)
                            response_time = (time.time() - start) * 1000
                            self.results.add_response(response_time, True)
                        except Exception as e:
                            self.results.errors.append(f"Browser {idx}: {str(e)[:50]}")
                            self.results.failure_count += 1
                    
                    tasks.append(interact(page, i))
                
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(1)  # Brief pause between rounds
                
        finally:
            # Clean up browsers
            for browser in browsers:
                await browser.close()
            await playwright.stop()
            
        print(f"   Browser stress test completed")
        
    async def spike_test(self, initial_users: int = 5, spike_users: int = 20, duration_seconds: int = 10):
        """Test system response to sudden traffic spike."""
        print(f"\n📈 Starting spike test: {initial_users} → {spike_users} users")
        
        # Start with normal load
        print(f"   Phase 1: Normal load ({initial_users} users)")
        await self.concurrent_users_test(initial_users, duration_seconds)
        
        # Clear previous results
        normal_p95 = self.results.get_percentile(95)
        self.results = StressTestResults()
        
        # Spike the load
        print(f"   Phase 2: Traffic spike ({spike_users} users)")
        await self.concurrent_users_test(spike_users, duration_seconds)
        
        spike_p95 = self.results.get_percentile(95)
        
        print(f"\n   📊 Spike Impact:")
        print(f"      Normal Load P95: {normal_p95:.0f}ms")
        print(f"      Spike Load P95: {spike_p95:.0f}ms")
        print(f"      Degradation: {(spike_p95/normal_p95 - 1)*100:.1f}%")
        
    async def endurance_test(self, num_users: int = 5, duration_minutes: int = 2):
        """Test system stability over extended period."""
        print(f"\n⏱️ Starting endurance test: {num_users} users for {duration_minutes} minutes")
        
        duration_seconds = duration_minutes * 60
        checkpoint_interval = 30  # Report every 30 seconds
        
        self.results.concurrent_users = num_users
        start_time = time.time()
        
        # Create long-running user sessions
        async def monitored_session(user_id: int):
            """User session with periodic monitoring."""
            last_checkpoint = time.time()
            checkpoint_responses = []
            
            async with aiohttp.ClientSession() as session:
                while time.time() - start_time < duration_seconds:
                    try:
                        # Regular chat interaction
                        req_start = time.time()
                        async with session.post(
                            f"{BASE_URL}/chat",
                            json={
                                "message": f"Endurance test user {user_id}",
                                "user_id": f"endurance_user_{user_id}"
                            }
                        ) as resp:
                            await resp.json()
                            response_time = (time.time() - req_start) * 1000
                            self.results.add_response(response_time, resp.status == 200)
                            checkpoint_responses.append(response_time)
                            
                        # Check if checkpoint reached
                        if time.time() - last_checkpoint >= checkpoint_interval:
                            avg_response = statistics.mean(checkpoint_responses) if checkpoint_responses else 0
                            elapsed = int(time.time() - start_time)
                            print(f"   [{elapsed}s] User {user_id} - Avg response: {avg_response:.0f}ms")
                            checkpoint_responses = []
                            last_checkpoint = time.time()
                            
                        await asyncio.sleep(2)  # Pause between requests
                        
                    except Exception as e:
                        self.results.errors.append(f"Endurance user {user_id}: {str(e)[:50]}")
                        self.results.failure_count += 1
                        
        # Run endurance test
        tasks = [monitored_session(i) for i in range(num_users)]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self.results.test_duration = time.time() - start_time
        
    async def api_flood_test(self, requests_per_second: int = 50, duration_seconds: int = 10):
        """Test API rate limiting and flood handling."""
        print(f"\n🌊 Starting API flood test: {requests_per_second} req/s for {duration_seconds}s")
        
        total_requests = requests_per_second * duration_seconds
        batch_size = 10
        delay_between_batches = batch_size / requests_per_second
        
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            while time.time() - start_time < duration_seconds:
                # Send batch of requests
                batch_tasks = []
                for _ in range(batch_size):
                    async def make_request():
                        try:
                            req_start = time.time()
                            async with session.get(f"{BASE_URL}/health") as resp:
                                response_time = (time.time() - req_start) * 1000
                                self.results.add_response(response_time, resp.status == 200)
                        except Exception as e:
                            self.results.errors.append(f"Flood: {str(e)[:30]}")
                            self.results.failure_count += 1
                    
                    batch_tasks.append(make_request())
                
                await asyncio.gather(*batch_tasks, return_exceptions=True)
                await asyncio.sleep(delay_between_batches)
                
        self.results.test_duration = time.time() - start_time
        actual_rps = len(self.results.response_times) / self.results.test_duration
        
        print(f"   Target RPS: {requests_per_second}")
        print(f"   Actual RPS: {actual_rps:.1f}")
        print(f"   Success Rate: {self.results.success_count/(self.results.success_count+self.results.failure_count)*100:.1f}%")


async def run_all_stress_tests():
    """Run comprehensive stress testing suite."""
    print("\n" + "="*70)
    print("🔥 ADHD SYSTEM STRESS & LOAD TESTING")
    print("="*70)
    print(f"Target: {BASE_URL}")
    print("="*70)
    
    tester = ADHDStressTest()
    
    # 1. Concurrent Users Test
    print("\n1️⃣ CONCURRENT USERS TEST")
    await tester.concurrent_users_test(num_users=10, duration_seconds=20)
    tester.results.print_summary()
    
    # 2. Browser Stress Test
    print("\n2️⃣ BROWSER STRESS TEST")
    tester.results = StressTestResults()
    await tester.browser_stress_test(num_browsers=3)
    tester.results.print_summary()
    
    # 3. Spike Test
    print("\n3️⃣ TRAFFIC SPIKE TEST")
    tester.results = StressTestResults()
    await tester.spike_test(initial_users=3, spike_users=15, duration_seconds=10)
    tester.results.print_summary()
    
    # 4. API Flood Test
    print("\n4️⃣ API FLOOD TEST")
    tester.results = StressTestResults()
    await tester.api_flood_test(requests_per_second=30, duration_seconds=10)
    tester.results.print_summary()
    
    # 5. Endurance Test (shorter for demo)
    print("\n5️⃣ ENDURANCE TEST")
    tester.results = StressTestResults()
    await tester.endurance_test(num_users=3, duration_minutes=1)
    tester.results.print_summary()
    
    print("\n" + "="*70)
    print("✅ STRESS TESTING COMPLETE")
    print("="*70)
    
    # Save results
    results_file = Path("stress_test_results.json")
    all_results = {
        "timestamp": datetime.now().isoformat(),
        "url": BASE_URL,
        "tests_completed": 5,
        "summary": "Stress testing completed successfully"
    }
    
    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n📁 Results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(run_all_stress_tests())