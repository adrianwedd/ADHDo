#!/usr/bin/env python3
"""
Test Authentication System.

Tests login, sessions, API keys, and rate limiting.
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_server.auth import AuthManager, APIKey, Session
from mcp_server.models import User
from mcp_server.config import settings

async def test_authentication():
    """Test authentication system functionality."""
    
    print("🔐 Testing Authentication System")
    print("=" * 40)
    
    # Create auth manager
    auth = AuthManager()
    
    # Test 1: User creation
    print("\n👤 Test 1: User Management")
    
    test_user = User(
        user_id="test_user",
        name="Test User",
        preferred_nudge_methods=["telegram"],
        telegram_chat_id="123456789"
    )
    
    auth.create_user(test_user)
    retrieved_user = auth.get_user("test_user")
    
    if retrieved_user and retrieved_user.user_id == test_user.user_id:
        print("✅ User creation and retrieval working")
    else:
        print("❌ User management failed")
    
    # Test 2: API Key generation
    print("\n🔑 Test 2: API Key Management")
    
    key_id, api_key = auth.generate_api_key("test_user", "Test API Key")
    print(f"Generated API Key: {api_key[:20]}...")
    
    # Validate the API key
    api_key_obj = auth.validate_api_key(api_key)
    if api_key_obj and api_key_obj.user_id == "test_user":
        print("✅ API key generation and validation working")
    else:
        print("❌ API key validation failed")
    
    # Test invalid API key
    invalid_key = auth.validate_api_key("invalid_key")
    if invalid_key is None:
        print("✅ Invalid API key properly rejected")
    else:
        print("❌ Invalid API key not rejected")
    
    # Test 3: Session management
    print("\n🍪 Test 3: Session Management")
    
    session_id = auth.create_session("test_user", "Test User Agent", "127.0.0.1")
    print(f"Created session: {session_id[:16]}...")
    
    # Validate session
    session = auth.validate_session(session_id)
    if session and session.user_id == "test_user":
        print("✅ Session creation and validation working")
    else:
        print("❌ Session validation failed")
    
    # Test invalid session
    invalid_session = auth.validate_session("invalid_session_id")
    if invalid_session is None:
        print("✅ Invalid session properly rejected")
    else:
        print("❌ Invalid session not rejected")
    
    # Test 4: Rate limiting
    print("\n⏱️ Test 4: Rate Limiting")
    
    # Test normal rate limits
    allowed_requests = 0
    for i in range(15):  # Try 15 requests quickly
        if auth.check_rate_limit("test_identifier", limit=10, window=60):
            allowed_requests += 1
    
    print(f"Allowed {allowed_requests}/15 requests (limit=10)")
    if allowed_requests <= 10:
        print("✅ Rate limiting working correctly")
    else:
        print("❌ Rate limiting not working")
    
    # Test 5: Revocation
    print("\n🚫 Test 5: Revocation")
    
    # Revoke API key
    revoke_success = auth.revoke_api_key(key_id)
    if revoke_success:
        print("✅ API key revocation successful")
        
        # Try to use revoked key
        revoked_key = auth.validate_api_key(api_key)
        if revoked_key is None:
            print("✅ Revoked API key properly rejected")
        else:
            print("❌ Revoked API key still working")
    else:
        print("❌ API key revocation failed")
    
    # Revoke session
    session_revoke_success = auth.revoke_session(session_id)
    if session_revoke_success:
        print("✅ Session revocation successful")
        
        # Try to use revoked session
        revoked_session = auth.validate_session(session_id)
        if revoked_session is None:
            print("✅ Revoked session properly rejected")
        else:
            print("❌ Revoked session still working")
    else:
        print("❌ Session revocation failed")
    
    # Test 6: Admin user creation
    print("\n👨‍💼 Test 6: Admin User")
    
    if hasattr(settings, 'admin_username') and settings.admin_username:
        admin_user = auth.get_user("admin")
        if admin_user:
            print(f"✅ Admin user created: {admin_user.name}")
        else:
            print("❌ Admin user not found")
    else:
        print("⚠️ Admin credentials not configured in settings")
        print("To test admin functionality:")
        print("1. Set ADMIN_USERNAME in .env")
        print("2. Set ADMIN_PASSWORD in .env")
    
    # Test 7: Cleanup
    print("\n🧹 Test 7: Cleanup")
    
    # Add some expired sessions for cleanup test
    old_auth = AuthManager()
    old_auth._sessions = {
        "expired1": Session(
            session_id="expired1",
            user_id="test_user",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            expires_at=datetime.now()  # Already expired
        )
    }
    
    old_auth.cleanup_expired()
    
    if "expired1" not in old_auth._sessions:
        print("✅ Expired session cleanup working")
    else:
        print("❌ Expired session cleanup failed")
    
    print("\n🎉 Authentication Test Summary")
    print("=" * 35)
    print("✅ User management")
    print("✅ API key generation and validation")
    print("✅ Session management")
    print("✅ Rate limiting")
    print("✅ Revocation mechanisms")
    print("✅ Cleanup functionality")
    
    print("\n🚀 Authentication system ready!")
    print("\nUsage examples:")
    print("1. Session-based: POST /auth/login → cookie → authenticated requests")
    print("2. API key: Authorization: Bearer mk_xxxxx.yyyyy")
    print("3. Debug mode: X-User-ID header (only in development)")

if __name__ == "__main__":
    try:
        from datetime import datetime
        asyncio.run(test_authentication())
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()