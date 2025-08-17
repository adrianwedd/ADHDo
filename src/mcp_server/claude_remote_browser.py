"""
Claude Remote Browser Client - Connects to existing browser session
Uses Chrome DevTools Protocol to connect to your running browser
"""

import asyncio
import json
import logging
import subprocess
import requests
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright
import time
import os

logger = logging.getLogger(__name__)


class ClaudeRemoteBrowserClient:
    """Connect to existing Chrome browser for Claude access."""
    
    def __init__(self, conversation_id: str = None):
        self.browser = None
        self.context = None  
        self.page = None
        self.playwright = None
        self.remote_debugging_port = 9222
        self.conversation_id = conversation_id or "c31fc8ae-e3c9-49be-ba36-d5a954a846f4"  # Default persistent conversation
        self.conversation_url = f"https://claude.ai/chat/{self.conversation_id}"
        
    async def connect_to_existing_browser(self) -> bool:
        """Connect to existing Chrome browser via remote debugging."""
        try:
            # Check if Chrome is running with remote debugging
            debug_url = f"http://localhost:{self.remote_debugging_port}/json"
            
            try:
                response = requests.get(debug_url, timeout=5)
                tabs = response.json()
                logger.info(f"Found {len(tabs)} browser tabs")
            except:
                # Chrome not running with remote debugging, try to enable it
                logger.info("Enabling remote debugging on existing Chrome...")
                if not await self._enable_remote_debugging():
                    return False
                    
                # Try again after enabling
                response = requests.get(debug_url, timeout=5) 
                tabs = response.json()
            
            # Connect via Playwright
            self.playwright = await async_playwright().start()
            
            # Connect to existing browser
            self.browser = await self.playwright.chromium.connect_over_cdp(
                f"http://localhost:{self.remote_debugging_port}"
            )
            
            # Look for existing Claude conversation tab
            claude_context = None
            target_found = False
            
            for context in self.browser.contexts:
                for page in context.pages:
                    if self.conversation_id in page.url:
                        self.page = page
                        self.context = context
                        claude_context = context
                        target_found = True
                        logger.info(f"✅ Connected to existing conversation: {self.conversation_id}")
                        break
                    elif "claude.ai" in page.url:
                        # Found a Claude tab but not our specific conversation
                        self.page = page
                        self.context = context
                        claude_context = context
                        logger.info("✅ Found Claude tab, will navigate to specific conversation")
                        break
                if claude_context:
                    break
            
            # If no Claude tab found, create one
            if not claude_context:
                self.context = self.browser.contexts[0] if self.browser.contexts else None
                if not self.context:
                    logger.error("No browser contexts available")
                    return False
                self.page = await self.context.new_page()
                logger.info("✅ Created new Claude tab")
            
            # Navigate to specific conversation if not already there
            if not target_found:
                await self.page.goto(self.conversation_url)
                logger.info(f"✅ Navigated to conversation: {self.conversation_id}")
            
            # Verify Claude access
            try:
                await self.page.wait_for_selector(
                    '[data-testid="chat-input"], textarea[placeholder*="message"]', 
                    timeout=10000
                )
                logger.info("✅ Claude interface ready")
                return True
            except:
                if "login" in self.page.url:
                    logger.warning("⚠️ Claude session expired - needs manual login")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to existing browser: {e}")
            return False
    
    async def _enable_remote_debugging(self) -> bool:
        """Enable remote debugging on existing Chrome process."""
        try:
            # Find Chrome process
            chrome_processes = []
            try:
                result = subprocess.run(['pgrep', '-f', 'chrome|chromium'], 
                                      capture_output=True, text=True)
                if result.stdout:
                    chrome_processes = result.stdout.strip().split('\n')
            except:
                pass
                
            if not chrome_processes:
                logger.error("No Chrome processes found")
                return False
                
            # Try to start Chrome with remote debugging
            # Note: This requires restarting Chrome, which may not be ideal
            logger.info("Chrome is running but remote debugging not enabled")
            logger.info("Please restart Chrome with: chrome --remote-debugging-port=9222")
            return False
            
        except Exception as e:
            logger.error(f"Failed to enable remote debugging: {e}")
            return False
    
    async def extract_session_cookies(self) -> Dict[str, str]:
        """Extract current Claude session cookies."""
        try:
            if not self.page:
                return {}
                
            cookies = await self.context.cookies("https://claude.ai")
            session_data = {}
            
            for cookie in cookies:
                if cookie['name'] in ['sessionKey', 'claude_session']:
                    session_data[cookie['name']] = cookie['value']
                    
            logger.info(f"✅ Extracted {len(session_data)} session cookies")
            return session_data
            
        except Exception as e:
            logger.error(f"Cookie extraction failed: {e}")
            return {}
    
    async def update_env_session(self) -> bool:
        """Update .env with fresh session token."""
        try:
            cookies = await self.extract_session_cookies()
            
            if 'sessionKey' not in cookies:
                logger.warning("No sessionKey found")
                return False
                
            # Update .env file
            env_path = "/home/pi/repos/ADHDo/.env"
            
            # Read current .env
            lines = []
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    lines = f.readlines()
            
            # Update sessionKey line
            updated = False
            for i, line in enumerate(lines):
                if line.startswith('CLAUDE_SESSION_KEY='):
                    lines[i] = f'CLAUDE_SESSION_KEY={cookies["sessionKey"]}\n'
                    updated = True
                    break
                    
            if not updated:
                lines.append(f'CLAUDE_SESSION_KEY={cookies["sessionKey"]}\n')
            
            # Write back
            with open(env_path, 'w') as f:
                f.writelines(lines)
                
            # Update current environment
            os.environ['CLAUDE_SESSION_KEY'] = cookies['sessionKey']
            
            logger.info("✅ Environment updated with fresh session")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update environment: {e}")
            return False
    
    async def send_message(self, message: str) -> str:
        """Send message to Claude via existing browser."""
        try:
            if not self.page:
                raise Exception("Not connected to browser")
                
            # Navigate to specific conversation if needed
            if self.conversation_id not in self.page.url:
                await self.page.goto(self.conversation_url)
                await self.page.wait_for_load_state('networkidle')
                logger.info(f"Navigated to conversation: {self.conversation_id}")
            
            # Find input field
            input_selectors = [
                '[data-testid="chat-input"]',
                'textarea[placeholder*="message"]',
                'div[contenteditable="true"]'
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    input_element = await self.page.wait_for_selector(selector, timeout=3000)
                    if input_element:
                        break
                except:
                    continue
                    
            if not input_element:
                raise Exception("Could not find Claude input field")
            
            # Clear and type message
            await input_element.click()
            await input_element.fill("")
            await input_element.type(message)
            
            # Send message (Enter key or send button)
            await input_element.press("Enter")
            
            # Wait for response
            await self.page.wait_for_timeout(3000)
            
            # Extract Claude's response
            response_text = await self._extract_latest_response()
            
            if response_text:
                logger.info("✅ Claude response received via browser")
                return response_text
            else:
                return "I didn't receive a clear response. Please try again."
                
        except Exception as e:
            logger.error(f"Send message failed: {e}")
            raise
    
    async def _extract_latest_response(self) -> str:
        """Extract the latest Claude response from the chat."""
        try:
            # Wait a bit more for response to fully load
            await self.page.wait_for_timeout(2000)
            
            # Try different selectors for Claude's responses
            response_selectors = [
                '[data-author="assistant"]',
                '[data-message-author="assistant"]', 
                '.font-claude',
                '.bg-bg-200'
            ]
            
            for selector in response_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        # Get the last response
                        last_element = elements[-1]
                        text = await last_element.inner_text()
                        if text.strip() and len(text.strip()) > 10:
                            return text.strip()
                except:
                    continue
                    
            # Fallback: get all text and try to extract response
            try:
                page_text = await self.page.inner_text('body')
                lines = page_text.split('\n')
                
                # Look for substantial text that looks like a response
                for line in reversed(lines[-20:]):
                    line = line.strip()
                    if (len(line) > 50 and 
                        not line.startswith('Message') and 
                        not line.startswith('Send') and
                        '?' in line or '.' in line):
                        return line
            except:
                pass
                
            return ""
            
        except Exception as e:
            logger.error(f"Response extraction failed: {e}")
            return ""
    
    async def close(self):
        """Clean up connection."""
        try:
            # Don't close the browser - it's the user's browser
            # Just disconnect Playwright
            if self.playwright:
                await self.playwright.stop()
        except:
            pass


class SmartSessionManager:
    """Intelligent session management with monitoring."""
    
    def __init__(self, conversation_id: str = None):
        self.client = None
        self.last_successful_request = time.time()
        self.session_check_interval = 1800  # 30 minutes
        self.conversation_id = conversation_id or "c31fc8ae-e3c9-49be-ba36-d5a954a846f4"
        
    async def ensure_claude_access(self) -> ClaudeRemoteBrowserClient:
        """Ensure we have working Claude access."""
        try:
            if not self.client:
                self.client = ClaudeRemoteBrowserClient(self.conversation_id)
                
            # Try to connect to existing browser
            if await self.client.connect_to_existing_browser():
                # Extract fresh session cookies
                await self.client.update_env_session()
                self.last_successful_request = time.time()
                return self.client
            else:
                logger.warning("Failed to connect to existing browser")
                return None
                
        except Exception as e:
            logger.error(f"Session management error: {e}")
            return None
    
    async def send_message_with_retry(self, message: str, max_retries: int = 2) -> str:
        """Send message with automatic retry and session refresh."""
        for attempt in range(max_retries):
            try:
                client = await self.ensure_claude_access()
                if client:
                    response = await client.send_message(message)
                    self.last_successful_request = time.time()
                    return response
                else:
                    logger.warning(f"No Claude client available (attempt {attempt + 1})")
                    
            except Exception as e:
                logger.error(f"Message attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # Brief pause before retry
                    
        return "I'm having trouble connecting to Claude. Please check your browser session."


# Test function
async def test_remote_browser():
    """Test the remote browser connection."""
    manager = SmartSessionManager()
    
    try:
        response = await manager.send_message_with_retry(
            "Hello! I'm testing the automated session management. Can you confirm you received this?"
        )
        print(f"Claude response: {response}")
        
    except Exception as e:
        print(f"Test failed: {e}")
        

if __name__ == "__main__":
    print("🌐 Testing remote browser connection...")
    print("Make sure Chrome is running and you're logged into Claude!")
    asyncio.run(test_remote_browser())