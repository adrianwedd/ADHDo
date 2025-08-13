"""
Claude integration using Playwright for browser automation.
Bypasses Cloudflare protection by using a real browser.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import os

logger = logging.getLogger(__name__)


class ClaudePlaywright:
    """Claude client using Playwright browser automation."""
    
    def __init__(self):
        """Initialize Claude Playwright client."""
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.authenticated = False
        self.conversation_id: Optional[str] = None
        
        # Get credentials from environment
        self.session_key = os.getenv('CLAUDE_SESSION_KEY', '')
        self.org_id = os.getenv('CLAUDE_ORG_ID', '1287541f-a020-4755-bbb0-8945a1be4fa5')
        self.user_id = os.getenv('CLAUDE_USER_ID', 'f71a8285-af11-4a58-ae8a-0020ecb210e8')
        
    async def initialize(self) -> bool:
        """Initialize browser and authenticate."""
        try:
            logger.info("Initializing Playwright browser...")
            
            # Start Playwright
            self.playwright = await async_playwright().start()
            
            # Launch browser (headless for server)
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # Set to False for debugging
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )
            
            # Create context with anti-detection measures
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='en-US'
            )
            
            # Add cookies if we have a session key
            if self.session_key:
                await self.context.add_cookies([
                    {
                        'name': 'sessionKey',
                        'value': self.session_key,
                        'domain': '.claude.ai',
                        'path': '/',
                        'httpOnly': True,
                        'secure': True,
                        'sameSite': 'Lax'
                    },
                    {
                        'name': 'lastActiveOrg',
                        'value': self.org_id,
                        'domain': '.claude.ai',
                        'path': '/'
                    },
                    {
                        'name': 'ajs_user_id',
                        'value': self.user_id,
                        'domain': '.claude.ai',
                        'path': '/'
                    }
                ])
            
            # Create page
            self.page = await self.context.new_page()
            
            # Navigate to Claude
            logger.info("Navigating to Claude...")
            await self.page.goto('https://claude.ai', wait_until='networkidle')
            
            # Wait for page to load
            await asyncio.sleep(3)
            
            # Check if we're authenticated
            try:
                # Look for chat interface elements
                await self.page.wait_for_selector('[data-testid="chat-input"]', timeout=5000)
                self.authenticated = True
                logger.info("✅ Authenticated with Claude successfully!")
                
                # Get or create conversation
                await self._ensure_conversation()
                return True
                
            except:
                # Check if we're on login page
                if 'login' in self.page.url or 'auth' in self.page.url:
                    logger.error("Not authenticated - session key may have expired")
                    self.authenticated = False
                    return False
                    
                # Might be on a different page, try to navigate to chat
                await self.page.goto('https://claude.ai/new', wait_until='networkidle')
                await asyncio.sleep(2)
                
                try:
                    await self.page.wait_for_selector('[data-testid="chat-input"]', timeout=5000)
                    self.authenticated = True
                    logger.info("✅ Authenticated after navigation!")
                    await self._ensure_conversation()
                    return True
                except:
                    logger.error("Failed to authenticate with Claude")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            return False
    
    async def _ensure_conversation(self):
        """Ensure we have an active conversation."""
        try:
            # Check current URL for conversation ID
            current_url = self.page.url
            if '/chat/' in current_url:
                self.conversation_id = current_url.split('/chat/')[-1].split('?')[0]
                logger.info(f"Using existing conversation: {self.conversation_id}")
            else:
                # Navigate to new chat
                await self.page.goto('https://claude.ai/new', wait_until='networkidle')
                await asyncio.sleep(2)
                
                # Get the new conversation ID from URL
                new_url = self.page.url
                if '/chat/' in new_url:
                    self.conversation_id = new_url.split('/chat/')[-1].split('?')[0]
                    logger.info(f"Created new conversation: {self.conversation_id}")
                    
        except Exception as e:
            logger.error(f"Failed to ensure conversation: {e}")
    
    async def send_message(self, message: str, timeout: int = 30) -> str:
        """Send a message to Claude and get response."""
        if not self.authenticated or not self.page:
            raise Exception("Not authenticated with Claude")
        
        try:
            # Find the chat input
            chat_input = await self.page.wait_for_selector(
                '[data-testid="chat-input"], [contenteditable="true"]',
                timeout=5000
            )
            
            # Clear and type message
            await chat_input.click()
            await chat_input.fill('')
            await chat_input.type(message)
            
            # Send message (Enter key or send button)
            await self.page.keyboard.press('Enter')
            
            # Wait for response to start
            await asyncio.sleep(2)
            
            # Wait for response to complete (look for stop button to disappear)
            try:
                await self.page.wait_for_selector(
                    '[aria-label*="Stop"], [data-testid="stop-button"]',
                    state='hidden',
                    timeout=timeout * 1000
                )
            except:
                # Fallback: just wait a bit
                await asyncio.sleep(5)
            
            # Get the last assistant message
            response_text = await self._get_last_response()
            
            return response_text
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise
    
    async def _get_last_response(self) -> str:
        """Extract the last assistant response from the page."""
        try:
            # Try multiple selectors for Claude's response
            selectors = [
                '[data-testid^="assistant-message"]',
                '.prose:last-of-type',
                '[class*="assistant"]:last-of-type',
                'div[class*="Message"]:last-of-type'
            ]
            
            for selector in selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        # Get the last element's text
                        last_element = elements[-1]
                        text = await last_element.inner_text()
                        if text and len(text) > 0:
                            return text.strip()
                except:
                    continue
            
            # Fallback: try to get any recent text
            all_text = await self.page.inner_text('body')
            lines = all_text.split('\n')
            
            # Find the last substantial block of text
            response_lines = []
            collecting = False
            
            for line in reversed(lines):
                line = line.strip()
                if line and len(line) > 10:  # Substantial text
                    if not collecting:
                        collecting = True
                    response_lines.insert(0, line)
                elif collecting and not line:
                    # End of response block
                    break
            
            if response_lines:
                return '\n'.join(response_lines)
            
            return "Unable to extract response"
            
        except Exception as e:
            logger.error(f"Failed to extract response: {e}")
            return f"Error extracting response: {e}"
    
    async def close(self):
        """Close browser and cleanup."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
                
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
            self.authenticated = False
            
            logger.info("Playwright browser closed")
            
        except Exception as e:
            logger.error(f"Error closing browser: {e}")


# Global instance (singleton pattern)
_claude_playwright: Optional[ClaudePlaywright] = None


async def get_claude_playwright() -> ClaudePlaywright:
    """Get or create the global Claude Playwright instance."""
    global _claude_playwright
    
    if _claude_playwright is None:
        _claude_playwright = ClaudePlaywright()
        success = await _claude_playwright.initialize()
        if not success:
            raise Exception("Failed to initialize Claude Playwright client")
    
    return _claude_playwright


async def test_claude_playwright():
    """Test the Playwright Claude integration."""
    try:
        client = await get_claude_playwright()
        
        # Test sending a message
        response = await client.send_message("Say hello in exactly 5 words")
        print(f"Claude response: {response}")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False
    finally:
        if _claude_playwright:
            await _claude_playwright.close()