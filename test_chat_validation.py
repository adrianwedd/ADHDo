#!/usr/bin/env python3
"""
Core Chat Functionality Validation Script
Tests the essential chat endpoint to ensure it works reliably for ADHD users.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional
import aiohttp
import sys

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test_user_adhd"

# ADHD-specific test messages
TEST_MESSAGES = [
    # Basic functionality
    "Hello, I need help focusing today",
    "I can't get started on my work",
    "Everything feels overwhelming",
    
    # Executive function challenges
    "I have 10 things to do and don't know where to start",
    "I've been procrastinating all day",
    "I keep getting distracted",
    
    # Time blindness
    "What time is it?",
    "How long have I been working?",
    "I lost track of time again",
    
    # Emotional regulation
    "I'm feeling really frustrated",
    "Why can't I just do things like everyone else?",
    "I'm having a hard time today",
    
    # Edge cases
    "",  # Empty message
    "!" * 500,  # Very long message
    "🤔💭🧠",  # Only emojis
]

class ChatValidator:
    def __init__(self):
        self.results = []
        self.response_times = []
        
    async def test_health(self, session: aiohttp.ClientSession) -> bool:
        """Check if server is healthy."""
        try:
            async with session.get(f"{BASE_URL}/health") as resp:
                return resp.status == 200
        except:
            return False
    
    async def test_chat_message(
        self, 
        session: aiohttp.ClientSession,
        message: str,
        test_num: int
    ) -> Dict:
        """Test a single chat message."""
        start_time = time.time()
        result = {
            "test_num": test_num,
            "message": message[:50] + "..." if len(message) > 50 else message,
            "success": False,
            "response_time": None,
            "error": None,
            "response_preview": None
        }
        
        try:
            payload = {
                "message": message,
                "user_id": TEST_USER_ID,
                "context": {
                    "time_of_day": "afternoon",
                    "energy_level": "low",
                    "stress_level": "high"
                }
            }
            
            async with session.post(
                f"{BASE_URL}/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                response_time = time.time() - start_time
                result["response_time"] = response_time
                self.response_times.append(response_time)
                
                if resp.status == 200:
                    data = await resp.json()
                    result["success"] = True
                    
                    # Check response quality
                    if "response" in data:
                        response_text = data["response"]
                        result["response_preview"] = response_text[:100]
                        
                        # ADHD-specific checks
                        if len(response_text) > 500:
                            result["warning"] = "Response too long for ADHD users"
                        if response_text.strip() == "":
                            result["error"] = "Empty response"
                            result["success"] = False
                else:
                    result["error"] = f"HTTP {resp.status}"
                    error_text = await resp.text()
                    result["error_detail"] = error_text[:200]
                    
        except asyncio.TimeoutError:
            result["error"] = "Timeout (>10s)"
            result["response_time"] = 10.0
            self.response_times.append(10.0)
        except Exception as e:
            result["error"] = str(e)[:100]
            
        self.results.append(result)
        return result
    
    async def test_session_persistence(
        self,
        session: aiohttp.ClientSession
    ) -> bool:
        """Test if sessions persist correctly."""
        try:
            # Send first message
            await self.test_chat_message(session, "Remember that I like blue", 100)
            
            # Send follow-up 
            result = await self.test_chat_message(
                session, 
                "What's my favorite color?",
                101
            )
            
            # Check if context was maintained
            if result["success"] and result["response_preview"]:
                return "blue" in result["response_preview"].lower()
            return False
        except:
            return False
    
    async def run_validation(self):
        """Run complete validation suite."""
        print("🧪 ADHDo Chat Validation Starting...")
        print("=" * 50)
        
        async with aiohttp.ClientSession() as session:
            # Check health
            print("Checking server health...")
            if not await self.test_health(session):
                print("❌ Server is not responding at", BASE_URL)
                print("\nPlease start the server with:")
                print("  python -m uvicorn src.mcp_server.main:app --reload")
                return False
            print("✅ Server is healthy\n")
            
            # Test each message
            print("Testing chat messages...")
            for i, message in enumerate(TEST_MESSAGES, 1):
                result = await self.test_chat_message(session, message, i)
                
                # Print progress
                status = "✅" if result["success"] else "❌"
                time_str = f"{result['response_time']:.2f}s" if result['response_time'] else "N/A"
                print(f"{status} Test {i:2d}: {time_str} - {result['message']}")
                
                if result.get("error"):
                    print(f"   Error: {result['error']}")
                if result.get("warning"):
                    print(f"   ⚠️  {result['warning']}")
            
            # Test session persistence
            print("\nTesting session persistence...")
            session_works = await self.test_session_persistence(session)
            print(f"{'✅' if session_works else '❌'} Session persistence")
            
        # Summary
        self.print_summary()
        return self.evaluate_success()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 50)
        print("📊 VALIDATION SUMMARY")
        print("=" * 50)
        
        successful = sum(1 for r in self.results if r["success"])
        total = len(self.results)
        success_rate = (successful / total * 100) if total > 0 else 0
        
        print(f"Success Rate: {successful}/{total} ({success_rate:.1f}%)")
        
        if self.response_times:
            avg_time = sum(self.response_times) / len(self.response_times)
            max_time = max(self.response_times)
            under_3s = sum(1 for t in self.response_times if t < 3.0)
            
            print(f"\nResponse Times:")
            print(f"  Average: {avg_time:.2f}s")
            print(f"  Maximum: {max_time:.2f}s")
            print(f"  Under 3s: {under_3s}/{len(self.response_times)} ({under_3s/len(self.response_times)*100:.1f}%)")
            
            if avg_time > 3.0:
                print("  ⚠️  WARNING: Average response time exceeds ADHD threshold (3s)")
        
        # List failures
        failures = [r for r in self.results if not r["success"]]
        if failures:
            print(f"\n❌ Failed Tests:")
            for f in failures[:5]:  # Show first 5 failures
                print(f"  Test {f['test_num']}: {f['message']}")
                if f.get("error"):
                    print(f"    Error: {f['error']}")
    
    def evaluate_success(self) -> bool:
        """Determine if validation passed."""
        if not self.results:
            return False
            
        success_rate = sum(1 for r in self.results if r["success"]) / len(self.results)
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 999
        
        # Pass criteria
        return success_rate >= 0.8 and avg_response_time < 5.0

async def main():
    validator = ChatValidator()
    success = await validator.run_validation()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ VALIDATION PASSED - Core chat is functional")
    else:
        print("❌ VALIDATION FAILED - Core chat needs fixes")
    print("=" * 50)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())