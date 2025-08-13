#!/usr/bin/env python3
"""
Reality check - actually test the dashboard like a real user
"""
import asyncio
from playwright.async_api import async_playwright
import json

async def reality_check():
    print("🔍 REALITY CHECK - Testing Dashboard Like a Real User")
    print("=" * 60)
    
    async with async_playwright() as p:
        # Use system chromium
        try:
            browser = await p.chromium.launch(headless=False, executable_path='/usr/bin/chromium-browser')
        except:
            browser = await p.chromium.launch(headless=False)
            
        page = await browser.new_page()
        
        try:
            # Navigate to dashboard
            print("1. Loading dashboard...")
            await page.goto("http://localhost:23444", wait_until="networkidle")
            await page.wait_for_timeout(3000)  # Wait for JS to load status
            
            # Take screenshot of initial state
            await page.screenshot(path="reality_check_initial.png")
            
            # Check what the user actually sees
            print("\n2. What user sees in status bar:")
            try:
                system_status = await page.text_content("#system-status")
                memory_status = await page.text_content("#memory-status") 
                music_status = await page.text_content("#music-status")
                claude_status = await page.text_content("#claude-status")
                
                print(f"   System: {system_status}")
                print(f"   Memory: {memory_status}")
                print(f"   Music: {music_status}")
                print(f"   Claude: {claude_status}")
            except Exception as e:
                print(f"   ❌ Error reading status: {e}")
            
            # Test actual chat interaction
            print("\n3. Testing chat interaction...")
            
            # Type a message
            await page.fill("#messageInput", "I feel overwhelmed")
            await page.click("button:has-text('Send')")
            
            # Wait for response and capture it
            await page.wait_for_timeout(2000)
            
            # Get the actual chat content
            try:
                messages_html = await page.inner_html("#messages")
                print(f"   Messages HTML: {messages_html[:200]}...")
                
                # Look for the last assistant message
                assistant_messages = await page.query_selector_all(".message.assistant")
                if assistant_messages:
                    last_response = await assistant_messages[-1].text_content()
                    print(f"   Last response: {last_response}")
                else:
                    print("   ❌ No assistant messages found")
                    
            except Exception as e:
                print(f"   ❌ Error reading chat: {e}")
            
            # Test music buttons
            print("\n4. Testing music controls...")
            
            try:
                # Click focus music
                await page.click("button:has-text('Focus Music')")
                await page.wait_for_timeout(1000)
                
                # Check if music status changed
                new_music_status = await page.text_content("#music-status")
                print(f"   Music status after click: {new_music_status}")
                
                # Check activity log
                activity = await page.text_content("#activity")
                print(f"   Activity log shows: {activity[:100]}...")
                
            except Exception as e:
                print(f"   ❌ Music test error: {e}")
            
            # Final screenshot
            await page.screenshot(path="reality_check_final.png")
            print(f"\n5. Screenshots saved: reality_check_initial.png, reality_check_final.png")
            
            # Wait for user to see
            print("\n6. Browser will stay open for 10 seconds so you can see...")
            await page.wait_for_timeout(10000)
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(reality_check())