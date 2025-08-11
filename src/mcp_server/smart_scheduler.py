"""
Smart Nudge Scheduler - Intelligent ADHD scheduling with LLM integration
Implements time-based nudging with escalation and personalization.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

import structlog
from mcp_server.llm_client import OllamaClient, LLMResponse
from mcp_server.nest_nudges import nest_nudge_system, NudgeType

logger = structlog.get_logger()

class ScheduleType(Enum):
    """Types of scheduled nudges."""
    BEDTIME = "bedtime"
    WAKEUP = "wakeup" 
    MEDICATION = "medication"
    BREAK_TIME = "break_time"
    TASK_DEADLINE = "task_deadline"
    FOCUS_SESSION = "focus_session"
    CUSTOM = "custom"

@dataclass
class NudgeSchedule:
    """Represents a scheduled nudge with escalation logic."""
    schedule_id: str
    user_id: str = "default"
    schedule_type: ScheduleType = ScheduleType.CUSTOM
    target_time: str = "22:00"  # HH:MM format
    title: str = "Reminder"
    context: str = ""
    
    # Escalation settings
    enabled: bool = True
    pre_nudge_minutes: int = 15  # Warn 15 min before
    escalation_intervals: List[int] = None  # [5, 10, 15] minutes
    max_attempts: int = 5
    
    # Personalization
    tone: str = "encouraging"  # encouraging, firm, playful, urgent
    include_context: bool = True
    use_llm: bool = True
    
    # State tracking
    current_attempt: int = 0
    last_nudge_time: Optional[datetime] = None
    acknowledged: bool = False
    snoozed_until: Optional[datetime] = None
    
    def __post_init__(self):
        if self.escalation_intervals is None:
            self.escalation_intervals = [5, 10, 15, 20, 30]  # Escalating delays

@dataclass 
class NudgeContext:
    """Context information for generating intelligent nudges."""
    user_name: str = "there"
    current_activity: Optional[str] = None
    time_until_target: int = 0  # minutes
    attempt_number: int = 1
    previous_responses: List[str] = None
    recent_accomplishments: List[str] = None
    energy_level: str = "normal"  # low, normal, high
    stress_level: str = "normal"  # low, normal, high
    
    def __post_init__(self):
        if self.previous_responses is None:
            self.previous_responses = []
        if self.recent_accomplishments is None:
            self.recent_accomplishments = []

class SmartScheduler:
    """Intelligent nudge scheduler with LLM integration and escalation."""
    
    def __init__(self):
        self.schedules: Dict[str, NudgeSchedule] = {}
        self.active_sequences: Dict[str, asyncio.Task] = {}
        self.llm_client = OllamaClient()
        self.scheduler_task: Optional[asyncio.Task] = None
        
        # Load default bedtime schedule
        self.schedules["bedtime_default"] = NudgeSchedule(
            schedule_id="bedtime_default",
            schedule_type=ScheduleType.BEDTIME,
            target_time="22:00",
            title="Bedtime",
            context="It's important to get good sleep for ADHD brain regulation",
            tone="encouraging",
            escalation_intervals=[10, 15, 20, 25, 30]
        )
    
    async def initialize(self) -> bool:
        """Start the scheduler."""
        try:
            self.scheduler_task = asyncio.create_task(self._main_scheduler_loop())
            logger.info("📅 Smart scheduler initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
            return False
    
    async def _main_scheduler_loop(self):
        """Main scheduling loop - checks every minute for due nudges."""
        logger.info("⏰ Smart scheduler loop started")
        
        while True:
            try:
                current_time = datetime.now()
                
                # Check all schedules for due nudges
                for schedule_id, schedule in self.schedules.items():
                    if not schedule.enabled:
                        continue
                        
                    # Parse target time
                    try:
                        target_hour, target_minute = map(int, schedule.target_time.split(':'))
                        target_today = current_time.replace(
                            hour=target_hour, 
                            minute=target_minute, 
                            second=0, 
                            microsecond=0
                        )
                    except ValueError:
                        logger.error(f"Invalid time format for schedule {schedule_id}: {schedule.target_time}")
                        continue
                    
                    # Check if we should start pre-nudging
                    pre_nudge_time = target_today - timedelta(minutes=schedule.pre_nudge_minutes)
                    
                    # Start nudge sequence if it's time and not already active
                    if (current_time >= pre_nudge_time and 
                        current_time <= target_today + timedelta(hours=2) and  # 2 hour window
                        schedule_id not in self.active_sequences and
                        not schedule.acknowledged and
                        (schedule.snoozed_until is None or current_time >= schedule.snoozed_until)):
                        
                        logger.info(f"🎯 Starting nudge sequence for {schedule.title}")
                        task = asyncio.create_task(self._run_nudge_sequence(schedule))
                        self.active_sequences[schedule_id] = task
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)
    
    async def _run_nudge_sequence(self, schedule: NudgeSchedule):
        """Run complete nudge sequence with escalation for a schedule."""
        try:
            logger.info(f"📢 Starting nudge sequence: {schedule.title}")
            
            # Reset state for new sequence
            schedule.current_attempt = 0
            schedule.acknowledged = False
            
            # Initial nudge (pre-warning)
            await self._send_intelligent_nudge(schedule, is_pre_nudge=True)
            
            # Wait for target time
            target_hour, target_minute = map(int, schedule.target_time.split(':'))
            target_time = datetime.now().replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
            
            if target_time > datetime.now():
                wait_seconds = (target_time - datetime.now()).total_seconds()
                await asyncio.sleep(wait_seconds)
            
            # Main nudge sequence with escalation
            for attempt in range(schedule.max_attempts):
                if schedule.acknowledged:
                    logger.info(f"✅ {schedule.title} acknowledged, stopping sequence")
                    break
                
                schedule.current_attempt = attempt + 1
                
                # Send escalating nudge
                await self._send_intelligent_nudge(schedule)
                
                # Wait for escalation interval
                if attempt < len(schedule.escalation_intervals):
                    wait_minutes = schedule.escalation_intervals[attempt]
                else:
                    wait_minutes = schedule.escalation_intervals[-1]  # Use last interval
                
                logger.info(f"⏰ Waiting {wait_minutes} minutes before next nudge attempt")
                await asyncio.sleep(wait_minutes * 60)
            
            # Cleanup
            if schedule.schedule_id in self.active_sequences:
                del self.active_sequences[schedule.schedule_id]
                
        except asyncio.CancelledError:
            logger.info(f"Nudge sequence cancelled for {schedule.title}")
        except Exception as e:
            logger.error(f"Nudge sequence error for {schedule.title}: {e}")
    
    async def _send_intelligent_nudge(self, schedule: NudgeSchedule, is_pre_nudge: bool = False):
        """Generate and send an intelligent nudge using LLM."""
        try:
            # Build context for LLM
            current_time = datetime.now()
            target_hour, target_minute = map(int, schedule.target_time.split(':'))
            target_time = current_time.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
            
            time_until_target = int((target_time - current_time).total_seconds() / 60)
            
            context = NudgeContext(
                user_name="there",  # Could be personalized
                time_until_target=time_until_target,
                attempt_number=schedule.current_attempt,
                energy_level="normal"  # Could be detected
            )
            
            # Generate intelligent message (use rich template bank for variety)
            message = self._generate_template_nudge(schedule, context, is_pre_nudge)
            
            # Send via TTS
            if nest_nudge_system:
                nudge_type = self._get_nudge_type(schedule, is_pre_nudge)
                success = await nest_nudge_system.send_nudge(
                    message=message,
                    nudge_type=nudge_type,
                    volume=0.6 if schedule.current_attempt < 3 else 0.8
                )
                
                if success:
                    schedule.last_nudge_time = current_time
                    logger.info(f"📢 Sent {schedule.schedule_type.value} nudge: {message[:50]}...")
                else:
                    logger.error(f"Failed to send nudge for {schedule.title}")
            
        except Exception as e:
            logger.error(f"Failed to send intelligent nudge: {e}")
    
    async def _generate_llm_nudge(self, schedule: NudgeSchedule, context: NudgeContext, is_pre_nudge: bool) -> str:
        """Generate personalized nudge using LLM."""
        
        # Build system prompt for ADHD-aware nudging
        system_prompt = f"""You are an ADHD accountability buddy. Generate a {schedule.tone} nudge message.

Guidelines:
- Keep it conversational and personal (20-40 words max)
- Consider ADHD patterns: executive dysfunction, time blindness, hyperfocus
- Be encouraging but effective
- Escalate intensity based on attempt number
- Use "you" language, not "I" language
- Sound natural and varied, avoid corporate language

Schedule: {schedule.title} at {schedule.target_time}
Context: {schedule.context}
Attempt: {context.attempt_number}/{schedule.max_attempts}
"""
        
        if is_pre_nudge:
            user_prompt = f"Generate a gentle pre-reminder that {schedule.title} is coming up in {context.time_until_target} minutes. Help them prepare mentally."
        else:
            if context.attempt_number <= 2:
                user_prompt = f"It's time for {schedule.title}. Generate an encouraging reminder to help them transition."
            elif context.attempt_number <= 4:
                user_prompt = f"This is attempt {context.attempt_number}. They haven't responded to {schedule.title} yet. Be more direct but still supportive."
            else:
                user_prompt = f"Final attempt for {schedule.title}. Be firm but understanding - ADHD brains need clear boundaries."
        
        try:
            response = await self.llm_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=60,  # Shorter for faster generation
                temperature=0.8  # Higher for more variation
            )
            
            # Clean up response (remove quotes, thinking tags, etc.)
            message = response.text.strip()
            if message.startswith('"') and message.endswith('"'):
                message = message[1:-1]
            
            return message
            
        except Exception as e:
            logger.error(f"LLM nudge generation failed: {e}")
            # Fallback to template
            return self._generate_template_nudge(schedule, context, is_pre_nudge)
    
    def _generate_template_nudge(self, schedule: NudgeSchedule, context: NudgeContext, is_pre_nudge: bool) -> str:
        """Generate nudge using templates as fallback."""
        
        if is_pre_nudge:
            return f"Hey! Just a heads up - {schedule.title} is coming up in {context.time_until_target} minutes. Start wrapping up what you're doing."
        
        templates = {
            ScheduleType.BEDTIME: [
                # Gentle/Encouraging (attempts 1-2)
                "Time to start your bedtime routine. Your brain needs that sleep to function well tomorrow.",
                "Hey, bedtime is here. Your ADHD brain will work better with consistent sleep.",
                "Sleep time! Your executive function depends on good rest.",
                "Bedtime routine time. Your future self will thank you for this.",
                "Time to wind down. Your brain needs this sleep to reset properly.",
                "Sleep is calling! Your ADHD symptoms are lighter when you're well-rested.",
                "Bedtime! Let's give your brain the rest it needs to function.",
                "Time to power down. Your focus tomorrow depends on sleep tonight.",
                "Sleep time. Your brain does amazing repair work while you rest.",
                "Bedtime routine! Your dopamine system needs this regular schedule.",
                "Time to rest. Your working memory works better after good sleep.",
                "Sleep time! Your emotional regulation depends on getting enough rest.",
                "Bedtime is here. Your brain needs this downtime to process today.",
                "Time to sleep. Your attention span improves with consistent rest.",
                "Sleep routine time! Your hyperactivity calms down with proper rest.",
                "Time for bed. Your brain's executive functions reset during sleep.",
                "Sleep time. Your impulse control is better when you're well-rested.",
                "Bedtime! Your focus and creativity both need this sleep.",
                "Time to rest. Your brain organizes memories while you sleep.",
                "Sleep is brain medicine for ADHD. Time to take your dose.",
                
                # Motivational/Direct (attempts 3-4)
                "Bedtime! Your ADHD brain will thank you for consistent sleep. Let's wind down.",
                "Sleep time! Put the screens down and start your bedtime routine.",
                "Your executive function depends on good sleep. Time to head to bed.",
                "Seriously, bedtime. Your brain chemistry needs this regular sleep cycle.",
                "Time to sleep! Your ADHD symptoms get worse when you're tired.",
                "Bedtime routine now. Your dopamine levels need this consistent schedule.",
                "Sleep time! Your hyperfocus tendencies calm down with proper rest.",
                "Time for bed. Your racing thoughts will settle with good sleep.",
                "Sleep now! Your emotional dysregulation gets worse without rest.",
                "Bedtime! Your working memory crashes when you're sleep-deprived.",
                "Time to sleep. Your brain fog clears up with consistent rest.",
                "Sleep time! Your procrastination gets worse when you're tired.",
                "Bedtime now. Your time perception is even worse without sleep.",
                "Time to rest! Your task-switching abilities need this sleep.",
                "Sleep! Your rejection sensitivity spikes when you're tired.",
                "Bedtime routine time. Your anxiety is manageable with good sleep.",
                "Time to sleep! Your decision-making improves with proper rest.",
                "Sleep now! Your social interactions are easier when well-rested.",
                "Bedtime! Your energy levels stabilize with consistent sleep.",
                "Time for sleep! Your medication works better when you're rested.",
                
                # Firm/Urgent (attempts 5+)
                "Bedtime means bedtime. Your future self will thank you for this discipline.",
                "Sleep NOW! Your ADHD brain is already struggling without proper rest.",
                "BEDTIME. Your executive dysfunction gets exponentially worse when tired.",
                "Time to sleep! Stop negotiating with yourself and just go to bed.",
                "SLEEP TIME! Your brain is literally starving for rest right now.",
                "Bedtime is NOT optional. Your ADHD symptoms are chaos without sleep.",
                "SLEEP NOW! Your hyperfocus is keeping you up but you NEED rest.",
                "BEDTIME! Your brain chemistry is already out of whack from poor sleep.",
                "Time to sleep! Your working memory is shot when you're tired.",
                "SLEEP! Your emotional regulation is hanging by a thread right now.",
                "BEDTIME NOW! Your dopamine system needs this sleep to function.",
                "Time for bed! Your impulse control disappears without proper rest.",
                "SLEEP TIME! Your focus is already compromised - don't make it worse.",
                "BEDTIME! Your procrastination spiral starts with poor sleep habits.",
                "Time to SLEEP! Your brain fog will be terrible tomorrow without rest.",
                "SLEEP NOW! Your time blindness is getting worse by the minute.",
                "BEDTIME! Your rejection sensitivity skyrockets when you're tired.",
                "Time for sleep! Your anxiety spirals without proper rest cycles.",
                "SLEEP! Your task paralysis gets worse when your brain is exhausted.",
                "BEDTIME NOW! Your future self is begging you to get some sleep.",
                
                # Creative/Varied approaches
                "Your brain is like a phone battery at 5%. Time to charge up with sleep!",
                "Sleep is your ADHD superpower charging station. Time to plug in!",
                "Your neurons are throwing a party but it's time to send them to bed.",
                "Time to give your overworked prefrontal cortex a break. Sleep time!",
                "Your brain's filing system only works during sleep. Time to organize!",
                "Sleep is when your brain takes out the garbage. Time for cleanup!",
                "Your dopamine factory needs to shut down for maintenance. Sleep time!",
                "Time to reboot your biological operating system. Sleep mode activated!",
                "Your brain is like a computer that needs to defragment. Sleep does that!",
                "Time to let your glymphatic system clean house. Sleep is brain detox!",
                "Your executive function CPU is overheating. Time to cool down with sleep!",
                "Sleep is your brain's reset button. Time to press it!",
                "Your working memory RAM is full. Sleep empties the cache!",
                "Time to let your brain's IT department run overnight updates!",
                "Your attention spotlight needs new batteries. Sleep provides the charge!",
                "Sleep is when your brain librarian organizes all the day's information.",
                "Time to give your mental browser 47 open tabs a break. Sleep closes them!",
                "Your brain's quality control team only works night shift. Time for sleep!",
                "Sleep is your brain's spa day. Time for some neural rejuvenation!",
                "Your cognitive engine is running hot. Time for a sleep cooldown!",
                
                # Time-specific variants
                "It's past your bedtime. Your circadian rhythm is already confused.",
                "You're in the overtired zone now. Sleep becomes harder the longer you wait.",
                "Your sleep debt is accumulating interest. Time to make a payment!",
                "The sleep train is leaving the station. Don't miss it again!",
                "Your natural melatonin window is closing. Catch it while you can!",
                "Every minute past bedtime makes tomorrow harder. Sleep now!",
                "Your body clock is screaming at you. Listen to it!",
                "The golden hour for sleep is slipping away. Grab it!",
                "Your sleep pressure is at maximum. Release the valve with rest!",
                "You're fighting your natural sleep drive. Stop resisting and sleep!"
            ],
            ScheduleType.MEDICATION: [
                "Medication time! Don't let ADHD symptoms sneak back in.",
                "Time for your meds. This is how you stay on top of your day.",
                "Medication reminder - consistency is key for ADHD management.",
                "Med time! Your brain needs this chemical support.",
                "Don't skip your medication. Your focus depends on it."
            ]
        }
        
        # Get templates for this schedule type
        type_templates = templates.get(schedule.schedule_type, [
            f"Time for {schedule.title}. Let's make it happen.",
            f"Reminder: {schedule.title} is due now.",
            f"Don't forget about {schedule.title}!"
        ])
        
        # Smart template selection based on attempt and context
        import random
        
        if context.attempt_number <= 2:
            # Gentle messages (first 20 templates)
            gentle_templates = type_templates[:20]
            return random.choice(gentle_templates) if gentle_templates else f"Gentle reminder: time for {schedule.title}"
        elif context.attempt_number <= 4:
            # Motivational/Direct messages (next 20 templates)
            motivational_templates = type_templates[20:40] if len(type_templates) > 20 else type_templates[-20:]
            return random.choice(motivational_templates) if motivational_templates else f"Time for {schedule.title}"
        else:
            # Firm/Urgent messages (next 20 templates)
            urgent_templates = type_templates[40:60] if len(type_templates) > 40 else type_templates[-20:]
            return random.choice(urgent_templates) if urgent_templates else f"URGENT: {schedule.title} NOW!"
        
        # If we have even more templates, mix in creative and time-specific ones
        if len(type_templates) > 60:
            extra_templates = type_templates[60:]
            if context.attempt_number >= 3 and random.random() < 0.3:  # 30% chance for creative approach
                return random.choice(extra_templates)
    
    def _get_nudge_type(self, schedule: NudgeSchedule, is_pre_nudge: bool) -> NudgeType:
        """Determine nudge type based on schedule and attempt."""
        if is_pre_nudge:
            return NudgeType.GENTLE
        
        if schedule.current_attempt <= 1:
            return NudgeType.GENTLE
        elif schedule.current_attempt <= 3:
            return NudgeType.MOTIVATIONAL
        else:
            return NudgeType.URGENT
    
    async def add_schedule(self, schedule: NudgeSchedule) -> bool:
        """Add a new nudge schedule."""
        try:
            self.schedules[schedule.schedule_id] = schedule
            logger.info(f"📅 Added schedule: {schedule.title} at {schedule.target_time}")
            return True
        except Exception as e:
            logger.error(f"Failed to add schedule: {e}")
            return False
    
    async def acknowledge_nudge(self, schedule_id: str) -> bool:
        """Acknowledge a nudge to stop the sequence."""
        if schedule_id in self.schedules:
            self.schedules[schedule_id].acknowledged = True
            
            # Cancel active sequence
            if schedule_id in self.active_sequences:
                self.active_sequences[schedule_id].cancel()
                del self.active_sequences[schedule_id]
            
            logger.info(f"✅ Acknowledged nudge: {schedule_id}")
            return True
        return False
    
    async def snooze_nudge(self, schedule_id: str, minutes: int = 10) -> bool:
        """Snooze a nudge for specified minutes."""
        if schedule_id in self.schedules:
            self.schedules[schedule_id].snoozed_until = datetime.now() + timedelta(minutes=minutes)
            
            # Cancel current sequence
            if schedule_id in self.active_sequences:
                self.active_sequences[schedule_id].cancel()
                del self.active_sequences[schedule_id]
                
            logger.info(f"😴 Snoozed nudge {schedule_id} for {minutes} minutes")
            return True
        return False
    
    def get_schedules(self) -> List[Dict[str, Any]]:
        """Get all schedules as dict for API."""
        return [asdict(schedule) for schedule in self.schedules.values()]
    
    async def cleanup(self):
        """Clean up scheduler resources."""
        # Cancel all active sequences
        for task in self.active_sequences.values():
            task.cancel()
        
        # Cancel main scheduler
        if self.scheduler_task:
            self.scheduler_task.cancel()

# Global scheduler instance
smart_scheduler: Optional[SmartScheduler] = None

async def initialize_smart_scheduler() -> bool:
    """Initialize the smart scheduler."""
    global smart_scheduler
    
    try:
        smart_scheduler = SmartScheduler()
        success = await smart_scheduler.initialize()
        
        if success:
            logger.info("🧠 Smart scheduler initialized")
            return True
        else:
            smart_scheduler = None
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize smart scheduler: {e}")
        smart_scheduler = None
        return False