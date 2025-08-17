"""
Enhanced Claude Browser Client - Uses System Browser Profile
Automates session token extraction and renewal from your actual browser session
"""

import asyncio
import os
import json
import logging
import platform
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class ClaudeSystemBrowserClient:
    """Claude client using system browser profile for seamless authentication."""
    
    def __init__(self, headless: bool = True):
        """Initialize Claude system browser client."""
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.conversation_id: Optional[str] = None
        self.headless = headless
        self.timeout = 30000
        
        # Detect system browser profiles
        self.browser_profiles = self._detect_browser_profiles()
        
        logger.info(f"🌐 System browser profiles found: {len(self.browser_profiles)}")
    
    def _detect_browser_profiles(self) -> Dict[str, str]:
        """Detect system browser profile paths."""
        profiles = {}
        system = platform.system()
        home = Path.home()
        
        if system == "Linux":
            # Chrome/Chromium on Linux
            chrome_paths = [
                home / ".config" / "google-chrome",
                home / ".config" / "google-chrome-beta", 
                home / ".config" / "chromium",
                home / "snap" / "chromium" / "common" / "chromium"
            ]
            
            for path in chrome_paths:
                if (path / "Default").exists():
                    profiles["chrome"] = str(path)
                    break
                    
            # Firefox on Linux  
            firefox_path = home / ".mozilla" / "firefox"
            if firefox_path.exists():
                # Find default profile
                profiles_ini = firefox_path / "profiles.ini"
                if profiles_ini.exists():
                    with open(profiles_ini, 'r') as f:
                        content = f.read()
                        if "Default=1" in content:
                            for line in content.split('\n'):
                                if line.startswith('Path='):
                                    profile_name = line.split('=')[1].strip()
                                    profiles["firefox"] = str(firefox_path / profile_name)
                                    break
                                    
        elif system == "Darwin":  # macOS
            profiles["chrome"] = str(home / "Library" / "Application Support" / "Google" / "Chrome")
            profiles["firefox"] = str(home / "Library" / "Application Support" / "Firefox" / "Profiles")
            
        elif system == "Windows":
            profiles["chrome"] = str(home / "AppData" / "Local" / "Google" / "Chrome" / "User Data")
            profiles["firefox"] = str(home / "AppData" / "Roaming" / "Mozilla" / "Firefox" / "Profiles")
        
        # Filter to existing paths only
        return {k: v for k, v in profiles.items() if Path(v).exists()}
    
    async def connect_with_system_profile(self, browser_type: str = "chrome") -> bool:
        """Connect using system browser profile."""
        try:
            if browser_type not in self.browser_profiles:
                logger.warning(f"Browser profile not found: {browser_type}")
                return False
                
            profile_path = self.browser_profiles[browser_type]
            logger.info(f"🔗 Connecting to {browser_type} profile: {profile_path}")
            
            self.playwright = await async_playwright().start()
            
            if browser_type == "chrome":
                # Launch Chrome with existing profile
                self.browser = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=profile_path,
                    headless=self.headless,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor"
                    ]
                )
                self.page = self.browser.pages[0] if self.browser.pages else await self.browser.new_page()
                
            elif browser_type == "firefox":
                # Firefox profile handling
                self.browser = await self.playwright.firefox.launch_persistent_context(
                    user_data_dir=profile_path,
                    headless=self.headless
                )
                self.page = self.browser.pages[0] if self.browser.pages else await self.browser.new_page()
            
            # Test Claude access
            await self.page.goto("https://claude.ai/chats", timeout=self.timeout)
            
            # Check if we're logged in
            try:
                await self.page.wait_for_selector('[data-testid="chat-input"]', timeout=5000)
                logger.info("✅ Successfully connected to Claude with system profile")
                return True
            except:
                # Try to handle login redirect
                if "login" in self.page.url:
                    logger.warning("⚠️ Session expired, attempting auto-refresh")
                    return await self._attempt_session_refresh()
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect with system profile: {e}")
            return False
    
    async def _attempt_session_refresh(self) -> bool:
        """Attempt to refresh Claude session using system browser."""
        try:
            logger.info("🔄 Attempting automatic session refresh...")
            
            # If we're at login page, the profile should auto-login if session is valid
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Check if we got redirected to chats (successful auto-login)
            if "chats" in self.page.url:
                logger.info("✅ Session auto-refreshed successfully")
                return True
                
            # If still at login, check for "Continue" or auto-login elements
            try:
                continue_button = await self.page.wait_for_selector(
                    'button:has-text("Continue"), button:has-text("Sign in"), [data-testid="continue-button"]', 
                    timeout=5000
                )
                if continue_button:
                    await continue_button.click()
                    await self.page.wait_for_load_state('networkidle')
                    
                    if "chats" in self.page.url:
                        logger.info("✅ Session refreshed via continue button")
                        return True
            except:
                pass
                
            logger.warning("❌ Automatic session refresh failed - manual intervention needed")
            return False
            
        except Exception as e:
            logger.error(f"Session refresh error: {e}")
            return False
    
    async def extract_fresh_session_cookies(self) -> Dict[str, str]:
        """Extract current session cookies from system browser."""
        try:
            if not self.page:
                raise Exception("No browser page available")
                
            # Get all cookies from claude.ai
            cookies = await self.page.context.cookies("https://claude.ai")
            
            session_data = {}
            for cookie in cookies:
                if cookie['name'] in ['sessionKey', 'claude_session', '__cf_bm', 'cf_clearance']:
                    session_data[cookie['name']] = cookie['value']
            
            if 'sessionKey' in session_data:
                logger.info("✅ Fresh session cookies extracted")
                return session_data
            else:
                logger.warning("⚠️ No session cookies found")
                return {}
                
        except Exception as e:
            logger.error(f"Cookie extraction failed: {e}")
            return {}
    
    async def update_env_with_fresh_session(self) -> bool:
        """Update .env file with fresh session token."""
        try:
            cookies = await self.extract_fresh_session_cookies()
            
            if 'sessionKey' not in cookies:
                return False
                
            # Read current .env
            env_path = Path(__file__).parent.parent.parent / ".env"
            env_lines = []
            
            if env_path.exists():
                with open(env_path, 'r') as f:
                    env_lines = f.readlines()
            
            # Update or add CLAUDE_SESSION_KEY
            updated = False
            for i, line in enumerate(env_lines):
                if line.startswith('CLAUDE_SESSION_KEY='):
                    env_lines[i] = f'CLAUDE_SESSION_KEY={cookies["sessionKey"]}\n'
                    updated = True
                    break
            
            if not updated:
                env_lines.append(f'CLAUDE_SESSION_KEY={cookies["sessionKey"]}\n')
            
            # Write back to .env
            with open(env_path, 'w') as f:
                f.writelines(env_lines)
                
            # Update environment variable for current process
            os.environ['CLAUDE_SESSION_KEY'] = cookies['sessionKey']
            
            logger.info("✅ Environment updated with fresh session token")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update environment: {e}")
            return False
    
    async def send_message(self, message: str, conversation_id: str = None) -> str:
        """Send message to Claude using system browser."""
        try:
            if not self.page:
                raise Exception("Browser not connected")
                
            # Navigate to Claude if not already there
            if "claude.ai" not in self.page.url:
                await self.page.goto("https://claude.ai/chats")
                await self.page.wait_for_selector('[data-testid="chat-input"]', timeout=10000)
            
            # Find and click the input field
            input_selector = '[data-testid="chat-input"], textarea[placeholder*="message"], div[contenteditable="true"]'
            input_element = await self.page.wait_for_selector(input_selector, timeout=10000)
            
            # Clear and type message
            await input_element.click()
            await input_element.fill("")  # Clear existing content
            await input_element.type(message)
            
            # Find and click send button
            send_selectors = [
                '[data-testid="send-button"]',
                'button[aria-label*="Send"]',
                'button:has([data-icon="send"])',
                'button:has(svg)',  # Generic button with icon
            ]
            
            send_button = None
            for selector in send_selectors:
                try:
                    send_button = await self.page.wait_for_selector(selector, timeout=2000)
                    if send_button and await send_button.is_enabled():
                        break
                except:
                    continue
            
            if not send_button:
                # Try Enter key as fallback
                await input_element.press("Enter")
            else:
                await send_button.click()
            
            # Wait for response
            await self.page.wait_for_timeout(2000)  # Wait for message to send
            
            # Look for Claude's response
            response_selectors = [
                '[data-author="assistant"] div[data-testid="message-content"]',
                '.font-claude div:last-child',
                '[data-message-author="assistant"] p',
                '.bg-bg-200 p'  # Generic response styling
            ]
            
            for selector in response_selectors:
                try:
                    response_elements = await self.page.query_selector_all(selector)
                    if response_elements:
                        # Get the last response
                        last_response = response_elements[-1]
                        response_text = await last_response.inner_text()
                        if response_text.strip():
                            logger.info("✅ Claude response received")
                            return response_text.strip()
                except:
                    continue
            
            # Wait longer and try again
            await self.page.wait_for_timeout(5000)
            
            # Try to get any new text content
            try:
                # Look for the chat container and get latest messages
                chat_container = await self.page.query_selector('[data-testid="chat-messages"], .overflow-auto, .flex-1')
                if chat_container:
                    all_text = await chat_container.inner_text()
                    # Extract what looks like the last response
                    lines = all_text.split('\n')
                    for line in reversed(lines[-10:]):  # Check last 10 lines
                        if len(line.strip()) > 20 and not message in line:
                            logger.info("✅ Claude response extracted from chat")
                            return line.strip()
            except:
                pass
            
            logger.warning("⚠️ No response detected from Claude")
            return "I apologize, but I didn't receive a clear response. Could you try again?"
            
        except Exception as e:
            logger.error(f"Send message failed: {e}")
            raise Exception(f"Failed to send message to Claude: {e}")
    
    async def close(self):
        """Clean up browser resources."""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except:
            pass


class AutoSessionManager:
    """Manages automatic Claude session refresh."""
    
    def __init__(self, client: ClaudeSystemBrowserClient):
        self.client = client
        self.last_refresh = 0
        self.refresh_interval = 3600  # Check every hour
        
    async def ensure_valid_session(self) -> bool:
        """Ensure Claude session is valid, refresh if needed."""
        try:
            current_time = time.time()
            
            # Check if we need to refresh
            if current_time - self.last_refresh > self.refresh_interval:
                logger.info("🔄 Checking session validity...")
                
                # Try to connect with system profile
                if await self.client.connect_with_system_profile():
                    # Extract and update fresh cookies
                    if await self.client.update_env_with_fresh_session():
                        self.last_refresh = current_time
                        logger.info("✅ Session automatically refreshed")
                        return True
                    
            return True
            
        except Exception as e:
            logger.error(f"Session management error: {e}")
            return False
    
    async def start_background_refresh(self):
        """Start background task for automatic session refresh."""
        while True:
            try:
                await self.ensure_valid_session()
                await asyncio.sleep(self.refresh_interval)
            except Exception as e:
                logger.error(f"Background refresh error: {e}")
                await asyncio.sleep(300)  # Retry in 5 minutes


# Usage example and testing
async def test_system_browser_client():
    """Test the system browser client."""
    client = ClaudeSystemBrowserClient(headless=False)  # Visible for testing
    
    try:
        # Connect using system Chrome profile
        if await client.connect_with_system_profile("chrome"):
            print("✅ Connected to Claude via system browser")
            
            # Extract fresh session cookies
            await client.update_env_with_fresh_session()
            
            # Test sending a message
            response = await client.send_message("Hello! Can you help me focus on my tasks?")
            print(f"Claude response: {response}")
            
        else:
            print("❌ Failed to connect to Claude")
            
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_system_browser_client())