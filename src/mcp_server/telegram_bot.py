"""
Telegram Bot Handler for MCP ADHD Server.

Handles incoming Telegram messages and integrates with the cognitive loop.
"""
import asyncio
from typing import Dict, Any, Optional

import structlog
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.error import TelegramError

from mcp_server.config import settings
from mcp_server.cognitive_loop import cognitive_loop
from mcp_server.models import User, NudgeTier, TraceMemory
from mcp_server.auth import auth_manager
from traces.memory import trace_memory

logger = structlog.get_logger()


class TelegramBotHandler:
    """Handles Telegram bot interactions for ADHD support."""
    
    def __init__(self):
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        self._user_cache: Dict[str, User] = {}
        
        if settings.telegram_bot_token:
            self.setup_bot()
        else:
            logger.warning("Telegram bot token not configured")
    
    def setup_bot(self) -> None:
        """Initialize Telegram bot and handlers."""
        try:
            self.application = Application.builder().token(settings.telegram_bot_token).build()
            self.bot = self.application.bot
            
            # Command handlers
            self.application.add_handler(CommandHandler("start", self.handle_start))
            self.application.add_handler(CommandHandler("help", self.handle_help))
            self.application.add_handler(CommandHandler("status", self.handle_status))
            self.application.add_handler(CommandHandler("focus", self.handle_focus))
            self.application.add_handler(CommandHandler("break", self.handle_break))
            self.application.add_handler(CommandHandler("register", self.handle_register))
            self.application.add_handler(CommandHandler("login", self.handle_login))
            self.application.add_handler(CommandHandler("link", self.handle_link_account))
            
            # Message handler for general chat
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
            )
            
            logger.info("Telegram bot initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Telegram bot", error=str(e))
    
    async def handle_start(self, update: Update, context) -> None:
        """Handle /start command."""
        if not update.message or not update.effective_user:
            return
        
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or update.effective_user.first_name or "User"
        
        # Create or retrieve user
        user = await self._get_or_create_user(user_id, username, update.message.chat_id)
        
        welcome_message = (
            f"Hi {username}! 👋\n\n"
            "I'm your ADHD support assistant. I'm here to help you:\n"
            "• Stay focused on tasks 🎯\n"
            "• Break down overwhelming projects 📝\n" 
            "• Provide gentle accountability nudges 🌱\n"
            "• Celebrate your wins 🎉\n\n"
            "Just chat with me naturally about what you're working on!\n\n"
            "Commands:\n"
            "/help - Show this help\n"
            "/status - Check your current focus\n"
            "/focus <task> - Set current focus\n"
            "/break - Take a break"
        )
        
        await update.message.reply_text(welcome_message)
        
        # Store welcome interaction
        trace_record = TraceMemory(
            user_id=user_id,
            event_type="telegram_start",
            event_data={
                "username": username,
                "chat_id": update.message.chat_id
            },
            source="telegram_bot",
            confidence=1.0
        )
        await trace_memory.store_trace(trace_record)
    
    async def handle_help(self, update: Update, context) -> None:
        """Handle /help command."""
        help_text = (
            "🧠 **MCP ADHD Assistant Commands**\n\n"
            "💬 **General Chat**: Just message me about your tasks or how you're feeling\n\n"
            "📋 **Task Commands**:\n"
            "/status - See your current focus and energy level\n"
            "/focus <task> - Set what you're working on now\n"
            "/break - Log that you're taking a break (important!)\n\n"
            "🔐 **Account Commands**:\n"
            "/register <name> <email> <password> - Create new account\n"
            "/login <email> <password> - Link existing account\n"
            "/link - Get account linking help\n\n"
            "🎯 **Examples**:\n"
            "• \"I'm struggling to start this email\"\n"
            "• \"Feeling overwhelmed with my project\"\n"
            "• \"Ready to tackle my to-do list\"\n"
            "• \"/focus Write quarterly report\"\n\n"
            "I'll provide context-aware support based on your patterns and needs!"
        )
        
        if update.message:
            await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def handle_status(self, update: Update, context) -> None:
        """Handle /status command."""
        if not update.effective_user or not update.message:
            return
        
        user_id = str(update.effective_user.id)
        user = await self._get_user(user_id)
        
        if not user:
            await update.message.reply_text("Please use /start first to set up your account.")
            return
        
        # Get recent context from trace memory
        try:
            recent_traces = await trace_memory.get_recent_traces(user_id, limit=5)
            
            status_message = f"📊 **Status for {user.name}**\n\n"
            
            # Current focus (from most recent trace)
            current_focus = "Nothing set"
            if recent_traces:
                for trace in recent_traces:
                    if trace.get("event_data", {}).get("task_focus"):
                        current_focus = trace["event_data"]["task_focus"]
                        break
            
            status_message += f"🎯 **Current Focus**: {current_focus}\n"
            
            # Recent activity
            if recent_traces:
                status_message += f"\n📈 **Recent Activity** ({len(recent_traces)} interactions):\n"
                for trace in recent_traces[:3]:
                    event_type = trace.get("event_type", "unknown")
                    timestamp = trace.get("timestamp", "unknown")
                    if isinstance(timestamp, str):
                        # Parse timestamp and show relative time
                        status_message += f"• {event_type} - {timestamp[:16]}\n"
            else:
                status_message += "\n📈 **Recent Activity**: No recent activity found\n"
            
            status_message += "\n💡 Ready to help with your next task!"
            
        except Exception as e:
            logger.error("Error getting status", error=str(e))
            status_message = "📊 Status check temporarily unavailable. Try again in a moment!"
        
        await update.message.reply_text(status_message, parse_mode="Markdown")
    
    async def handle_focus(self, update: Update, context) -> None:
        """Handle /focus command."""
        if not update.effective_user or not update.message:
            return
        
        user_id = str(update.effective_user.id)
        user = await self._get_user(user_id)
        
        if not user:
            await update.message.reply_text("Please use /start first to set up your account.")
            return
        
        # Extract task from command
        if context.args:
            task_focus = " ".join(context.args)
        else:
            await update.message.reply_text(
                "Please specify what you want to focus on!\n"
                "Example: `/focus Write quarterly report`", 
                parse_mode="Markdown"
            )
            return
        
        # Process through cognitive loop
        focus_message = f"I want to focus on: {task_focus}"
        
        result = await cognitive_loop.process_user_input(
            user_id=user_id,
            user_input=focus_message,
            task_focus=task_focus,
            nudge_tier=NudgeTier.GENTLE
        )
        
        if result.success and result.response:
            response_text = f"🎯 **Focus Set**: {task_focus}\n\n{result.response.text}"
        else:
            response_text = f"🎯 **Focus Set**: {task_focus}\n\nI'm here to help you stay on track!"
        
        await update.message.reply_text(response_text, parse_mode="Markdown")
    
    async def handle_break(self, update: Update, context) -> None:
        """Handle /break command."""
        if not update.effective_user or not update.message:
            return
        
        user_id = str(update.effective_user.id)
        
        break_messages = [
            "🌿 Taking a break is important! Recharge and come back strong.",
            "☕ Good call on the break! Your brain needs rest to stay sharp.",
            "🧘 Break time! Remember: rest is productive too.",
            "🌱 Smart move! Taking breaks prevents burnout.",
            "⏰ Break logged! Your future focused self will thank you."
        ]
        
        import random
        response = random.choice(break_messages)
        
        # Log break in trace memory
        trace_record = TraceMemory(
            user_id=user_id,
            event_type="break_taken",
            event_data={
                "trigger": "telegram_command"
            },
            source="telegram_bot",
            confidence=1.0
        )
        await trace_memory.store_trace(trace_record)
        
        await update.message.reply_text(response)
    
    async def handle_message(self, update: Update, context) -> None:
        """Handle general messages through cognitive loop."""
        if not update.message or not update.effective_user:
            return
        
        user_id = str(update.effective_user.id)
        message_text = update.message.text
        
        # Get or create user
        username = update.effective_user.username or update.effective_user.first_name or "User"
        user = await self._get_or_create_user(user_id, username, update.message.chat_id)
        
        # Process through cognitive loop
        try:
            result = await cognitive_loop.process_user_input(
                user_id=user_id,
                user_input=message_text,
                nudge_tier=NudgeTier.GENTLE
            )
            
            if result.success and result.response:
                # Send response via Telegram
                response_text = result.response.text
                
                # Add some context about response source for transparency
                if result.response.source == "pattern_match":
                    response_text += "\n\n_✨ Ultra-fast response_"
                elif result.response.source == "local_cached":
                    response_text += "\n\n_💾 From my memory_"
                elif result.response.source == "hard_coded":
                    response_text += "\n\n_🚨 Safety response_"
                    
                await update.message.reply_text(response_text, parse_mode="Markdown")
                
            else:
                # Fallback response
                await update.message.reply_text(
                    "I'm here to help! Try telling me about what you're working on or how you're feeling."
                )
                
        except Exception as e:
            logger.error("Error processing Telegram message", error=str(e), user_id=user_id)
            await update.message.reply_text(
                "I had a brief moment of confusion 😅 Could you try that again?"
            )
    
    async def handle_register(self, update: Update, context) -> None:
        """Handle /register command for creating new account via Telegram."""
        if not update.effective_user or not update.message:
            return
        
        # Check if user already has context.args with name, email, password
        if not context.args or len(context.args) < 3:
            await update.message.reply_text(
                "To register via Telegram, use:\n"
                "`/register YourName your.email@example.com yourpassword123`\n\n"
                "⚠️ *Security Note*: Consider deleting this message after registration "
                "to protect your password!\n\n"
                "Or register safely via the web interface at the server URL.",
                parse_mode="Markdown"
            )
            return
        
        name = context.args[0]
        email = context.args[1]
        password = context.args[2]
        
        try:
            from mcp_server.auth import RegistrationRequest
            registration = RegistrationRequest(name=name, email=email, password=password)
            result = auth_manager.register_user(registration)
            
            if result.success:
                # Update user with Telegram chat ID
                user_data = auth_manager._user_data.get(result.user['user_id'])
                if user_data:
                    auth_user = auth_manager._users.get(result.user['user_id'])
                    if auth_user:
                        auth_user.telegram_chat_id = str(update.message.chat_id)
                        auth_user.preferred_nudge_methods.append("telegram")
                
                await update.message.reply_text(
                    f"🎉 Welcome to MCP ADHD Server, {name}!\n\n"
                    "Your account has been created and linked to this Telegram chat.\n"
                    "You can now:\n"
                    "• Chat with me here for ADHD support\n"
                    "• Use the web interface with your email/password\n"
                    "• Get nudges and reminders via Telegram\n\n"
                    "⚠️ *Please delete your registration message above for security!*"
                )
            else:
                await update.message.reply_text(f"❌ Registration failed: {result.message}")
                
        except ValueError as e:
            await update.message.reply_text(f"❌ Registration error: {str(e)}")
        except Exception as e:
            logger.error("Telegram registration error", error=str(e))
            await update.message.reply_text("🔄 Something went wrong with registration. Let's try again or you can use our web interface for easier setup.")

    async def handle_login(self, update: Update, context) -> None:
        """Handle /login command for linking existing account."""
        if not update.effective_user or not update.message:
            return
        
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "To login via Telegram, use:\n"
                "`/login your.email@example.com yourpassword`\n\n"
                "⚠️ *Security Note*: Please delete this message after login "
                "to protect your password!\n\n"
                "Or login safely via the web interface.",
                parse_mode="Markdown"
            )
            return
        
        email = context.args[0]
        password = context.args[1]
        
        try:
            from mcp_server.auth import LoginRequest
            login_request = LoginRequest(email=email, password=password)
            result = auth_manager.login_user(login_request)
            
            if result.success:
                # Link Telegram to existing account
                user = auth_manager._users.get(result.user['user_id'])
                if user:
                    user.telegram_chat_id = str(update.message.chat_id)
                    if "telegram" not in user.preferred_nudge_methods:
                        user.preferred_nudge_methods.append("telegram")
                
                await update.message.reply_text(
                    f"✅ Welcome back, {result.user['name']}!\n\n"
                    "Your existing account is now linked to this Telegram chat.\n"
                    "You can continue using both the web interface and Telegram bot.\n\n"
                    "⚠️ *Please delete your login message above for security!*"
                )
            else:
                await update.message.reply_text(f"❌ Login failed: {result.message}")
                
        except Exception as e:
            logger.error("Telegram login error", error=str(e))
            await update.message.reply_text("❌ Login failed. Please check your credentials and try again.")

    async def handle_link_account(self, update: Update, context) -> None:
        """Handle /link command to get linking instructions."""
        await update.message.reply_text(
            "🔗 **Link Your Account**\n\n"
            "To connect your existing web account to Telegram:\n\n"
            "1️⃣ If you have an account: `/login your.email@domain.com yourpassword`\n"
            "2️⃣ If you need an account: `/register YourName your.email@domain.com yourpassword`\n\n"
            "⚠️ **Security Tips**:\n"
            "• Delete your login/register message after use\n"
            "• Consider using the secure web interface instead\n"
            "• Only do this in a private chat with me\n\n"
            "💡 **Alternative**: Use the web interface to manage your account securely!",
            parse_mode="Markdown"
        )
    
    async def _get_or_create_user(self, user_id: str, username: str, chat_id: int) -> User:
        """Get existing user or create new one."""
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        
        # TODO: Check database for existing user
        # For now, create in-memory user
        user = User(
            user_id=user_id,
            name=username,
            telegram_chat_id=str(chat_id),
            preferred_nudge_methods=["telegram"],
            preferences={
                "nudge_frequency": "normal",
                "response_style": "encouraging"
            }
        )
        
        self._user_cache[user_id] = user
        
        logger.info("Created new Telegram user", user_id=user_id, username=username)
        return user
    
    async def _get_user(self, user_id: str) -> Optional[User]:
        """Get existing user."""
        return self._user_cache.get(user_id)
    
    async def send_nudge(self, user_id: str, message: str, tier: NudgeTier = NudgeTier.GENTLE) -> bool:
        """Send a nudge message to user via Telegram."""
        if not self.bot:
            return False
        
        user = await self._get_user(user_id)
        if not user or not user.telegram_chat_id:
            return False
        
        try:
            # Format message based on tier
            if tier == NudgeTier.GENTLE:
                formatted_message = f"🌱 {message}"
            elif tier == NudgeTier.SARCASTIC:
                formatted_message = f"🙄 {message}"
            else:  # SERGEANT
                formatted_message = f"⚡ {message.upper()}"
            
            await self.bot.send_message(
                chat_id=int(user.telegram_chat_id),
                text=formatted_message,
                parse_mode="Markdown"
            )
            
            logger.info("Sent Telegram nudge", user_id=user_id, tier=tier.name)
            return True
            
        except TelegramError as e:
            logger.error("Failed to send Telegram nudge", user_id=user_id, error=str(e))
            return False
    
    async def start_polling(self) -> None:
        """Start polling for Telegram updates."""
        if not self.application:
            logger.error("Telegram application not initialized")
            return
        
        try:
            logger.info("Starting Telegram bot polling...")
            await self.application.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error("Telegram polling error", error=str(e))
    
    async def stop(self) -> None:
        """Stop the Telegram bot."""
        if self.application:
            await self.application.stop()
            logger.info("Telegram bot stopped")


# Global Telegram bot instance
telegram_bot = TelegramBotHandler()