#!/usr/bin/env python3
"""
Patch the cognitive loop to use simple Claude integration.
This replaces the broken browser-based Claude with a working API-based approach.
"""

import sys
from pathlib import Path

def patch_llm_client():
    """Patch llm_client.py to use simple Claude integration."""
    
    llm_client_path = Path(__file__).parent / "src" / "mcp_server" / "llm_client.py"
    
    if not llm_client_path.exists():
        print(f"❌ File not found: {llm_client_path}")
        return False
    
    content = llm_client_path.read_text()
    
    # Check if already patched
    if "simple_claude_integration" in content:
        print("✅ llm_client.py already patched")
        return True
    
    # Find the imports section
    lines = content.split('\n')
    
    # Add import after other imports
    import_added = False
    for i, line in enumerate(lines):
        if line.startswith('from mcp_server.adhd_logger import'):
            lines.insert(i + 1, "from mcp_server.simple_claude_integration import simple_claude_router")
            import_added = True
            break
    
    if not import_added:
        print("❌ Could not find import location")
        return False
    
    # Now patch the _handle_claude method to use simple integration
    new_content = '\n'.join(lines)
    
    # Replace the _handle_claude method
    old_method_start = "    async def _handle_claude("
    new_method = '''    async def _handle_claude(
        self,
        user_input: str,
        context: Optional[MCPFrame],
        nudge_tier: NudgeTier,
        use_case: str = 'gentle_nudge'
    ) -> LLMResponse:
        """Handle request with Claude using simple API integration."""
        
        import time
        start_time = time.time()
        
        try:
            # Use the simple Claude router
            result = await simple_claude_router.process_request(
                user_input=user_input,
                context=context,
                nudge_tier=nudge_tier
            )
            
            return LLMResponse(
                text=result['text'],
                source=result['source'],
                confidence=result['confidence'],
                latency_ms=result['latency_ms'],
                cost_usd=0.0,
                model_used="claude-haiku" if result['source'] == 'claude' else "patterns"
            )
            
        except Exception as e:
            logger.error("Claude request failed, falling back to local", error=str(e))
            # Fallback to local LLM
            return await self._handle_local(user_input, context, nudge_tier)'''
    
    # Find and replace the method
    if old_method_start in new_content:
        # Find the end of the current _handle_claude method
        start_idx = new_content.index(old_method_start)
        
        # Find the next method definition (starts with "    async def " or "    def ")
        remaining = new_content[start_idx:]
        lines_after = remaining.split('\n')
        
        end_line_idx = None
        for i, line in enumerate(lines_after[1:], 1):  # Skip first line
            if line.startswith('    async def ') or line.startswith('    def ') or (line and not line.startswith(' ')):
                end_line_idx = i
                break
        
        if end_line_idx:
            # Replace the method
            method_lines = lines_after[:end_line_idx]
            new_remaining = new_method + '\n' + '\n'.join(lines_after[end_line_idx:])
            new_content = new_content[:start_idx] + new_remaining
        else:
            print("❌ Could not find end of _handle_claude method")
            return False
    else:
        print("❌ Could not find _handle_claude method")
        return False
    
    # Also update initialization to mark Claude as available
    init_fix = """            # Check if Claude is available via simple integration
            try:
                from mcp_server.simple_claude_integration import simple_claude_router
                self._claude_available = simple_claude_router.claude.available
                if self._claude_available:
                    logger.info("✅ Claude API available - using for complex tasks")
                else:
                    logger.info("ℹ️ Claude API not configured - using pattern matching")
            except Exception as e:
                logger.warning(f"Claude integration check failed: {e}")
                self._claude_available = False"""
    
    # Replace the browser-based Claude check
    old_check = """            # Check if Claude browser is available
            try:
                if _use_browser_claude:
                    self.claude_browser_client = await get_claude_browser()
                    self._claude_available = True
                    logger.info("✅ Claude browser available - using for complex tasks")
                else:
                    self._claude_available = False
                    logger.info("ℹ️ Claude browser not available - local + pattern matching mode")
            except Exception as e:
                logger.warning(f"Claude browser initialization failed: {e}")
                self._claude_available = False"""
    
    if old_check in new_content:
        new_content = new_content.replace(old_check, init_fix)
    
    # Write the patched content
    llm_client_path.write_text(new_content)
    print("✅ Patched llm_client.py to use simple Claude integration")
    
    return True


def main():
    """Main function."""
    
    print("🔧 Patching cognitive loop to use simple Claude integration...")
    
    if patch_llm_client():
        print("\n✨ Patch applied successfully!")
        print("\n📌 Next steps:")
        print("1. Make sure you have an Anthropic API key:")
        print("   Add to .env: ANTHROPIC_API_KEY=your-api-key")
        print("   Or use existing: CLAUDE_SESSION_KEY (if it's a valid API key)")
        print("\n2. Restart the server:")
        print("   pkill -f 'python.*minimal_main'")
        print("   PYTHONPATH=/home/pi/repos/ADHDo/src PORT=23444 /home/pi/repos/ADHDo/venv_beta/bin/python -m mcp_server.minimal_main &")
        print("\n3. Test the chat:")
        print("   curl -X POST http://localhost:23444/chat -H 'Content-Type: application/json' -d '{\"user_id\": \"test\", \"message\": \"Hello Claude!\"}'")
    else:
        print("\n❌ Patch failed. Check the errors above.")


if __name__ == "__main__":
    main()