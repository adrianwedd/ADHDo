#!/usr/bin/env python3
"""
MCP ADHD Server - Automated Telegram Bot Setup

This script helps users set up their Telegram bot automatically with guided prompts.
"""

import os
import sys
import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

class TelegramBotSetup:
    """Automated Telegram bot configuration."""
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir
        self.env_file = project_dir / ".env"
        
    def print_step(self, step: int, total: int, message: str):
        """Print a formatted step message."""
        print(f"\n🔧 Step {step}/{total}: {message}")
        
    def print_success(self, message: str):
        """Print a success message."""
        print(f"✅ {message}")
        
    def print_error(self, message: str):
        """Print an error message."""
        print(f"❌ {message}")
        
    def print_info(self, message: str):
        """Print an info message."""
        print(f"ℹ️  {message}")
    
    async def validate_bot_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a Telegram bot token and return bot info."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{token}/getMe"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("ok"):
                            return data["result"]
                    return None
        except Exception as e:
            print(f"Error validating token: {e}")
            return None
    
    def get_chat_id_instructions(self, bot_username: str) -> str:
        """Generate instructions for getting chat ID."""
        return f"""
📱 To get your Telegram Chat ID:

1. Open Telegram and search for: @{bot_username}
2. Start a conversation with your bot by clicking "Start" or sending /start
3. Then search for: @userinfobot
4. Send any message to @userinfobot
5. It will reply with your user info including your Chat ID
6. Copy the "Id" number (it looks like: 123456789)

📝 Example Chat ID: 123456789 (just the numbers, no quotes)
"""
    
    def update_env_file(self, bot_token: str, chat_id: str):
        """Update the .env file with bot credentials."""
        if not self.env_file.exists():
            self.print_error(f".env file not found at {self.env_file}")
            return False
        
        # Read existing content
        with open(self.env_file, 'r') as f:
            content = f.read()
        
        # Update bot token
        if "TELEGRAM_BOT_TOKEN=" in content:
            content = content.replace(
                "TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here",
                f"TELEGRAM_BOT_TOKEN={bot_token}"
            )
            if "your_telegram_bot_token_here" not in content:
                # Token already set, replace it
                import re
                content = re.sub(
                    r'TELEGRAM_BOT_TOKEN=.*',
                    f'TELEGRAM_BOT_TOKEN={bot_token}',
                    content
                )
        else:
            content += f"\nTELEGRAM_BOT_TOKEN={bot_token}\n"
        
        # Update chat ID
        if "TELEGRAM_CHAT_ID=" in content:
            content = content.replace(
                "TELEGRAM_CHAT_ID=your_telegram_chat_id_here",
                f"TELEGRAM_CHAT_ID={chat_id}"
            )
            if "your_telegram_chat_id_here" not in content:
                # Chat ID already set, replace it
                import re
                content = re.sub(
                    r'TELEGRAM_CHAT_ID=.*',
                    f'TELEGRAM_CHAT_ID={chat_id}',
                    content
                )
        else:
            content += f"TELEGRAM_CHAT_ID={chat_id}\n"
        
        # Write updated content
        with open(self.env_file, 'w') as f:
            f.write(content)
        
        return True
    
    async def test_bot_setup(self, bot_token: str, chat_id: str) -> bool:
        """Test the bot setup by sending a welcome message."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": "🧠⚡ MCP ADHD Server connected!\n\nYour nudge bot is now ready to help keep you focused and productive! 🎯\n\nYou'll receive gentle nudges, task reminders, and hyperfocus alerts here.",
                    "parse_mode": "Markdown"
                }
                
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("ok", False)
                    else:
                        error_text = await response.text()
                        self.print_error(f"Failed to send test message: {error_text}")
                        return False
                        
        except Exception as e:
            self.print_error(f"Error testing bot: {e}")
            return False
    
    async def setup_interactive(self):
        """Interactive setup process."""
        print("🧠⚡ MCP ADHD Server - Telegram Bot Setup")
        print("=" * 50)
        
        self.print_step(1, 4, "Creating your Telegram bot")
        print("""
📱 Let's create your personal nudge bot!

1. Open Telegram and search for: @BotFather
2. Start a chat and send: /newbot
3. Follow the prompts to create your bot:
   - Choose a name (e.g., "My ADHD Assistant")
   - Choose a username (e.g., "my_adhd_assistant_bot")
4. BotFather will give you a token that looks like: 123456789:ABCdefGhIjKlMnOpQrStUvWxYz

⚠️  Keep this token private! It's like a password for your bot.
        """)
        
        # Get bot token
        while True:
            bot_token = input("\n🔑 Paste your bot token here: ").strip()
            if not bot_token:
                print("Please enter a valid bot token.")
                continue
            
            self.print_info("Validating bot token...")
            bot_info = await self.validate_bot_token(bot_token)
            
            if bot_info:
                bot_username = bot_info.get("username", "your_bot")
                bot_name = bot_info.get("first_name", "Your Bot")
                self.print_success(f"Bot validated: {bot_name} (@{bot_username})")
                break
            else:
                self.print_error("Invalid bot token. Please check and try again.")
        
        self.print_step(2, 4, "Getting your Chat ID")
        print(self.get_chat_id_instructions(bot_username))
        
        # Get chat ID
        while True:
            chat_id = input("\n💬 Enter your Chat ID: ").strip()
            if not chat_id:
                print("Please enter a valid chat ID.")
                continue
            
            # Validate chat ID format (should be a number)
            try:
                int(chat_id)
                break
            except ValueError:
                self.print_error("Chat ID should be a number. Please check and try again.")
        
        self.print_step(3, 4, "Updating configuration")
        if self.update_env_file(bot_token, chat_id):
            self.print_success("Configuration updated successfully!")
        else:
            self.print_error("Failed to update configuration.")
            return False
        
        self.print_step(4, 4, "Testing your bot")
        self.print_info("Sending a test message to your Telegram...")
        
        if await self.test_bot_setup(bot_token, chat_id):
            self.print_success("Test message sent! Check your Telegram.")
        else:
            self.print_error("Failed to send test message. Check your Chat ID.")
            return False
        
        print("\n" + "=" * 50)
        print("🎉 Telegram bot setup complete!")
        print("""
✅ Your MCP ADHD Server is now connected to Telegram!

Next steps:
1. Start your server: ./start_personal_server.sh
2. Create your account at: http://localhost:8000
3. Start chatting and watch for nudges in Telegram!

Your bot will send you:
• Gentle task reminders 🔔
• Hyperfocus break alerts ⏰
• Motivational nudges 🚀
• Crisis support when needed 🆘
        """)
        
        return True
    
    async def setup_automatic(self, bot_token: str, chat_id: str):
        """Automatic setup for scripted deployment."""
        # Validate token
        bot_info = await self.validate_bot_token(bot_token)
        if not bot_info:
            raise ValueError("Invalid bot token")
        
        # Update env file
        if not self.update_env_file(bot_token, chat_id):
            raise ValueError("Failed to update .env file")
        
        # Test setup
        if not await self.test_bot_setup(bot_token, chat_id):
            raise ValueError("Bot test failed")
        
        return True

async def main():
    """Main setup function."""
    # Get project directory
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    
    setup = TelegramBotSetup(project_dir)
    
    # Check for command line arguments for automated setup
    if len(sys.argv) == 3:
        # Automated setup
        bot_token = sys.argv[1]
        chat_id = sys.argv[2]
        
        try:
            await setup.setup_automatic(bot_token, chat_id)
            print("✅ Telegram bot configured automatically!")
        except Exception as e:
            print(f"❌ Automated setup failed: {e}")
            sys.exit(1)
    else:
        # Interactive setup
        try:
            await setup.setup_interactive()
        except KeyboardInterrupt:
            print("\n\n👋 Setup cancelled. Run this script again when you're ready!")
        except Exception as e:
            print(f"\n❌ Setup failed: {e}")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())