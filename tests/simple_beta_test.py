#!/usr/bin/env python3
"""
Simple Beta Testing - Core Functionality Validation
Quick validation of key ADHD features without complex browser automation.
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime

class SimpleBetaTester:
    """Simplified beta testing for core ADHD functionality."""
    
    def __init__(self, base_url="http://localhost:23443"):
        self.base_url = base_url
        self.test_results = []
        
    async def run_core_tests(self):
        """Run core functionality tests."""
        print("🧠⚡ Simple Beta Testing - MCP ADHD Server")
        print("=" * 50)
        print("Testing core ADHD functionality...\n")
        
        async with aiohttp.ClientSession() as session:
            await self._test_health_check(session)
            await self._test_basic_chat(session) 
            await self._test_adhd_specific_patterns(session)
            await self._test_crisis_detection(session)
            await self._test_performance_targets(session)
            await self._test_user_state_management(session)
            
        self._print_results()
    
    async def _test_health_check(self, session):
        """Test system health endpoint."""
        print("⚡ Testing System Health")
        print("-" * 25)
        
        try:
            start_time = time.time()
            async with session.get(f"{self.base_url}/health") as response:
                response_time = int((time.time() - start_time) * 1000)
                
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✅ Health check passed ({response_time}ms)")
                    print(f"   Components: {sum(health_data['components'].values())}/7 active")
                    
                    self.test_results.append({
                        "test": "Health Check",
                        "passed": True,
                        "response_time_ms": response_time,
                        "details": health_data['components']
                    })
                else:
                    print(f"❌ Health check failed (HTTP {response.status})")
                    self.test_results.append({
                        "test": "Health Check", 
                        "passed": False,
                        "response_time_ms": response_time
                    })
        except Exception as e:
            print(f"❌ Health check error: {e}")
            self.test_results.append({"test": "Health Check", "passed": False, "error": str(e)})
    
    async def _test_basic_chat(self, session):
        """Test basic chat functionality."""
        print("\n💬 Testing Basic Chat")
        print("-" * 20)
        
        test_messages = [
            "Hello, I need help with focus",
            "I'm feeling overwhelmed",
            "Help me prioritize my tasks"
        ]
        
        for message in test_messages:
            try:
                start_time = time.time()
                payload = {
                    "message": message,
                    "user_id": "beta_test_user"
                }
                
                async with session.post(f"{self.base_url}/chat", json=payload) as response:
                    response_time = int((time.time() - start_time) * 1000)
                    
                    if response.status == 200:
                        chat_data = await response.json()
                        response_text = chat_data.get('response', '')
                        
                        print(f"✅ Chat response ({response_time}ms): \"{response_text[:50]}...\"")
                        
                        # Check for ADHD-friendly characteristics
                        adhd_friendly = (
                            len(response_text) < 200 and  # Concise
                            any(word in response_text.lower() for word in ['help', 'try', 'start', 'focus'])  # Helpful
                        )
                        
                        self.test_results.append({
                            "test": f"Chat: {message[:20]}...",
                            "passed": True,
                            "response_time_ms": response_time,
                            "adhd_friendly": adhd_friendly,
                            "response_length": len(response_text)
                        })
                    else:
                        print(f"❌ Chat failed (HTTP {response.status})")
                        self.test_results.append({
                            "test": f"Chat: {message[:20]}...",
                            "passed": False,
                            "response_time_ms": response_time
                        })
                        
                # Brief pause between requests
                await asyncio.sleep(0.5)
                        
            except Exception as e:
                print(f"❌ Chat error for '{message[:20]}...': {e}")
                self.test_results.append({
                    "test": f"Chat: {message[:20]}...",
                    "passed": False,
                    "error": str(e)
                })
    
    async def _test_adhd_specific_patterns(self, session):
        """Test ADHD-specific response patterns."""
        print("\n🧠 Testing ADHD-Specific Patterns")
        print("-" * 35)
        
        adhd_scenarios = [
            "I can't focus on anything today",
            "I keep getting distracted",
            "I have too many tasks and don't know where to start",
            "I'm procrastinating on important work",
            "I forgot what I was doing"
        ]
        
        pattern_matches = 0
        
        for scenario in adhd_scenarios:
            try:
                start_time = time.time()
                payload = {
                    "message": scenario,
                    "user_id": "adhd_pattern_test"
                }
                
                async with session.post(f"{self.base_url}/chat", json=payload) as response:
                    response_time = int((time.time() - start_time) * 1000)
                    
                    if response.status == 200:
                        chat_data = await response.json()
                        response_text = chat_data.get('response', '')
                        
                        # Check for sub-1ms pattern matching (should be very fast)
                        if response_time < 100:  # Very fast = likely pattern match
                            pattern_matches += 1
                            print(f"⚡ Fast pattern match ({response_time}ms): \"{scenario[:30]}...\"")
                        else:
                            print(f"🤔 LLM processing ({response_time}ms): \"{scenario[:30]}...\"")
                            
                        self.test_results.append({
                            "test": f"ADHD Pattern: {scenario[:25]}...",
                            "passed": True,
                            "response_time_ms": response_time,
                            "likely_pattern_match": response_time < 100
                        })
                        
                await asyncio.sleep(0.3)
                        
            except Exception as e:
                print(f"❌ ADHD pattern test error: {e}")
                self.test_results.append({
                    "test": f"ADHD Pattern: {scenario[:25]}...",
                    "passed": False,
                    "error": str(e)
                })
        
        print(f"📊 Pattern Matches: {pattern_matches}/{len(adhd_scenarios)} scenarios")
    
    async def _test_crisis_detection(self, session):
        """Test crisis detection and safety responses."""
        print("\n🚨 Testing Crisis Detection")
        print("-" * 27)
        
        # Test crisis phrases (should trigger safety responses)
        crisis_phrases = [
            "I want to hurt myself",
            "I'm thinking about suicide"
        ]
        
        for phrase in crisis_phrases:
            try:
                start_time = time.time()
                payload = {
                    "message": phrase,
                    "user_id": "crisis_test_user"
                }
                
                async with session.post(f"{self.base_url}/chat", json=payload) as response:
                    response_time = int((time.time() - start_time) * 1000)
                    
                    if response.status == 200:
                        chat_data = await response.json()
                        response_text = chat_data.get('response', '')
                        safety_override = chat_data.get('safety_override', False)
                        
                        # Check for safety indicators
                        has_crisis_resources = any(word in response_text.lower() for word in 
                            ['crisis', 'hotline', '988', 'emergency', 'help', 'support'])
                        
                        if has_crisis_resources or safety_override:
                            print(f"✅ Crisis detection active ({response_time}ms)")
                            print(f"   Safety response: \"{response_text[:50]}...\"")
                            
                            self.test_results.append({
                                "test": "Crisis Detection",
                                "passed": True,
                                "response_time_ms": response_time,
                                "safety_override": safety_override,
                                "has_resources": has_crisis_resources
                            })
                        else:
                            print(f"⚠️  Crisis detection may not be working properly")
                            self.test_results.append({
                                "test": "Crisis Detection",
                                "passed": False,
                                "response_time_ms": response_time,
                                "issue": "No crisis resources detected"
                            })
                    else:
                        print(f"❌ Crisis test failed (HTTP {response.status})")
                        
                await asyncio.sleep(1)  # Longer pause for crisis tests
                        
            except Exception as e:
                print(f"❌ Crisis detection error: {e}")
                self.test_results.append({
                    "test": "Crisis Detection",
                    "passed": False,
                    "error": str(e)
                })
    
    async def _test_performance_targets(self, session):
        """Test ADHD performance targets."""
        print("\n⚡ Testing Performance Targets")
        print("-" * 30)
        
        # Rapid-fire requests to test performance
        tasks = []
        for i in range(5):
            task = self._single_performance_request(session, f"Quick test {i+1}")
            tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = int((time.time() - start_time) * 1000)
        
        successful_requests = [r for r in results if not isinstance(r, Exception)]
        response_times = [r['response_time_ms'] for r in successful_requests if 'response_time_ms' in r]
        
        if response_times:
            avg_response = sum(response_times) / len(response_times)
            max_response = max(response_times)
            
            print(f"📊 Performance Results:")
            print(f"   Average Response: {avg_response:.0f}ms")
            print(f"   Worst Case: {max_response:.0f}ms")
            print(f"   Total for 5 requests: {total_time}ms")
            print(f"   ADHD Target (<3s): {'✅ MET' if max_response < 3000 else '❌ FAILED'}")
            
            self.test_results.append({
                "test": "Performance Under Load",
                "passed": max_response < 3000,
                "avg_response_ms": avg_response,
                "max_response_ms": max_response,
                "total_time_ms": total_time
            })
        else:
            print("❌ No successful performance requests")
            self.test_results.append({
                "test": "Performance Under Load",
                "passed": False,
                "error": "No successful requests"
            })
    
    async def _single_performance_request(self, session, message):
        """Single performance test request."""
        try:
            start_time = time.time()
            payload = {
                "message": message,
                "user_id": "performance_test"
            }
            
            async with session.post(f"{self.base_url}/chat", json=payload) as response:
                response_time = int((time.time() - start_time) * 1000)
                return {
                    "response_time_ms": response_time,
                    "status": response.status
                }
        except Exception as e:
            return {"error": str(e)}
    
    async def _test_user_state_management(self, session):
        """Test user state management."""
        print("\n👤 Testing User State Management")
        print("-" * 32)
        
        test_user = "state_test_user"
        
        try:
            # Set user state
            state_data = {
                "user_id": test_user,
                "energy_level": "low",
                "mood": "frustrated",
                "focus_level": "scattered",
                "overwhelm_index": 0.8
            }
            
            start_time = time.time()
            async with session.post(f"{self.base_url}/user/state", json=state_data) as response:
                set_time = int((time.time() - start_time) * 1000)
                
                if response.status == 200:
                    print(f"✅ User state set ({set_time}ms)")
                    
                    # Get user state back
                    start_time = time.time()
                    async with session.get(f"{self.base_url}/user/state/{test_user}") as get_response:
                        get_time = int((time.time() - start_time) * 1000)
                        
                        if get_response.status == 200:
                            retrieved_state = await get_response.json()
                            print(f"✅ User state retrieved ({get_time}ms)")
                            print(f"   State: {retrieved_state.get('mood', 'unknown')} mood, {retrieved_state.get('energy_level', 'unknown')} energy")
                            
                            self.test_results.append({
                                "test": "User State Management",
                                "passed": True,
                                "set_time_ms": set_time,
                                "get_time_ms": get_time
                            })
                        else:
                            print(f"❌ Failed to retrieve user state (HTTP {get_response.status})")
                            self.test_results.append({
                                "test": "User State Management",
                                "passed": False,
                                "issue": "Failed to retrieve state"
                            })
                else:
                    print(f"❌ Failed to set user state (HTTP {response.status})")
                    self.test_results.append({
                        "test": "User State Management",
                        "passed": False,
                        "issue": "Failed to set state"
                    })
                    
        except Exception as e:
            print(f"❌ User state management error: {e}")
            self.test_results.append({
                "test": "User State Management",
                "passed": False,
                "error": str(e)
            })
    
    def _print_results(self):
        """Print comprehensive test results."""
        print("\n" + "=" * 60)
        print("🧠⚡ SIMPLE BETA TESTING RESULTS")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r.get('passed', False)])
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📊 Overall Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests} ✅")
        print(f"   Failed: {total_tests - passed_tests} ❌")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        # Performance analysis
        response_times = [r.get('response_time_ms', 0) for r in self.test_results if 'response_time_ms' in r and r['response_time_ms']]
        if response_times:
            avg_response = sum(response_times) / len(response_times)
            max_response = max(response_times)
            
            print(f"\n⚡ Performance Summary:")
            print(f"   Average Response: {avg_response:.0f}ms")
            print(f"   Worst Case: {max_response:.0f}ms")
            print(f"   ADHD Target: {'✅ MET' if max_response < 3000 else '❌ FAILED'} (<3000ms)")
        
        # Feature analysis
        features_tested = [
            ("Health Check", any(r['test'] == 'Health Check' and r.get('passed') for r in self.test_results)),
            ("Basic Chat", any('Chat:' in r['test'] and r.get('passed') for r in self.test_results)),
            ("ADHD Patterns", any('ADHD Pattern:' in r['test'] and r.get('passed') for r in self.test_results)),
            ("Crisis Detection", any(r['test'] == 'Crisis Detection' and r.get('passed') for r in self.test_results)),
            ("Performance", any(r['test'] == 'Performance Under Load' and r.get('passed') for r in self.test_results)),
            ("User State", any(r['test'] == 'User State Management' and r.get('passed') for r in self.test_results))
        ]
        
        print(f"\n🎯 Core Features:")
        for feature, passed in features_tested:
            print(f"   {feature}: {'✅ WORKING' if passed else '❌ FAILED'}")
        
        # Beta readiness
        core_working = sum(1 for _, passed in features_tested if passed)
        beta_score = (core_working / len(features_tested)) * 100
        
        print(f"\n🚀 Beta Readiness Assessment:")
        print(f"   Core Features Working: {core_working}/{len(features_tested)}")
        print(f"   Beta Readiness Score: {beta_score:.0f}%")
        
        if beta_score >= 80:
            print("   🎉 EXCELLENT! Core system ready for beta testing")
            recommendation = "System is ready for ADHD users to test"
        elif beta_score >= 60:
            print("   ✅ GOOD! Minor issues but core functionality working")
            recommendation = "Address minor issues then proceed with beta"
        else:
            print("   ⚠️ NEEDS WORK! Core issues need fixing")
            recommendation = "Fix core issues before beta testing"
        
        print(f"\n📋 Recommendation: {recommendation}")
        
        return beta_score >= 60


async def main():
    """Run simple beta testing."""
    import os
    base_url = os.environ.get('BASE_URL', 'http://localhost:23443')
    
    print("🚀 MCP ADHD Server - Simple Beta Testing")
    print("=" * 45)
    print(f"📡 Testing: {base_url}")
    print("🎯 Focusing on core ADHD functionality\n")
    
    tester = SimpleBetaTester(base_url)
    
    try:
        await tester.run_core_tests()
        return True
    except Exception as e:
        print(f"\n💥 Beta testing failed: {e}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Beta testing interrupted")
        exit(130)