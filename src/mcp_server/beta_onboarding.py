"""
Beta Tester Onboarding System for MCP ADHD Server

Provides automated account creation and streamlined onboarding for beta testers.
"""

import secrets
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
import qrcode
from io import BytesIO
import base64

import structlog
from fastapi import HTTPException
from pydantic import BaseModel, EmailStr

from mcp_server.auth import auth_manager, RegistrationRequest
from mcp_server.models import User
from mcp_server.onboarding import onboarding_manager
from mcp_server.config import settings

logger = structlog.get_logger()


class BetaInvite(BaseModel):
    """Beta tester invitation."""
    invite_code: str
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    used_at: Optional[datetime] = None
    user_id: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    onboarding_completed: bool = False


class QuickSetupRequest(BaseModel):
    """Quick setup request for beta testers."""
    invite_code: str
    name: str
    email: EmailStr
    password: str
    telegram_chat_id: Optional[str] = None
    energy_patterns: Optional[Dict[str, Any]] = None
    preferred_nudge_methods: Optional[List[str]] = None


class BetaOnboardingManager:
    """Manages beta tester invitations and automated onboarding."""
    
    def __init__(self):
        self._invites: Dict[str, BetaInvite] = {}
        
    def generate_invite_code(self) -> str:
        """Generate a unique invite code."""
        return f"ADHD-{secrets.token_urlsafe(8).upper()}"
    
    def create_invite(
        self,
        expires_hours: int = 168,  # 1 week
        email: Optional[str] = None,
        name: Optional[str] = None
    ) -> BetaInvite:
        """Create a new beta invite."""
        invite_code = self.generate_invite_code()
        
        invite = BetaInvite(
            invite_code=invite_code,
            email=email,
            name=name,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=expires_hours)
        )
        
        self._invites[invite_code] = invite
        
        logger.info(
            "Beta invite created",
            invite_code=invite_code,
            email=email,
            expires_at=invite.expires_at.isoformat()
        )
        
        return invite
    
    def get_invite(self, invite_code: str) -> Optional[BetaInvite]:
        """Get an invite by code."""
        return self._invites.get(invite_code)
    
    def is_invite_valid(self, invite_code: str) -> bool:
        """Check if an invite is valid and unused."""
        invite = self._invites.get(invite_code)
        if not invite:
            return False
        
        # Check if expired
        if datetime.utcnow() > invite.expires_at:
            return False
        
        # Check if already used
        if invite.used_at:
            return False
        
        return True
    
    def generate_setup_url(self, invite_code: str, base_url: str = "http://localhost:8000") -> str:
        """Generate a setup URL for beta testers."""
        return f"{base_url}/beta/setup?invite={invite_code}"
    
    def generate_qr_code(self, invite_code: str, base_url: str = "http://localhost:8000") -> str:
        """Generate a QR code for the setup URL."""
        setup_url = self.generate_setup_url(invite_code, base_url)
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(setup_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for web display
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    async def quick_setup(self, setup_request: QuickSetupRequest) -> Dict[str, Any]:
        """Complete automated setup for a beta tester."""
        # Validate invite
        if not self.is_invite_valid(setup_request.invite_code):
            raise ValueError("Invalid or expired invite code")
        
        invite = self._invites[setup_request.invite_code]
        
        # Register user
        registration = RegistrationRequest(
            name=setup_request.name,
            email=setup_request.email,
            password=setup_request.password
        )
        
        auth_response = auth_manager.register_user(registration)
        if not auth_response.success:
            raise ValueError(f"Registration failed: {auth_response.message}")
        
        user_id = auth_response.user["user_id"]
        
        # Update user with ADHD-specific settings
        user = auth_manager.get_user(user_id)
        if user:
            # Set up energy patterns
            if setup_request.energy_patterns:
                user.energy_patterns = setup_request.energy_patterns
            else:
                # Use ADHD-friendly defaults
                user.energy_patterns = {
                    "peak_hours": [9, 10, 11, 14, 15, 16],
                    "low_hours": [12, 13, 17, 18, 19],
                    "hyperfocus_risk_hours": [20, 21, 22, 23, 0, 1]
                }
            
            # Set up nudge methods
            if setup_request.preferred_nudge_methods:
                user.preferred_nudge_methods = setup_request.preferred_nudge_methods
            else:
                user.preferred_nudge_methods = ["web", "telegram"] if setup_request.telegram_chat_id else ["web"]
            
            # Set Telegram chat ID if provided
            if setup_request.telegram_chat_id:
                user.telegram_chat_id = setup_request.telegram_chat_id
            
            # Set ADHD-optimized defaults
            user.hyperfocus_indicators = [
                "long_sessions",
                "late_night_activity",
                "missed_breaks",
                "repetitive_tasks"
            ]
            
            user.nudge_timing_preferences = {
                "morning_check_in": "09:00",
                "afternoon_refocus": "14:00", 
                "evening_wind_down": "18:00",
                "break_reminders": True,
                "hyperfocus_alerts": True
            }
        
        # Mark invite as used
        invite.used_at = datetime.utcnow()
        invite.user_id = user_id
        invite.telegram_chat_id = setup_request.telegram_chat_id
        
        # Auto-complete onboarding with user preferences
        await self._auto_complete_onboarding(user_id, setup_request)
        
        invite.onboarding_completed = True
        
        # Generate API key for immediate use
        key_id, api_key = auth_manager.generate_api_key(user_id, "Beta Tester Key")
        
        logger.info(
            "Beta user setup completed",
            user_id=user_id,
            invite_code=setup_request.invite_code,
            email=setup_request.email
        )
        
        return {
            "success": True,
            "message": f"Welcome to MCP ADHD Server, {setup_request.name}! 🧠⚡",
            "user": {
                "user_id": user_id,
                "name": setup_request.name,
                "email": setup_request.email
            },
            "api_key": api_key,
            "setup_complete": True,
            "next_steps": [
                "Your account is ready to use!",
                "Start chatting at the main interface",
                "Check Telegram for nudge notifications" if setup_request.telegram_chat_id else None,
                "Explore your personalized ADHD support features"
            ]
        }
    
    async def _auto_complete_onboarding(self, user_id: str, setup_request: QuickSetupRequest):
        """Auto-complete onboarding based on setup preferences."""
        try:
            # Start onboarding
            await onboarding_manager.start_onboarding(user_id)
            
            # Simulate step completions based on provided data
            
            # Step 1: Welcome (auto-advance)
            await onboarding_manager.process_step(user_id, {"action": "continue"})
            
            # Step 2: ADHD Patterns
            adhd_patterns = {
                "primary_challenges": ["focus", "time_management", "task_completion"],
                "energy_pattern": setup_request.energy_patterns or "variable",
                "hyperfocus_frequency": "sometimes"
            }
            await onboarding_manager.process_step(user_id, adhd_patterns)
            
            # Step 3: Nudge Preferences  
            nudge_prefs = {
                "preferred_methods": setup_request.preferred_nudge_methods or ["web"],
                "nudge_style": "gentle",
                "timing_preferences": "adaptive"
            }
            await onboarding_manager.process_step(user_id, nudge_prefs)
            
            # Step 4: Goals (use defaults)
            goals = {
                "primary_goals": ["stay_focused", "complete_tasks", "manage_time"],
                "success_metrics": ["task_completion", "focus_time"]
            }
            await onboarding_manager.process_step(user_id, goals)
            
            # Complete onboarding
            await onboarding_manager.process_step(user_id, {"action": "complete"})
            
        except Exception as e:
            logger.warning("Auto-onboarding failed, user can complete manually", 
                         user_id=user_id, error=str(e))
    
    def create_batch_invites(self, count: int, prefix: str = "BATCH") -> List[BetaInvite]:
        """Create multiple invites for batch distribution."""
        invites = []
        
        for i in range(count):
            invite_code = f"ADHD-{prefix}-{secrets.token_urlsafe(6).upper()}"
            
            invite = BetaInvite(
                invite_code=invite_code,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=30)  # Longer expiry for batch
            )
            
            self._invites[invite_code] = invite
            invites.append(invite)
        
        logger.info("Batch invites created", count=count, prefix=prefix)
        return invites
    
    def get_invite_stats(self) -> Dict[str, Any]:
        """Get statistics about beta invites."""
        total = len(self._invites)
        used = sum(1 for inv in self._invites.values() if inv.used_at)
        expired = sum(1 for inv in self._invites.values() 
                     if datetime.utcnow() > inv.expires_at and not inv.used_at)
        active = total - used - expired
        onboarded = sum(1 for inv in self._invites.values() if inv.onboarding_completed)
        
        return {
            "total_invites": total,
            "used_invites": used,
            "expired_invites": expired,
            "active_invites": active,
            "completed_onboarding": onboarded,
            "conversion_rate": (onboarded / used * 100) if used > 0 else 0
        }


# Global beta onboarding manager
beta_onboarding = BetaOnboardingManager()