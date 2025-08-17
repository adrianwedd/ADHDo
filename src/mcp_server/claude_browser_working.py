"""
Claude Browser Client for Python - Adapted from working JavaScript implementation
Uses Playwright to bypass Cloudflare like the working Puppeteer version
"""

import asyncio
import os
import json
import logging
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
import time

logger = logging.getLogger(__name__)


class ClaudeBrowserClient:
    """Claude client using Playwright - Python port of working JS implementation."""
    
    def __init__(self, headless: bool = True):
        """Initialize Claude browser client."""
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.conversation_id: Optional[str] = None
        self.headless = headless
        self.timeout = 120000  # 120 seconds for long prompts
        
        # Load cookies from environment
        self.cookies = self._load_cookies_from_env()
        
        logger.info(f"🤖 Browser mode: {'headless' if headless else 'visible'}")
    
    async def _check_auth_expired(self) -> bool:
        """Check if authentication has expired."""
        if not self.page:
            return True
        
        try:
            # Check for common auth failure indicators
            auth_fail_selectors = [
                'text="Session expired"',
                'text="Please sign in"',
                'text="Authentication required"',
                '[data-testid="login-button"]'
            ]
            
            for selector in auth_fail_selectors:
                if await self.page.locator(selector).count() > 0:
                    return True
            
            # Check if we're redirected to login page
            if 'login' in self.page.url or 'auth' in self.page.url:
                return True
                
            return False
        except:
            return False
    
    async def _refresh_session(self):
        """Attempt to refresh the session."""
        logger.info("Attempting session refresh...")
        
        # Reload cookies from environment (user may have updated them)
        self.cookies = self._load_cookies_from_env()
        
        if self.context:
            # Clear existing cookies and add new ones
            await self.context.clear_cookies()
            await self.context.add_cookies(self.cookies)
            
            # Reload the page
            if self.page:
                await self.page.reload(wait_until='networkidle', timeout=30000)
                await asyncio.sleep(2)
                
                # Check if refresh worked
                if not await self._check_auth_expired():
                    logger.info("✅ Session refreshed successfully")
                    return
        
        # If refresh failed, try full re-initialization
        logger.warning("Simple refresh failed, attempting full re-initialization...")
        await self.cleanup()
        success = await self.initialize()
        if not success:
            raise Exception("Failed to refresh session. Please update CLAUDE_SESSION_KEY environment variable.")
    
    def _load_cookies_from_env(self) -> List[Dict[str, Any]]:
        """Load cookies from environment variables."""
        cookies = []
        
        # Essential cookies
        session_key = os.getenv('CLAUDE_SESSION_KEY', '')
        org_id = os.getenv('CLAUDE_ORG_ID', '1287541f-a020-4755-bbb0-8945a1be4fa5')
        user_id = os.getenv('CLAUDE_USER_ID', 'f71a8285-af11-4a58-ae8a-0020ecb210e8')
        
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
        
        cookies.append({
            'name': 'lastActiveOrg',
            'value': org_id,
            'domain': '.claude.ai',
            'path': '/',
            'httpOnly': False,
            'secure': True,
            'sameSite': 'Lax'
        })
        
        cookies.append({
            'name': 'ajs_user_id',
            'value': user_id,
            'domain': '.claude.ai',
            'path': '/',
            'httpOnly': False,
            'secure': False,
            'sameSite': 'Lax'
        })
        
        # Cloudflare clearance cookie - critical for bypassing protection
        cf_clearance = os.getenv('CLAUDE_CF_CLEARANCE')
        if cf_clearance:
            cookies.append({
                'name': 'cf_clearance',
                'value': cf_clearance,
                'domain': '.claude.ai',
                'path': '/',
                'httpOnly': True,
                'secure': True,
                'sameSite': 'None'
            })
        
        # Optional CF_BM cookie
        cf_bm = os.getenv('CLAUDE_CF_BM')
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
        
        device_id = os.getenv('CLAUDE_DEVICE_ID', 'e8262e68-2d3d-4b30-a486-ec5827180a6b')
        if device_id:
            cookies.append({
                'name': 'anthropic-device-id',
                'value': device_id,
                'domain': 'claude.ai',
                'path': '/',
                'httpOnly': False,
                'secure': True,
                'sameSite': 'Lax'
            })
        
        activity_id = os.getenv('CLAUDE_ACTIVITY_SESSION_ID', '545db420-68a0-4cc6-bb87-76f9306eb522')
        if activity_id:
            cookies.append({
                'name': 'activitySessionId',
                'value': activity_id,
                'domain': 'claude.ai',
                'path': '/',
                'httpOnly': True,
                'secure': True,
                'sameSite': 'Lax'
            })
        
        return cookies
    
    async def initialize(self) -> bool:
        """Initialize browser and set up Claude session."""
        try:
            logger.info("🚀 Launching Chromium browser...")
            
            self.playwright = await async_playwright().start()
            
            # Launch with stealth args similar to Puppeteer
            # Use system Chromium on Raspberry Pi
            self.browser = await self.playwright.chromium.launch(
                executable_path='/usr/bin/chromium-browser',
                headless=self.headless,
                args=[
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
                    # Fingerprinting protection
                    '--disable-blink-features=AutomationControlled',
                    '--exclude-switches=enable-automation',
                    '--disable-web-security',
                    '--allow-running-insecure-content'
                ]
            )
            
            # Create context with realistic settings
            self.context = await self.browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York'
            )
            
            # Add cookies
            logger.info("🍪 Setting session cookies...")
            await self.context.add_cookies(self.cookies)
            
            # Create page
            self.page = await self.context.new_page()
            
            # Add stealth JavaScript
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Mock chrome object
                window.chrome = { runtime: {} };
                
                // Remove automation indicators
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """)
            
            # Navigate to Claude with shorter timeout
            logger.info("🌐 Navigating to Claude.ai...")
            await self.page.goto('https://claude.ai', wait_until='domcontentloaded', timeout=30000)
            
            # Wait for page to settle
            await asyncio.sleep(3)
            
            # Debug info
            page_title = await self.page.title()
            logger.info(f"📄 Page title: {page_title}")
            
            url = self.page.url
            logger.info(f"🔗 Current URL: {url}")
            
            # Check for chat input with multiple selectors (from JS implementation)
            selectors = [
                '[data-testid="chat-input"]',
                'textarea[placeholder*="Message"]',
                'textarea[placeholder*="message"]',
                '.ProseMirror',
                '[contenteditable="true"]',
                'textarea',
                'input[type="text"]'
            ]
            
            input_found = False
            for selector in selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        logger.info(f"✅ Found input with selector: {selector}")
                        input_found = True
                        break
                except:
                    continue
            
            if not input_found:
                logger.warning("⚠️ No chat input found, checking page content...")
                
                # Check page content
                body_text = await self.page.inner_text('body')
                logger.info(f"📝 Page content preview: {body_text[:200]}")
                
                # Check for auth issues
                auth_keywords = ['sign in', 'login', 'authenticate', 'blocked', 'access denied']
                has_auth_issue = any(keyword in body_text.lower() for keyword in auth_keywords)
                
                if has_auth_issue:
                    logger.error("🚨 Authentication issue detected")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            return False
    
    async def send_message(self, message: str, timeout: int = 30, retry_on_auth_fail: bool = True) -> str:
        """Send message to Claude and get response with auto-refresh on auth failure."""
        if not self.page:
            raise Exception("Browser not initialized. Call initialize() first.")
        
        # Log full interaction to untracked file
        import datetime
        log_file = "/home/pi/repos/ADHDo/claude_interactions.log"
        with open(log_file, "a") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"TIMESTAMP: {datetime.datetime.now().isoformat()}\n")
            f.write(f"REQUEST:\n{message}\n")
            f.write(f"{'-'*40}\n")
        
        try:
            # Check if session is still valid
            if await self._check_auth_expired():
                logger.warning("Session expired, attempting refresh...")
                if retry_on_auth_fail:
                    await self._refresh_session()
                    return await self.send_message(message, timeout, retry_on_auth_fail=False)
                else:
                    raise Exception("Session expired and refresh failed")
            
            logger.info(f"💬 Sending message: {message[:50]}...")
            
            # Check if we're already on a chat page
            current_url = self.page.url
            if '/new' in current_url or '/chat/' in current_url:
                logger.info(f"Already on chat page: {current_url}")
            else:
                logger.info("Navigating to new chat...")
                await self.page.goto('https://claude.ai/chat/new', wait_until='networkidle', timeout=self.timeout)
                await asyncio.sleep(2)
            
            # Find chat input using selectors from JS
            input_selectors = [
                '[data-testid="chat-input"]',
                'textarea[placeholder*="Message"]',
                'textarea[placeholder*="message"]',
                '.ProseMirror',
                '[contenteditable="true"]',
                'textarea'
            ]
            
            input_element = None
            for selector in input_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        logger.info(f"💬 Using input selector: {selector}")
                        input_element = element
                        break
                except:
                    continue
            
            if not input_element:
                raise Exception("Could not find chat input element")
            
            # Clear and type message
            await input_element.click()
            
            # For ProseMirror, we need to clear it first
            await self.page.keyboard.press('Control+A')
            await self.page.keyboard.press('Backspace')
            
            # Use JavaScript to fill content quickly instead of typing character by character
            await input_element.fill(message)
            
            # Wait for the send button to become enabled
            await asyncio.sleep(1)
            
            # Send message - try multiple methods
            # First try the send button with the circle icon
            send_selectors = [
                'button[aria-label*="Send"]',
                'button[aria-label*="send"]',
                '[data-testid="send-button"]',
                'button.text-text-500',  # The circle button in the screenshot
                'button svg circle',  # Button with circle icon
                'button:has(svg)'  # Any button with SVG
            ]
            
            sent = False
            for selector in send_selectors:
                try:
                    button = await self.page.query_selector(selector)
                    if button:
                        # Check if button is visible and enabled
                        is_visible = await button.is_visible()
                        if is_visible:
                            logger.info(f"📤 Clicking send button: {selector}")
                            await button.click()
                            sent = True
                            break
                except:
                    continue
            
            if not sent:
                # Fallback: press Ctrl+Enter or just Enter
                logger.info("📤 No send button found, pressing Ctrl+Enter...")
                await self.page.keyboard.press('Control+Enter')
            
            logger.info("📤 Message sent, waiting for response...")
            
            # Debug: save screenshot
            await self.page.screenshot(path='/home/pi/repos/ADHDo/claude_debug.png')
            logger.info("📸 Screenshot saved to claude_debug.png")
            
            # Wait for response - give it more time
            logger.info("⏳ Waiting for Claude to respond...")
            await asyncio.sleep(15)  # Wait 15 seconds for response
            
            # Take another screenshot to see the response
            await self.page.screenshot(path='/home/pi/repos/ADHDo/claude_response.png')
            logger.info("📸 Response screenshot saved to claude_response.png")
            
            # Extract response - look for Claude's response text
            response = await self.page.evaluate("""
                () => {
                    // Try to find Claude's response using multiple strategies
                    
                    // Strategy 1: Look for code blocks or JSON responses
                    const codeBlocks = document.querySelectorAll('pre code, code');
                    for (let block of codeBlocks) {
                        const text = block.innerText.trim();
                        // Check if it looks like JSON
                        if (text.startsWith('{') && text.includes('"reasoning"')) {
                            return text;
                        }
                    }
                    
                    // Strategy 2: Look for the assistant message content
                    const assistantMessages = document.querySelectorAll('[data-testid="user-message"]');
                    const allMessages = document.querySelectorAll('.whitespace-normal.break-words, .whitespace-pre-wrap.break-words');
                    
                    if (allMessages.length > 0) {
                        // Get the last message that's not from the user
                        for (let i = allMessages.length - 1; i >= 0; i--) {
                            const msg = allMessages[i];
                            const text = msg.innerText.trim();
                            
                            // Skip if it's our message or UI elements
                            if (!text.includes('this is a test') && 
                                !text.includes('Say exactly:') && 
                                !text.includes('You are an ADHD') &&
                                text.length > 10 &&
                                !text.includes('Claude can make mistakes')) {
                                return text;
                            }
                        }
                    }
                    
                    // Strategy 3: Look for JSON in any text content
                    const allText = document.body.innerText;
                    
                    // Try to find JSON object in the text
                    const jsonMatch = allText.match(/\{[^{}]*"reasoning"[^{}]*\}/s);
                    if (jsonMatch) {
                        // Try to extract complete JSON including nested objects
                        const startIdx = allText.indexOf(jsonMatch[0]);
                        let braceCount = 0;
                        let inString = false;
                        let escaped = false;
                        let jsonEnd = startIdx;
                        
                        for (let i = startIdx; i < allText.length; i++) {
                            const char = allText[i];
                            
                            if (!escaped && char === '"') {
                                inString = !inString;
                            } else if (!inString && char === '{') {
                                braceCount++;
                            } else if (!inString && char === '}') {
                                braceCount--;
                                if (braceCount === 0) {
                                    jsonEnd = i + 1;
                                    break;
                                }
                            }
                            
                            escaped = (char === '\\\\' && !escaped);
                        }
                        
                        if (jsonEnd > startIdx) {
                            return allText.substring(startIdx, jsonEnd);
                        }
                    }
                    
                    // Strategy 4: Collect all response lines
                    const lines = allText.split('\\n');
                    let foundUserMessage = false;
                    let responseLines = [];
                    
                    for (let i = 0; i < lines.length; i++) {
                        const line = lines[i].trim();
                        
                        // Look for the end of our message
                        if (line.includes('Now analyze this state') || line.includes('You are an ADHD')) {
                            foundUserMessage = true;
                            responseLines = [];
                            continue;
                        }
                        
                        // After finding user message, collect Claude's response
                        if (foundUserMessage) {
                            // Stop at UI elements
                            if (line.includes('Claude can make mistakes') || 
                                line.includes('Reply to Claude')) {
                                break;
                            }
                            
                            if (line.length > 0) {
                                responseLines.push(line);
                            }
                        }
                    }
                    
                    if (responseLines.length > 0) {
                        return responseLines.join('\\n');
                    }
                    
                    return 'Message sent - awaiting response extraction';
                }
            """)
            
            logger.info(f"📥 Received response: {response[:100]}...")
            
            # Log response to untracked file
            import datetime
            log_file = "/home/pi/repos/ADHDo/claude_interactions.log"
            with open(log_file, "a") as f:
                f.write(f"RESPONSE:\n{response}\n")
                f.write(f"TIMESTAMP: {datetime.datetime.now().isoformat()}\n")
                f.write(f"{'='*80}\n")
            
            # Get conversation ID
            url = self.page.url
            if '/chat/' in url:
                self.conversation_id = url.split('/chat/')[-1].split('?')[0]
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to send message: {e}")
            raise
    
    async def close(self):
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
            
            logger.info("🔒 Browser closed")
            
        except Exception as e:
            logger.error(f"Error closing browser: {e}")


# Global instance
_browser_client: Optional[ClaudeBrowserClient] = None


async def get_claude_browser() -> ClaudeBrowserClient:
    """Get or create the global Claude browser client."""
    global _browser_client
    
    if _browser_client is None:
        _browser_client = ClaudeBrowserClient(headless=False)
        success = await _browser_client.initialize()
        if not success:
            raise Exception("Failed to initialize Claude browser client")
    
    return _browser_client


async def test_claude_browser():
    """Test the browser client."""
    try:
        client = await get_claude_browser()
        response = await client.send_message("Hello! Please respond with exactly 5 words.")
        print(f"✅ Claude responded: {response}")
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        if _browser_client:
            await _browser_client.close()