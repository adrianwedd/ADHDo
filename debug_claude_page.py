#!/usr/bin/env python3
"""Debug script to inspect Claude page structure."""

import asyncio
from playwright.async_api import async_playwright
import os
import json

async def inspect_claude_page():
    """Inspect Claude page to understand the structure."""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        
        # Set cookies
        session_key = os.getenv('CLAUDE_SESSION_KEY', '')
        if session_key:
            await context.add_cookies([{
                'name': 'sessionKey',
                'value': session_key,
                'domain': '.claude.ai',
                'path': '/'
            }])
        
        page = await context.new_page()
        await page.goto('https://claude.ai/new')
        await asyncio.sleep(3)
        
        # Send a test message
        input_element = await page.query_selector('.ProseMirror')
        if input_element:
            await input_element.click()
            await input_element.fill('Respond with JSON: {"test": "hello", "value": 123}')
            
            # Find send button
            send_button = await page.query_selector('button[aria-label*="Send"]')
            if send_button:
                await send_button.click()
                print("Message sent, waiting for response...")
                await asyncio.sleep(10)
        
        # Inspect the page structure
        structure = await page.evaluate("""
            () => {
                const result = {
                    codeBlocks: [],
                    messages: [],
                    selectors: {}
                };
                
                // Find code blocks
                document.querySelectorAll('pre, code').forEach(el => {
                    result.codeBlocks.push({
                        tag: el.tagName,
                        class: el.className,
                        text: el.innerText.substring(0, 100)
                    });
                });
                
                // Find message containers
                const possibleSelectors = [
                    '.whitespace-pre-wrap',
                    '.prose',
                    '[data-testid*="message"]',
                    '.text-text-200',
                    'div[class*="message"]'
                ];
                
                possibleSelectors.forEach(selector => {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > 0) {
                        result.selectors[selector] = elements.length;
                        elements.forEach(el => {
                            if (el.innerText && el.innerText.length > 20) {
                                result.messages.push({
                                    selector: selector,
                                    text: el.innerText.substring(0, 200)
                                });
                            }
                        });
                    }
                });
                
                return result;
            }
        """)
        
        print(json.dumps(structure, indent=2))
        
        # Take screenshot
        await page.screenshot(path='claude_structure_debug.png')
        print("\nScreenshot saved to claude_structure_debug.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_claude_page())