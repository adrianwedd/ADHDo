#!/usr/bin/env python3
"""
Timer System - Manages timers and reminders
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import uuid

logger = logging.getLogger(__name__)


class TimerSystem:
    """Manages timers for work blocks, breaks, etc."""
    
    def __init__(self):
        self.active_timers: Dict[str, Dict] = {}
        
    async def set_timer(self, minutes: int, purpose: str = "work", message: str = None) -> str:
        """Set a timer that will trigger after specified minutes."""
        timer_id = str(uuid.uuid4())[:8]
        
        if not message:
            message = f"Timer for {purpose} has ended!"
        
        timer_info = {
            "id": timer_id,
            "duration_minutes": minutes,
            "purpose": purpose,
            "message": message,
            "start_time": datetime.now(),
            "end_time": datetime.now() + timedelta(minutes=minutes),
            "active": True
        }
        
        self.active_timers[timer_id] = timer_info
        
        # Schedule the timer callback
        asyncio.create_task(self._timer_callback(timer_id, minutes, message))
        
        logger.info(f"Set {purpose} timer for {minutes} minutes (ID: {timer_id})")
        
        return timer_id
    
    async def _timer_callback(self, timer_id: str, minutes: int, message: str):
        """Callback when timer expires."""
        await asyncio.sleep(minutes * 60)
        
        if timer_id in self.active_timers and self.active_timers[timer_id]["active"]:
            logger.info(f"Timer {timer_id} expired: {message}")
            
            # TODO: Trigger actual notification/nudge
            # For now just mark as expired
            self.active_timers[timer_id]["active"] = False
            
            # Could integrate with nudge system here
            from .nest_nudges import NestNudgeSystem
            nudges = NestNudgeSystem()
            await nudges.send_nudge(message, urgency="normal")
    
    async def cancel_timer(self, timer_id: Optional[str] = None) -> Dict[str, Any]:
        """Cancel a timer or all timers."""
        if timer_id:
            if timer_id in self.active_timers:
                self.active_timers[timer_id]["active"] = False
                logger.info(f"Cancelled timer {timer_id}")
                return {"status": "cancelled", "timer_id": timer_id}
            else:
                return {"status": "not_found", "timer_id": timer_id}
        else:
            # Cancel all timers
            for tid in self.active_timers:
                self.active_timers[tid]["active"] = False
            logger.info("Cancelled all timers")
            return {"status": "all_cancelled"}
    
    def get_active_timers(self) -> List[Dict[str, Any]]:
        """Get list of active timers."""
        active = []
        now = datetime.now()
        
        for timer_id, info in self.active_timers.items():
            if info["active"]:
                remaining = (info["end_time"] - now).total_seconds() / 60
                active.append({
                    "id": timer_id,
                    "purpose": info["purpose"],
                    "remaining_minutes": max(0, int(remaining)),
                    "message": info["message"]
                })
        
        return active