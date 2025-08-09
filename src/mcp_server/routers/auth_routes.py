"""
Authentication routes - User registration, login, profile management.

Extracted from monolithic main.py to improve code organization and maintainability.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ..auth import (
    auth_manager, get_current_user, get_optional_user,
    RegistrationRequest, LoginRequest, PasswordResetRequest, 
    PasswordResetConfirm, UserProfile, AuthResponse
)
from ..models import User
from ..database import get_database_session
from ..repositories import UserRepository, APIKeyRepository
from ..health_monitor import health_monitor

auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class CreateAPIKeyRequest(BaseModel):
    name: str
    expires_in_days: int = 30


@auth_router.post("/register", response_model=AuthResponse, 
                  summary="Register a new user",
                  description="Creates a new user account with email verification")
async def register_user(registration: RegistrationRequest, request: Request) -> AuthResponse:
    """Register a new user with comprehensive validation and security measures."""
    try:
        # Check if user already exists
        user_repo = UserRepository()
        existing_user = await user_repo.get_by_email(registration.email)
        
        if existing_user:
            raise HTTPException(
                status_code=400, 
                detail="User with this email already exists"
            )
        
        # Create user through auth manager
        result = await auth_manager.register_user(registration, str(request.client.host))
        
        # Record health metric
        health_monitor.record_metric("user_registrations", 1)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        health_monitor.record_error("user_registration", str(e))
        raise HTTPException(status_code=500, detail="Registration failed")


@auth_router.post("/login", response_model=AuthResponse)  
async def login_user(login: LoginRequest, request: Request) -> AuthResponse:
    """Authenticate user and return JWT token with comprehensive security logging."""
    try:
        # Authenticate through auth manager
        result = await auth_manager.authenticate_user(
            login.email, 
            login.password, 
            str(request.client.host)
        )
        
        if not result.success:
            health_monitor.record_metric("failed_login_attempts", 1)
            raise HTTPException(status_code=401, detail=result.message)
        
        # Record successful login
        health_monitor.record_metric("successful_logins", 1)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        health_monitor.record_error("user_login", str(e))
        raise HTTPException(status_code=500, detail="Login failed")


@auth_router.post("/logout", response_model=AuthResponse)
async def logout_user(request: Request) -> AuthResponse:
    """Logout user and invalidate session with security cleanup."""
    try:
        # Extract token from headers
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="No valid token provided")
        
        token = auth_header.split(" ")[1]
        
        # Logout through auth manager
        result = await auth_manager.logout_user(token)
        
        health_monitor.record_metric("user_logouts", 1)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        health_monitor.record_error("user_logout", str(e))
        raise HTTPException(status_code=500, detail="Logout failed")


@auth_router.get("/me")
async def get_current_user_profile(current_user: User = Depends(get_current_user)) -> dict:
    """Get current user's profile information with privacy controls."""
    try:
        return {
            "id": current_user.id,
            "email": current_user.email,
            "username": getattr(current_user, 'username', None),
            "created_at": current_user.created_at,
            "last_active": getattr(current_user, 'last_active', None),
            "preferences": getattr(current_user, 'preferences', {}),
            "onboarding_completed": getattr(current_user, 'onboarding_completed', False)
        }
    except Exception as e:
        health_monitor.record_error("get_user_profile", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve profile")


@auth_router.put("/me", response_model=AuthResponse)
async def update_user_profile(
    profile_update: UserProfile, 
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session)
) -> AuthResponse:
    """Update user profile with validation and audit logging."""
    try:
        # Update through auth manager
        result = await auth_manager.update_user_profile(current_user.id, profile_update)
        
        if result.success:
            health_monitor.record_metric("profile_updates", 1)
        
        return result
        
    except Exception as e:
        health_monitor.record_error("update_user_profile", str(e))
        raise HTTPException(status_code=500, detail="Profile update failed")


@auth_router.post("/forgot-password", response_model=AuthResponse)
async def request_password_reset(
    reset_request: PasswordResetRequest,
    request: Request
) -> AuthResponse:
    """Initiate password reset process with security controls."""
    try:
        # Process through auth manager
        result = await auth_manager.request_password_reset(
            reset_request.email,
            str(request.client.host)
        )
        
        health_monitor.record_metric("password_reset_requests", 1)
        
        # Always return success for security (don't reveal if email exists)
        return AuthResponse(
            success=True,
            message="If the email exists, a reset link will be sent"
        )
        
    except Exception as e:
        health_monitor.record_error("password_reset_request", str(e))
        raise HTTPException(status_code=500, detail="Password reset request failed")


@auth_router.post("/reset-password", response_model=AuthResponse)
async def confirm_password_reset(
    reset_confirm: PasswordResetConfirm,
    request: Request
) -> AuthResponse:
    """Complete password reset with token validation."""
    try:
        # Process through auth manager
        result = await auth_manager.confirm_password_reset(
            reset_confirm.token,
            reset_confirm.new_password,
            str(request.client.host)
        )
        
        if result.success:
            health_monitor.record_metric("successful_password_resets", 1)
        else:
            health_monitor.record_metric("failed_password_resets", 1)
        
        return result
        
    except Exception as e:
        health_monitor.record_error("password_reset_confirm", str(e))
        raise HTTPException(status_code=500, detail="Password reset failed")


# Legacy auth endpoints (keeping for backward compatibility)
@auth_router.post("/login")
async def login(request: LoginRequest, response: JSONResponse):
    """Legacy login endpoint for backward compatibility."""
    try:
        result = await auth_manager.authenticate_user(request.email, request.password)
        
        if not result.success:
            raise HTTPException(status_code=401, detail=result.message)
        
        # Set HTTP-only cookie
        response.set_cookie(
            key="session_token",
            value=result.token,
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=86400  # 24 hours
        )
        
        return {"status": "success", "message": "Logged in successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        health_monitor.record_error("legacy_login", str(e))
        raise HTTPException(status_code=500, detail="Login failed")


@auth_router.post("/logout")
async def logout(response: JSONResponse, current_user: User = Depends(get_current_user)):
    """Legacy logout endpoint for backward compatibility."""
    try:
        # Clear cookie
        response.delete_cookie(key="session_token", httponly=True)
        return {"status": "success", "message": "Logged out successfully"}
        
    except Exception as e:
        health_monitor.record_error("legacy_logout", str(e))
        raise HTTPException(status_code=500, detail="Logout failed")


@auth_router.post("/api-keys")
async def create_api_key(
    key_request: CreateAPIKeyRequest,
    current_user: User = Depends(get_current_user)
):
    """Create API key for programmatic access."""
    try:
        api_key_repo = APIKeyRepository()
        api_key = await api_key_repo.create_api_key(
            user_id=current_user.id,
            name=key_request.name,
            expires_in_days=key_request.expires_in_days
        )
        
        health_monitor.record_metric("api_keys_created", 1)
        
        return {"key": api_key.key, "expires_at": api_key.expires_at}
        
    except Exception as e:
        health_monitor.record_error("create_api_key", str(e))
        raise HTTPException(status_code=500, detail="API key creation failed")


@auth_router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user)
):
    """Revoke an API key."""
    try:
        api_key_repo = APIKeyRepository()
        await api_key_repo.revoke_api_key(key_id, current_user.id)
        
        health_monitor.record_metric("api_keys_revoked", 1)
        
        return {"status": "success", "message": "API key revoked"}
        
    except Exception as e:
        health_monitor.record_error("revoke_api_key", str(e))
        raise HTTPException(status_code=500, detail="API key revocation failed")


@auth_router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information (legacy endpoint)."""
    try:
        return {
            "id": current_user.id,
            "email": current_user.email,
            "username": getattr(current_user, 'username', None),
            "created_at": current_user.created_at
        }
    except Exception as e:
        health_monitor.record_error("get_current_user_info", str(e))
        raise HTTPException(status_code=500, detail="Failed to get user info")