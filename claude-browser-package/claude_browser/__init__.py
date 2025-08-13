"""
Claude Browser Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A Python package for interacting with Claude.ai through browser automation.
Bypasses API limitations and Cloudflare protection using Playwright.

Basic usage:
    >>> from claude_browser import ClaudeBrowserClient
    >>> 
    >>> client = ClaudeBrowserClient()
    >>> await client.initialize()
    >>> response = await client.send_message("Hello Claude!")
    >>> print(response)

Full documentation at https://github.com/yourusername/claude-browser
"""

__version__ = "1.0.0"
__author__ = "Adrian Wedd"
__license__ = "MIT"

from .client import ClaudeBrowserClient
from .exceptions import (
    ClaudeAuthenticationError,
    ClaudeTimeoutError,
    ClaudeResponseError,
    ClaudeBrowserNotInitializedError
)

__all__ = [
    "ClaudeBrowserClient",
    "ClaudeAuthenticationError", 
    "ClaudeTimeoutError",
    "ClaudeResponseError",
    "ClaudeBrowserNotInitializedError"
]