"""
Claude Browser Client V2 - Improved version with critique fixes.

Improvements:
- Added retry mechanism with exponential backoff
- Added response caching
- Better type hints
- Connection reuse
- Rate limiting
"""

import asyncio
import hashlib
import time
from typing import Optional, Dict, Any, List, Union, TypeVar, Generic
from datetime import datetime, timedelta
from dataclasses import dataclass
from functools import lru_cache
import logging

from playwright.async_api import async_playwright, Browser, Page, BrowserContext

from .exceptions import (
    ClaudeAuthenticationError,
    ClaudeTimeoutError,
    ClaudeResponseError,
    ClaudeBrowserNotInitializedError
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CachedResponse:
    """Cached response with timestamp."""
    response: str
    timestamp: datetime
    
    def is_expired(self, ttl_seconds: int = 3600) -> bool:
        """Check if cache entry is expired."""
        return datetime.now() - self.timestamp > timedelta(seconds=ttl_seconds)


class RateLimiter:
    """Simple rate limiter."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: List[datetime] = []
    
    async def acquire(self) -> None:
        """Wait if necessary to respect rate limits."""
        now = datetime.now()
        
        # Remove old requests outside window
        self.requests = [
            req for req in self.requests 
            if now - req < timedelta(seconds=self.window_seconds)
        ]
        
        if len(self.requests) >= self.max_requests:
            # Wait until oldest request exits window
            wait_time = self.window_seconds - (now - self.requests[0]).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
        
        self.requests.append(now)


class ClaudeBrowserClientV2:
    """
    Improved Claude.ai browser automation client.
    
    Features:
    - Connection pooling and reuse
    - Retry with exponential backoff
    - Response caching
    - Rate limiting
    - Better type hints
    """
    
    # Class-level connection pool
    _connection_pool: Dict[str, 'ClaudeBrowserClientV2'] = {}
    
    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,
        chromium_path: Optional[str] = None,
        cookies: Optional[List[Dict[str, Any]]] = None,
        cache_ttl: int = 3600,
        max_retries: int = 3,
        rate_limit: Optional[RateLimiter] = None
    ):
        """
        Initialize improved Claude browser client.
        
        Args:
            headless: Run browser in headless mode
            timeout: Default timeout in milliseconds
            chromium_path: Path to Chromium executable
            cookies: Optional list of cookies
            cache_ttl: Cache time-to-live in seconds
            max_retries: Maximum retry attempts
            rate_limit: Optional rate limiter instance
        """
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self.conversation_id: Optional[str] = None
        
        self.headless = headless
        self.timeout = timeout
        self.chromium_path = chromium_path or self._detect_chromium_path()
        self.cookies = cookies or self._load_cookies_from_env()
        
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        self.rate_limiter = rate_limit or RateLimiter()
        
        self._initialized = False
        self._response_cache: Dict[str, CachedResponse] = {}
        self._last_activity = datetime.now()
        
        logger.info(f"🤖 Claude Browser Client V2 initialized")
    
    @classmethod
    async def get_or_create(
        cls,
        pool_key: str = "default",
        **kwargs
    ) -> 'ClaudeBrowserClientV2':
        """
        Get existing client from pool or create new one.
        
        Args:
            pool_key: Key for connection pooling
            **kwargs: Arguments for new client
            
        Returns:
            ClaudeBrowserClientV2 instance
        """
        if pool_key in cls._connection_pool:
            client = cls._connection_pool[pool_key]
            # Check if connection is still alive
            if client._is_connection_alive():
                logger.info(f"♻️ Reusing existing connection: {pool_key}")
                return client
            else:
                # Connection dead, remove from pool
                await client.close()
                del cls._connection_pool[pool_key]
        
        # Create new client
        client = cls(**kwargs)
        if await client.initialize():
            cls._connection_pool[pool_key] = client
            return client
        else:
            raise ClaudeAuthenticationError("Failed to initialize client")
    
    def _is_connection_alive(self) -> bool:
        """Check if browser connection is still alive."""
        if not self._initialized or not self.page:
            return False
        
        # Check if idle for too long (5 minutes)
        if datetime.now() - self._last_activity > timedelta(minutes=5):
            return False
        
        try:
            # Try to evaluate simple JS
            self.page.evaluate("1 + 1")
            return True
        except:
            return False
    
    def _get_cache_key(self, message: str) -> str:
        """Generate cache key for message."""
        return hashlib.md5(message.encode()).hexdigest()
    
    async def send_message_with_retry(
        self,
        message: str,
        timeout: Optional[int] = None,
        use_cache: bool = True
    ) -> str:
        """
        Send message with retry logic and caching.
        
        Args:
            message: Message to send
            timeout: Optional timeout in seconds
            use_cache: Whether to use response cache
            
        Returns:
            Claude's response
        """
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(message)
            if cache_key in self._response_cache:
                cached = self._response_cache[cache_key]
                if not cached.is_expired(self.cache_ttl):
                    logger.info("📦 Returning cached response")
                    return cached.response
        
        # Apply rate limiting
        await self.rate_limiter.acquire()
        
        # Try with exponential backoff
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await self.send_message(message, timeout)
                
                # Cache successful response
                if use_cache:
                    self._response_cache[cache_key] = CachedResponse(
                        response=response,
                        timestamp=datetime.now()
                    )
                
                self._last_activity = datetime.now()
                return response
                
            except (ClaudeTimeoutError, ClaudeResponseError) as e:
                last_error = e
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            except Exception as e:
                # Don't retry on other errors
                raise
        
        # All retries failed
        raise last_error or ClaudeResponseError("All retry attempts failed")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the client.
        
        Returns:
            Health status dictionary
        """
        return {
            "initialized": self._initialized,
            "connection_alive": self._is_connection_alive(),
            "last_activity": self._last_activity.isoformat(),
            "cache_size": len(self._response_cache),
            "conversation_id": self.conversation_id,
            "idle_seconds": (datetime.now() - self._last_activity).total_seconds()
        }
    
    def clear_cache(self) -> None:
        """Clear response cache."""
        self._response_cache.clear()
        logger.info("🗑️ Cache cleared")
    
    # ... (include all other methods from original client with proper type hints)
    
    async def send_message(self, message: str, timeout: Optional[int] = None) -> str:
        """Send message (implementation from original)."""
        # Implementation from original client
        pass
    
    async def initialize(self) -> bool:
        """Initialize browser (implementation from original)."""
        # Implementation from original client
        pass
    
    async def close(self) -> None:
        """Close browser (implementation from original)."""
        # Implementation from original client
        pass
    
    def _detect_chromium_path(self) -> Optional[str]:
        """Detect Chromium path (implementation from original)."""
        # Implementation from original client
        pass
    
    def _load_cookies_from_env(self) -> List[Dict[str, Any]]:
        """Load cookies (implementation from original)."""
        # Implementation from original client
        pass