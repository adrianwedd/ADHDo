# Claude Browser Integration

A Python package for interacting with Claude.ai through browser automation, bypassing API limitations and Cloudflare protection.

## Features

- ✅ **No API key required** - Uses browser session cookies
- ✅ **Bypasses Cloudflare** - Full browser automation
- ✅ **Raspberry Pi support** - Optimized for ARM devices
- ✅ **Cross-platform** - Works on Windows, macOS, and Linux
- ✅ **Async/await** - Modern Python async support
- ✅ **Context manager** - Automatic cleanup
- ✅ **Auto-retry** - Handles transient failures

## Installation

```bash
pip install claude-browser
```

After installation, install Playwright browsers:
```bash
playwright install chromium
playwright install-deps  # System dependencies
```

## Quick Start

```python
import asyncio
from claude_browser import ClaudeBrowserClient

async def main():
    # Initialize client
    client = ClaudeBrowserClient(headless=True)
    
    try:
        # Connect to Claude
        if await client.initialize():
            # Send message and get response
            response = await client.send_message("Hello, Claude!")
            print(f"Claude says: {response}")
    finally:
        # Clean up
        await client.close()

asyncio.run(main())
```

## Authentication

### Method 1: Environment Variables (Recommended)

1. Log into [Claude.ai](https://claude.ai) in your browser
2. Open Developer Tools (F12)
3. Go to Application → Cookies → claude.ai
4. Copy the cookie values and set as environment variables:

```bash
export CLAUDE_SESSION_KEY="sk-ant-sid01-..."
export CLAUDE_ORG_ID="your-org-id"
export CLAUDE_USER_ID="your-user-id"
```

### Method 2: Direct Cookie Passing

```python
cookies = [
    {
        'name': 'sessionKey',
        'value': 'sk-ant-sid01-...',
        'domain': '.claude.ai',
        'path': '/',
        'httpOnly': True,
        'secure': True,
        'sameSite': 'Lax'
    }
]

client = ClaudeBrowserClient(cookies=cookies)
```

## Advanced Usage

### Context Manager

```python
async with ClaudeBrowserClient() as client:
    response = await client.send_message("What is the meaning of life?")
    print(response)
```

### Custom Chromium Path

```python
# For Raspberry Pi
client = ClaudeBrowserClient(
    chromium_path="/usr/bin/chromium-browser"
)

# For macOS
client = ClaudeBrowserClient(
    chromium_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
)
```

### Multiple Conversations

```python
async with ClaudeBrowserClient() as client:
    # First conversation
    response1 = await client.send_message("Tell me about Python")
    print(response1)
    
    # Start new conversation
    await client.new_conversation()
    
    # Second conversation (no context from first)
    response2 = await client.send_message("Tell me about JavaScript")
    print(response2)
```

### Error Handling

```python
from claude_browser import (
    ClaudeBrowserClient,
    ClaudeAuthenticationError,
    ClaudeTimeoutError,
    ClaudeResponseError
)

async def safe_chat():
    client = ClaudeBrowserClient()
    
    try:
        await client.initialize()
        response = await client.send_message("Hello!")
        return response
        
    except ClaudeAuthenticationError:
        print("Authentication failed - check your cookies")
    except ClaudeTimeoutError:
        print("Request timed out - Claude might be slow")
    except ClaudeResponseError:
        print("Failed to extract response")
    finally:
        await client.close()
```

## Platform-Specific Notes

### Raspberry Pi

The package automatically detects and uses system Chromium on Raspberry Pi:

```python
# Auto-detection works
client = ClaudeBrowserClient()

# Or specify explicitly
client = ClaudeBrowserClient(
    chromium_path="/usr/bin/chromium-browser"
)
```

### Windows

Requires Chrome or Chromium installed. The package will auto-detect the installation.

### macOS

Requires Chrome or Chromium. Install via:
```bash
brew install --cask google-chrome
```

## Troubleshooting

### "Timeout on navigation"

**Solution**: Increase timeout or check internet connection
```python
client = ClaudeBrowserClient(timeout=60000)  # 60 seconds
```

### "Send button disabled"

**Solution**: This package handles ProseMirror correctly, but ensure you're not sending empty messages

### "Authentication failed"

**Solution**: Your session cookies may have expired. Get fresh cookies from your browser.

### "No module named 'playwright'"

**Solution**: Install playwright and system dependencies
```bash
pip install playwright
playwright install chromium
playwright install-deps
```

## Performance

- **Initialization**: 5-10 seconds
- **Message round-trip**: 15-25 seconds
- **Memory usage**: ~500MB (Chromium)
- **CPU**: Moderate usage during browser operations

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [Playwright](https://playwright.dev/)
- Inspired by the need to bypass API limitations
- Special thanks to the "you're so close" moment that led to the ProseMirror fix

## Disclaimer

This package is for educational purposes. Please respect Claude's terms of service and use responsibly.