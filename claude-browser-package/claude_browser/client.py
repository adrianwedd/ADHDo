"""
Claude Browser Client - Core implementation.

This module provides browser-based interaction with Claude.ai,
bypassing API limitations and Cloudflare protection.
"""

import asyncio
import os
import json
import logging
import platform
from typing import Optional, Dict, Any, List
from pathlib import Path

from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from .exceptions import (
    ClaudeAuthenticationError,
    ClaudeTimeoutError,
    ClaudeResponseError,
    ClaudeBrowserNotInitializedError
)

logger = logging.getLogger(__name__)


class ClaudeBrowserClient:
    """
    Claude.ai browser automation client.
    
    This client uses Playwright to interact with Claude through the web interface,
    bypassing API limitations and Cloudflare protection.
    
    Args:
        headless: Run browser in headless mode (default: True)
        timeout: Default timeout for operations in ms (default: 30000)
        chromium_path: Path to Chromium executable (auto-detected if None)
        cookies: Optional list of cookies to use for authentication
    """
    
    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,
        chromium_path: Optional[str] = None,
        cookies: Optional[List[Dict[str, Any]]] = None
    ):
        """Initialize Claude browser client."""
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.conversation_id: Optional[str] = None
        self.headless = headless
        self.timeout = timeout
        self.chromium_path = chromium_path or self._detect_chromium_path()
        self.cookies = cookies or self._load_cookies_from_env()
        self._initialized = False
        
        logger.info(f"🤖 Claude Browser Client initialized (headless={headless})")
    
    def _detect_chromium_path(self) -> Optional[str]:
        """Auto-detect Chromium path based on platform."""
        system = platform.system()
        
        if system == "Linux":
            # Check for Raspberry Pi
            if os.path.exists("/usr/bin/chromium-browser"):
                return "/usr/bin/chromium-browser"
            elif os.path.exists("/usr/bin/chromium"):
                return "/usr/bin/chromium"
        elif system == "Darwin":  # macOS
            chrome_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium"
            ]
            for path in chrome_paths:
                if os.path.exists(path):
                    return path
        elif system == "Windows":
            import winreg
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                   r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as key:
                    chrome_path = winreg.QueryValue(key, None)
                    if os.path.exists(chrome_path):
                        return chrome_path
            except:
                pass
        
        # Use Playwright's bundled Chromium as fallback
        return None
    
    def _load_cookies_from_env(self) -> List[Dict[str, Any]]:
        """Load cookies from environment variables."""
        cookies = []
        
        # Essential cookies
        session_key = os.getenv('CLAUDE_SESSION_KEY', '')
        org_id = os.getenv('CLAUDE_ORG_ID', '')
        user_id = os.getenv('CLAUDE_USER_ID', '')
        
        if session_key:
            cookies.append({
                'name': 'sessionKey',
                'value': session_key,
                'domain': '.claude.ai',
                'path': '/',
                'httpOnly': True,
                'secure': True,
                'sameSite': 'Lax'
            })
        
        if org_id:
            cookies.append({
                'name': 'lastActiveOrg',
                'value': org_id,
                'domain': '.claude.ai',
                'path': '/',
                'httpOnly': False,
                'secure': True,
                'sameSite': 'Lax'
            })
        
        if user_id:
            cookies.append({
                'name': 'ajs_user_id',
                'value': user_id,
                'domain': '.claude.ai',
                'path': '/',
                'httpOnly': False,
                'secure': False,
                'sameSite': 'Lax'
            })
        
        # Optional cookies
        cf_bm = os.getenv('CLAUDE_CF_BM', '')
        if cf_bm:
            cookies.append({
                'name': '__cf_bm',
                'value': cf_bm,
                'domain': '.claude.ai',
                'path': '/',
                'httpOnly': True,
                'secure': True,
                'sameSite': 'None'
            })
        
        return cookies
    
    async def initialize(self) -> bool:
        """
        Initialize browser and authenticate with Claude.
        
        Returns:
            bool: True if initialization successful, False otherwise
            
        Raises:
            ClaudeAuthenticationError: If authentication fails
        """
        try:
            logger.info("🚀 Launching browser...")
            
            self.playwright = await async_playwright().start()
            
            # Browser launch arguments
            launch_args = {
                'headless': self.headless,
                'args': [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                    '--disable-blink-features=AutomationControlled',
                    '--exclude-switches=enable-automation',
                ]
            }
            
            # Use custom Chromium path if available
            if self.chromium_path:
                launch_args['executable_path'] = self.chromium_path
                logger.info(f"Using Chromium at: {self.chromium_path}")
            
            self.browser = await self.playwright.chromium.launch(**launch_args)
            
            # Create context with anti-detection measures
            self.context = await self.browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York'
            )
            
            # Add cookies if available
            if self.cookies:
                logger.info("🍪 Setting session cookies...")
                await self.context.add_cookies(self.cookies)
            
            # Create page
            self.page = await self.context.new_page()
            
            # Add stealth JavaScript
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                window.chrome = { runtime: {} };
                
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """)
            
            # Navigate to Claude
            logger.info("🌐 Navigating to Claude.ai...")
            await self.page.goto('https://claude.ai', wait_until='networkidle', timeout=self.timeout)
            
            # Wait for page to settle
            await asyncio.sleep(3)
            
            # Check authentication
            if not await self._check_authentication():
                raise ClaudeAuthenticationError(
                    "Not authenticated with Claude. Please check your session cookies."
                )
            
            self._initialized = True
            logger.info("✅ Claude browser client initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            await self.close()
            return False
    
    async def _check_authentication(self) -> bool:
        """Check if we're authenticated with Claude."""
        try:
            # Look for chat input as indicator of successful auth
            selectors = [
                '[data-testid="chat-input"]',
                'textarea[placeholder*="Message"]',
                'textarea[placeholder*="message"]',
                '.ProseMirror',
                '[contenteditable="true"]'
            ]
            
            for selector in selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        logger.info(f"✅ Authenticated - found {selector}")
                        return True
                except:
                    continue
            
            # Check if we're on login page
            url = self.page.url
            if 'login' in url or 'auth' in url:
                logger.warning("On login page - authentication required")
                return False
            
            return False
            
        except Exception as e:
            logger.error(f"Authentication check failed: {e}")
            return False
    
    async def send_message(self, message: str, timeout: Optional[int] = None) -> str:
        """
        Send a message to Claude and get the response.
        
        Args:
            message: The message to send
            timeout: Optional timeout in seconds (default: 30)
            
        Returns:
            str: Claude's response
            
        Raises:
            ClaudeBrowserNotInitializedError: If client not initialized
            ClaudeTimeoutError: If operation times out
            ClaudeResponseError: If response extraction fails
        """
        if not self._initialized or not self.page:
            raise ClaudeBrowserNotInitializedError(
                "Client not initialized. Call initialize() first."
            )
        
        timeout = timeout or 30
        
        try:
            logger.info(f"💬 Sending message: {message[:50]}...")
            
            # Navigate to new chat if needed
            current_url = self.page.url
            if '/new' not in current_url and '/chat/' not in current_url:
                await self.page.goto('https://claude.ai/chat/new', wait_until='networkidle')
                await asyncio.sleep(2)
            
            # Find and clear input
            input_element = await self._find_input_element()
            if not input_element:
                raise ClaudeResponseError("Could not find chat input element")
            
            # THE CRITICAL FIX: Clear and type properly for ProseMirror
            await input_element.click()
            await self.page.keyboard.press('Control+A')
            await self.page.keyboard.press('Backspace')
            await input_element.type(message, delay=50)
            await asyncio.sleep(1)  # Let send button enable
            
            # Send the message
            await self._click_send_button()
            
            logger.info("⏳ Waiting for Claude's response...")
            await asyncio.sleep(15)  # Give Claude time to respond
            
            # Extract response
            response = await self._extract_response()
            
            if response:
                logger.info(f"📥 Received response: {response[:100]}...")
                return response
            else:
                raise ClaudeResponseError("Failed to extract Claude's response")
            
        except asyncio.TimeoutError:
            raise ClaudeTimeoutError(f"Operation timed out after {timeout} seconds")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise
    
    async def _find_input_element(self):
        """Find the chat input element."""
        selectors = [
            '[data-testid="chat-input"]',
            'textarea[placeholder*="Message"]',
            'textarea[placeholder*="message"]',
            '.ProseMirror',
            '[contenteditable="true"]',
            'textarea'
        ]
        
        for selector in selectors:
            try:
                element = await self.page.wait_for_selector(selector, timeout=2000)
                if element:
                    logger.debug(f"Found input with selector: {selector}")
                    return element
            except:
                continue
        
        return None
    
    async def _click_send_button(self):
        """Click the send button or press Enter."""
        send_selectors = [
            'button[aria-label*="Send"]',
            'button[aria-label*="send"]',
            '[data-testid="send-button"]',
            'button.text-text-500',
            'button svg circle',
            'button:has(svg)'
        ]
        
        for selector in send_selectors:
            try:
                button = await self.page.query_selector(selector)
                if button and await button.is_visible():
                    await button.click()
                    logger.debug(f"Clicked send button: {selector}")
                    return
            except:
                continue
        
        # Fallback: press Ctrl+Enter
        logger.debug("No send button found, pressing Ctrl+Enter")
        await self.page.keyboard.press('Control+Enter')
    
    async def _extract_response(self) -> str:
        """Extract Claude's response from the page."""
        return await self.page.evaluate("""
            () => {
                // Look for response text
                const allMessages = document.querySelectorAll('.whitespace-normal.break-words, .whitespace-pre-wrap.break-words');
                
                if (allMessages.length > 0) {
                    for (let i = allMessages.length - 1; i >= 0; i--) {
                        const msg = allMessages[i];
                        const text = msg.innerText.trim();
                        
                        // Skip user messages and UI elements
                        if (text.length > 10 && 
                            !text.includes('You are') &&
                            !text.includes('User:') &&
                            !text.includes('Claude can make mistakes')) {
                            return text;
                        }
                    }
                }
                
                // Fallback: parse line by line
                const allText = document.body.innerText;
                const lines = allText.split('\\n');
                let responseLines = [];
                let foundEnd = false;
                
                for (let i = lines.length - 1; i >= 0; i--) {
                    const line = lines[i].trim();
                    
                    if (line.includes('Claude can make mistakes') ||
                        line.includes('Copy') ||
                        line.includes('Retry')) {
                        foundEnd = true;
                        continue;
                    }
                    
                    if (foundEnd && line.length > 10) {
                        responseLines.unshift(line);
                        if (responseLines.join(' ').length > 100) {
                            break;
                        }
                    }
                }
                
                return responseLines.join(' ') || null;
            }
        """)
    
    async def new_conversation(self) -> None:
        """Start a new conversation."""
        if not self._initialized:
            raise ClaudeBrowserNotInitializedError(
                "Client not initialized. Call initialize() first."
            )
        
        await self.page.goto('https://claude.ai/chat/new', wait_until='networkidle')
        await asyncio.sleep(2)
        self.conversation_id = None
        logger.info("🆕 Started new conversation")
    
    async def close(self) -> None:
        """Clean up browser resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            self._initialized = False
            logger.info("🔒 Browser closed")
            
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Convenience function
async def create_client(
    headless: bool = True,
    session_key: Optional[str] = None,
    org_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> ClaudeBrowserClient:
    """
    Create and initialize a Claude browser client.
    
    Args:
        headless: Run browser in headless mode
        session_key: Claude session key
        org_id: Claude organization ID
        user_id: Claude user ID
        
    Returns:
        ClaudeBrowserClient: Initialized client
    """
    # Set environment variables if provided
    if session_key:
        os.environ['CLAUDE_SESSION_KEY'] = session_key
    if org_id:
        os.environ['CLAUDE_ORG_ID'] = org_id
    if user_id:
        os.environ['CLAUDE_USER_ID'] = user_id
    
    client = ClaudeBrowserClient(headless=headless)
    await client.initialize()
    return client