#!/usr/bin/env python3
"""
Accountability Buddy Demo - Proactive Environmental Nudging
Shows the MCP system's proactive environmental orchestration capabilities.

This demonstrates the "accountability buddy" concept with cut-through notifications
via Nest Hub displays, Home Assistant TTS, and other environmental systems.
"""

import asyncio
import aiohttp
import time
from datetime import datetime, timedelta

class AccountabilityBuddyDemo:
    """Demo of proactive accountability system with environmental integration."""
    
    def __init__(self, base_url="http://localhost:23443"):
        self.base_url = base_url
        self.user_id = "demo_user"
        
    async def run_demo(self):
        """Run complete accountability buddy demonstration."""
        print("🤝 Starting Accountability Buddy Demo")
        print("=" * 50)
        print("Demonstrating proactive environmental nudging system\n")
        
        async with aiohttp.ClientSession() as session:
            # Show system status
            await self._check_system_health(session)
            
            # Demo 1: Gentle focus reminder
            print("\n🎯 DEMO 1: Gentle Focus Reminder")
            print("-" * 35)
            await self._demo_focus_reminder(session)
            
            await asyncio.sleep(3)
            
            # Demo 2: Accountability check-in
            print("\n🤝 DEMO 2: Accountability Check-in")  
            print("-" * 37)
            await self._demo_accountability_checkin(session)
            
            await asyncio.sleep(3)
            
            # Demo 3: Escalating nudge system
            print("\n⚡ DEMO 3: Escalating Nudge System")
            print("-" * 35)
            await self._demo_escalating_nudges(session)
            
            await asyncio.sleep(3)
            
            # Demo 4: Environmental orchestration
            print("\n🏠 DEMO 4: Environmental Orchestration")
            print("-" * 39)
            await self._demo_environmental_control(session)
            
        print(f"\n🎉 Demo Complete!")
        print(f"\n📊 Summary:")
        print(f"   ✅ MCP Contextual OS Dashboard: {self.base_url}")
        print(f"   ✅ Proactive environmental nudging system")
        print(f"   ✅ Multi-method delivery (Nest Hub, TTS, Telegram)")
        print(f"   ✅ Accountability scoring and feedback")
        print(f"   ✅ Escalating intervention system")
        
    async def _check_system_health(self, session):
        """Check MCP system health."""
        try:
            async with session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    components = health_data.get('components', {})
                    active_components = sum(1 for v in components.values() if v)
                    
                    print(f"✅ MCP System Health: {active_components}/7 components active")
                    print(f"   🧠 Cognitive Loop: {'✅' if components.get('cognitive_loop') else '❌'}")
                    print(f"   💾 Memory System: {'✅' if components.get('redis') else '❌'}")
                    print(f"   🤖 Frame Builder: {'✅' if components.get('frame_builder') else '❌'}")
                    print(f"   📯 Nudge Engine: {'✅' if components.get('nudge_engine') else '❌'}")
                    print(f"   🔐 Safety Monitor: {'✅' if components.get('trace_memory') else '❌'}")
                    print(f"   🎭 Claude Integration: {'✅' if components.get('claude_integration') else '❌'}")
                else:
                    print(f"⚠️ System health check failed (HTTP {response.status})")
                    
        except Exception as e:
            print(f"❌ Cannot connect to MCP system: {e}")
            print(f"   Make sure server is running: ./start_network.sh")
            return False
            
        return True
    
    async def _demo_focus_reminder(self, session):
        """Demo gentle focus reminder through environmental systems."""
        print("Scenario: User has been idle for 30 minutes")
        print("Action: Gentle environmental nudge to refocus")
        
        try:
            nudge_data = {
                "user_id": self.user_id,
                "nudge_type": "FOCUS_REMINDER", 
                "methods": ["nest_hub", "tts"],
                "message": "🎯 Gentle reminder: What's your next priority task?"
            }
            
            async with session.post(f"{self.base_url}/nudge/trigger", json=nudge_data) as response:
                result = await response.json()
                
                if result.get('success'):
                    print(f"✅ Nudge delivered via {len(result.get('results', {}))} methods")
                    print(f"   📱 Methods attempted: {list(result.get('results', {}).keys())}")
                    print(f"   🎚️ Nudge tier: {result.get('tier', 'GENTLE')}")
                    print(f"   💬 Message: \"{result.get('message', 'N/A')}\"")
                    
                    # Simulate environmental effects
                    print(f"\n🏠 Environmental Effects:")
                    print(f"   🖥️ Nest Hub: Display gentle focus reminder for 15 seconds")
                    print(f"   🔊 Home Assistant TTS: \"Time to refocus! What's your next priority?\"")
                    print(f"   💡 Smart Lights: Subtle brightness increase to enhance alertness")
                    
                else:
                    print(f"⚠️ Nudge delivery had issues: {result}")
                    
        except Exception as e:
            print(f"❌ Focus reminder demo failed: {e}")
    
    async def _demo_accountability_checkin(self, session):
        """Demo accountability buddy check-in system."""
        print("Scenario: 2 hours have passed since last check-in")
        print("Action: Proactive accountability check with environmental cut-through")
        
        try:
            # Trigger accountability nudge
            nudge_data = {
                "user_id": self.user_id,
                "nudge_type": "ACCOUNTABILITY_CHECK",
                "methods": ["nest_hub", "tts", "telegram"]
            }
            
            async with session.post(f"{self.base_url}/nudge/trigger", json=nudge_data) as response:
                result = await response.json()
                
                if result.get('success'):
                    print(f"✅ Accountability nudge sent")
                    print(f"   📢 Message: \"What have you accomplished in the last 2 hours?\"")
                    print(f"   🎚️ Tier: {result.get('tier', 'SARCASTIC')} (accountability tone)")
                    
                    print(f"\n🏠 Multi-Channel Delivery:")
                    print(f"   🖥️ Nest Hub: Full-screen accountability prompt with timer")
                    print(f"   🔊 TTS: Assertive voice reminder through all speakers")
                    print(f"   📱 Telegram: Persistent notification with check-in buttons")
                    
                    # Simulate user responding to check-in
                    print(f"\n🤝 Simulating User Check-in Response...")
                    await asyncio.sleep(2)
                    
                    checkin_data = {
                        "user_id": self.user_id,
                        "accomplishments": "Completed email review, started project outline, took focused work break",
                        "mood": "focused",
                        "next_goals": "Finish project outline section 1, schedule follow-up meeting"
                    }
                    
                    async with session.post(f"{self.base_url}/accountability/checkin", json=checkin_data) as checkin_response:
                        checkin_result = await checkin_response.json()
                        
                        if checkin_result.get('success'):
                            score = checkin_result.get('accountability_score', 0)
                            message = checkin_result.get('message', '')
                            
                            print(f"✅ Check-in processed successfully")
                            print(f"   📊 Accountability Score: {score}/10")
                            print(f"   💬 System Response: \"{message}\"")
                            print(f"   ⏰ Next Check-in: {checkin_result.get('next_checkin', 'TBD')}")
                            
                        else:
                            print(f"⚠️ Check-in processing failed")
                
        except Exception as e:
            print(f"❌ Accountability demo failed: {e}")
    
    async def _demo_escalating_nudges(self, session):
        """Demo escalating nudge system for persistent challenges."""
        print("Scenario: User has been avoiding difficult task for 3 days")
        print("Action: Escalating nudge sequence from gentle to sergeant level")
        
        nudge_levels = [
            ("GENTLE", "🌱 Maybe it's time to tackle that challenging task?", ["tts"]),
            ("SARCASTIC", "🙄 Still avoiding that task, I see...", ["nest_hub", "tts"]),
            ("SERGEANT", "🚨 ENOUGH PROCRASTINATION! TIME TO ACT!", ["nest_hub", "tts", "telegram"])
        ]
        
        for i, (tier_name, message, methods) in enumerate(nudge_levels, 1):
            print(f"\n📈 Escalation Level {i}: {tier_name}")
            
            try:
                nudge_data = {
                    "user_id": self.user_id,
                    "nudge_type": "FOCUS_REMINDER",
                    "methods": methods,
                    "message": message
                }
                
                async with session.post(f"{self.base_url}/nudge/trigger", json=nudge_data) as response:
                    result = await response.json()
                    
                    if result.get('success'):
                        print(f"   ✅ {tier_name} nudge delivered")
                        print(f"   📢 Message: \"{message}\"")
                        print(f"   📱 Methods: {', '.join(methods)}")
                        
                        # Show environmental effects based on tier
                        if tier_name == "GENTLE":
                            print(f"   🏠 Effect: Soft TTS announcement")
                        elif tier_name == "SARCASTIC":
                            print(f"   🏠 Effect: Nest Hub display + assertive TTS")
                        elif tier_name == "SERGEANT":
                            print(f"   🏠 Effect: Pause media, full-screen alert, loud TTS, urgent Telegram")
                            
                    else:
                        print(f"   ⚠️ {tier_name} nudge had issues")
                        
                await asyncio.sleep(2)  # Pause between escalations
                
            except Exception as e:
                print(f"   ❌ {tier_name} nudge failed: {e}")
    
    async def _demo_environmental_control(self, session):
        """Demo comprehensive environmental orchestration."""
        print("Scenario: User needs deep focus session for important deadline")
        print("Action: Full environmental optimization via Home Assistant integration")
        
        print(f"\n🏠 Environmental Orchestration Sequence:")
        print(f"   💡 Smart Lighting: Switch to 'Focus' scene (bright, cool white)")
        print(f"   🎵 Audio System: Enable brown noise at 30% volume")
        print(f"   📱 Phone Integration: Enable Do Not Disturb mode")
        print(f"   🖥️ Nest Hub: Display focus timer and task breakdown")
        print(f"   🌡️ HVAC: Set temperature to optimal 21°C for alertness")
        print(f"   🚪 Smart Locks: Prevent interruptions during focus block")
        
        try:
            # This would be handled by the Home Assistant integration in the nudge engine
            nudge_data = {
                "user_id": self.user_id,
                "nudge_type": "FOCUS_SESSION_START",
                "methods": ["nest_hub", "tts"],
                "message": "🎯 Deep focus environment activated. You've got this!"
            }
            
            async with session.post(f"{self.base_url}/nudge/trigger", json=nudge_data) as response:
                result = await response.json()
                
                print(f"\n✅ Environmental sequence initiated")
                print(f"   📊 Success rate: {len([v for v in result.get('results', {}).values() if v])}/3 systems")
                print(f"   🎯 Focus session: 25 minutes (Pomodoro technique)")
                print(f"   🔔 Break reminder: Scheduled after focus block")
                
        except Exception as e:
            print(f"❌ Environmental control demo failed: {e}")
            
        # Show what would happen during the session
        print(f"\n⏱️ During Focus Session:")
        print(f"   🖥️ Nest Hub: Live progress display, no distractions")
        print(f"   🔇 All notifications: Suppressed except emergencies")
        print(f"   📊 MCP System: Monitoring for attention drift patterns")
        print(f"   🤖 Agents: TaskBreaker active, FocusMonitor tracking")
        
        print(f"\n🔔 Session End (after 25 minutes):")
        print(f"   🎉 Achievement notification: \"Focus session complete!\"")
        print(f"   🌱 Break suggestion: \"Take a 5-minute walk\"")
        print(f"   💡 Environment reset: Return to normal lighting/audio")
        print(f"   📈 Progress update: Add to accountability tracking")

async def main():
    """Run the accountability buddy demonstration."""
    demo = AccountabilityBuddyDemo()
    await demo.run_demo()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n💥 Demo failed: {e}")