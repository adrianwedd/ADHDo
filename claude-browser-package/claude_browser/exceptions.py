"""
Custom exceptions for Claude Browser Integration.
"""


class ClaudeBrowserError(Exception):
    """Base exception for all Claude Browser errors."""
    pass


class ClaudeAuthenticationError(ClaudeBrowserError):
    """Raised when authentication with Claude fails."""
    pass


class ClaudeTimeoutError(ClaudeBrowserError):
    """Raised when operations timeout."""
    pass


class ClaudeResponseError(ClaudeBrowserError):
    """Raised when response extraction fails."""
    pass


class ClaudeBrowserNotInitializedError(ClaudeBrowserError):
    """Raised when trying to use client before initialization."""
    pass