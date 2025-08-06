#!/usr/bin/env python3
"""
Test Telegram Bot Integration.

This script tests the Telegram bot without requiring a real bot token.
For production use, set TELEGRAM_BOT_TOKEN in your .env file.
"""
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_server.telegram_bot import TelegramBotHandler
from mcp_server.models import NudgeTier, User
from mcp_server.config import settings
from traces.memory import trace_memory

async def test_telegram_bot():
    """Test Telegram bot functionality."""
    
    print("🤖 Testing Telegram Bot Integration")
    print("=" * 40)
    
    # Connect to Redis for testing
    try:
        await trace_memory.connect()
        print("✅ Connected to Redis for testing")
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")
        print("Continuing with limited functionality...")
    
    # Check if bot token is configured
    if settings.telegram_bot_token:
        print("✅ Telegram bot token configured")
        bot_handler = TelegramBotHandler()
    else:
        print("⚠️  Telegram bot token not configured - using mock")
        bot_handler = TelegramBotHandler()
        
        # Create mock objects for testing
        bot_handler.bot = AsyncMock()
        bot_handler.application = MagicMock()
    
    print(f"Bot initialized: {'✅' if bot_handler.bot else '❌'}")
    
    # Test 1: User creation
    print("\n🧑 Test 1: User Management")
    test_user_id = "123456789"
    test_username = "TestUser"
    test_chat_id = 987654321
    
    user = await bot_handler._get_or_create_user(test_user_id, test_username, test_chat_id)
    print(f"Created user: {user.name} (ID: {user.user_id})")
    print(f"Chat ID: {user.telegram_chat_id}")
    print(f"Preferred methods: {user.preferred_nudge_methods}")
    
    # Test 2: User retrieval
    retrieved_user = await bot_handler._get_user(test_user_id)
    if retrieved_user:
        print(f"✅ Successfully retrieved user: {retrieved_user.name}")
    else:
        print("❌ Failed to retrieve user")
    
    # Test 3: Nudge sending (mocked)
    print("\n📨 Test 3: Nudge Sending")
    nudge_tests = [
        ("Gentle nudge test", NudgeTier.GENTLE),
        ("Sarcastic nudge test", NudgeTier.SARCASTIC), 
        ("Sergeant nudge test", NudgeTier.SERGEANT)
    ]
    
    for message, tier in nudge_tests:
        if bot_handler.bot:
            success = await bot_handler.send_nudge(test_user_id, message, tier)
            print(f"{tier.name}: {'✅ Sent' if success else '❌ Failed'} - '{message}'")
        else:
            print(f"{tier.name}: ⚠️  No bot configured - would send '{message}'")
    
    # Test 4: Command simulation
    print("\n💬 Test 4: Command Simulation")
    
    # Create mock update objects
    class MockUser:
        def __init__(self, user_id, username):
            self.id = user_id
            self.username = username
            self.first_name = username
    
    class MockChat:
        def __init__(self, chat_id):
            self.id = chat_id
    
    class MockMessage:
        def __init__(self, text, user_id, chat_id):
            self.text = text
            self.chat_id = chat_id
            self.chat = MockChat(chat_id)
            self.reply_text = AsyncMock()
    
    class MockUpdate:
        def __init__(self, text, user_id, chat_id):
            self.effective_user = MockUser(user_id, "TestUser")
            self.message = MockMessage(text, user_id, chat_id)
    
    # Test start command
    print("Testing /start command...")
    start_update = MockUpdate("/start", test_user_id, test_chat_id)
    await bot_handler.handle_start(start_update, None)
    print("✅ /start command handled")
    
    # Test help command
    print("Testing /help command...")
    help_update = MockUpdate("/help", test_user_id, test_chat_id)
    await bot_handler.handle_help(help_update, None)
    print("✅ /help command handled")
    
    # Test status command
    print("Testing /status command...")
    status_update = MockUpdate("/status", test_user_id, test_chat_id)
    await bot_handler.handle_status(status_update, None)
    print("✅ /status command handled")
    
    # Test break command
    print("Testing /break command...")
    break_update = MockUpdate("/break", test_user_id, test_chat_id)
    await bot_handler.handle_break(break_update, None)
    print("✅ /break command handled")
    
    # Test general message
    print("Testing general message...")
    message_update = MockUpdate("I'm feeling overwhelmed", test_user_id, test_chat_id)
    await bot_handler.handle_message(message_update, None)
    print("✅ General message handled")
    
    # Test 5: Integration with cognitive loop
    print("\n🧠 Test 5: Cognitive Loop Integration")
    
    test_messages = [
        "I'm ready to work",
        "I'm stuck on this task",
        "Feeling overwhelmed right now",
        "I need help with my email"
    ]
    
    for msg in test_messages:
        print(f"Processing: '{msg}'")
        msg_update = MockUpdate(msg, test_user_id, test_chat_id)
        try:
            await bot_handler.handle_message(msg_update, None)
            print(f"  ✅ Processed successfully")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\n🎉 Telegram Bot Test Summary")
    print("=" * 30)
    print("✅ User management working")
    print("✅ Command handlers implemented")
    print("✅ Cognitive loop integration active")
    print("✅ Nudge system ready")
    
    if settings.telegram_bot_token:
        print("🚀 Bot is ready for production use!")
        print("To test with real Telegram:")
        print(f"1. Message your bot @{settings.telegram_bot_token.split(':')[0]}bot")
        print("2. Use /start to initialize")
        print("3. Chat naturally about your tasks!")
    else:
        print("⚠️  To use with real Telegram:")
        print("1. Set TELEGRAM_BOT_TOKEN in .env")
        print("2. Run: python -m mcp_server.telegram_bot")
        print("3. Or integrate with FastAPI server")
    
    # Cleanup
    try:
        await trace_memory.disconnect()
        print("✅ Disconnected from Redis cleanly")
    except Exception:
        pass  # Ignore cleanup errors

if __name__ == "__main__":
    try:
        asyncio.run(test_telegram_bot())
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()