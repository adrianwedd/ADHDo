#!/usr/bin/env python3
"""
Final validation of both Claude routing and music system
"""
import asyncio
import json
from playwright.async_api import async_playwright

async def test_final_validation():
    print("🎯 FINAL VALIDATION - Claude + Music")
    print("=" * 50)
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=False, executable_path='/usr/bin/chromium-browser')
        except:
            browser = await p.chromium.launch(headless=False)
            
        page = await browser.new_page()
        
        try:
            print("1. Loading dashboard...")
            await page.goto("http://localhost:23444", wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            # Check Claude status
            claude_status = await page.text_content("#claude-status")
            print(f"   - Claude status: {claude_status}")
            
            # Check music status  
            music_status = await page.text_content("#music-status")
            print(f"   - Music status: {music_status}")
            
            print("\n2. Testing Claude with complex query...")
            await page.fill("#messageInput", "Can you help me understand why I struggle with task switching?")
            await page.click("button:has-text('Send')")
            
            # Wait for response
            await page.wait_for_timeout(5000)
            
            # Get latest message
            messages = await page.query_selector_all(".message.assistant")
            if messages:
                latest = await messages[-1].text_content()
                print(f"   - Claude response: {latest[:100]}...")
                
                # Check if it's a sophisticated response (Claude) vs simple pattern
                if len(latest) > 150 and any(word in latest.lower() for word in ['adhd', 'switching', 'cognitive', 'brain']):
                    print("   - ✅ Sophisticated Claude response detected!")
                else:
                    print("   - ❌ Still getting simple pattern response")
            
            print("\n3. Testing music controls...")
            
            # Click stop music first to reset
            stop_button = await page.query_selector("button:has-text('Stop Music')")
            if stop_button:
                await stop_button.click()
                await page.wait_for_timeout(1000)
            
            # Start energy music
            await page.click("button:has-text('Energy Music')")
            await page.wait_for_timeout(3000)
            
            music_final = await page.text_content("#music-status")
            print(f"   - Music switched to: {music_final}")
            
            print("\n4. Final system health...")
            
            system = await page.text_content("#system-status")
            memory = await page.text_content("#memory-status")
            
            print(f"   - System: {system}")
            print(f"   - Memory: {memory}")
            print(f"   - Music: {music_final}")
            print(f"   - Claude: {claude_status}")
            
            await page.screenshot(path="final_validation.png")
            print("\n✅ Validation complete! Screenshot saved: final_validation.png")
            
            await page.wait_for_timeout(3000)
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_final_validation())