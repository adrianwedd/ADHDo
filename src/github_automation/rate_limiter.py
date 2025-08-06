"""
Intelligent Rate Limiting System

Advanced rate limiting with sliding window algorithms, predictive throttling,
and adaptive backoff for optimal GitHub API usage.
"""

import asyncio
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class RateLimitWindow:
    """Sliding window for rate limit tracking."""
    requests: deque
    window_size_seconds: int
    max_requests: int
    
    def add_request(self, timestamp: float = None) -> None:
        """Add a request to the window."""
        if timestamp is None:
            timestamp = time.time()
        self.requests.append(timestamp)
        self._cleanup_old_requests()
    
    def _cleanup_old_requests(self) -> None:
        """Remove requests outside the current window."""
        cutoff_time = time.time() - self.window_size_seconds
        while self.requests and self.requests[0] < cutoff_time:
            self.requests.popleft()
    
    def current_count(self) -> int:
        """Get current request count in window."""
        self._cleanup_old_requests()
        return len(self.requests)
    
    def can_make_request(self) -> bool:
        """Check if we can make another request without exceeding limit."""
        return self.current_count() < self.max_requests
    
    def time_until_slot_available(self) -> float:
        """Get seconds until a request slot becomes available."""
        if self.can_make_request():
            return 0.0
        
        # If we're at the limit, return time until oldest request expires
        if self.requests:
            oldest_request = self.requests[0]
            return max(0.0, oldest_request + self.window_size_seconds - time.time())
        
        return 0.0


class RateLimiter:
    """
    Intelligent rate limiting system with multiple strategies.
    
    Features:
    - Sliding window rate limiting
    - GitHub API-specific rate limit handling
    - Predictive throttling based on usage patterns
    - Adaptive backoff for different API endpoints
    - Per-repository rate limiting
    """
    
    def __init__(
        self,
        max_calls_per_hour: int = 4000,
        max_calls_per_minute: int = 60,
        burst_allowance: int = 10
    ):
        """Initialize rate limiter with configurable limits."""
        self.max_calls_per_hour = max_calls_per_hour
        self.max_calls_per_minute = max_calls_per_minute
        self.burst_allowance = burst_allowance
        
        # Rate limiting windows
        self.hourly_window = RateLimitWindow(
            requests=deque(),
            window_size_seconds=3600,
            max_requests=max_calls_per_hour
        )
        
        self.minute_window = RateLimitWindow(
            requests=deque(),
            window_size_seconds=60,
            max_requests=max_calls_per_minute
        )
        
        self.burst_window = RateLimitWindow(
            requests=deque(),
            window_size_seconds=10,
            max_requests=burst_allowance
        )
        
        # GitHub API rate limit tracking
        self.github_rate_limit: Optional[Dict] = None
        self.last_github_check = 0
        
        # Adaptive throttling
        self.throttle_factor = 1.0
        self.consecutive_rate_limits = 0
        self.last_rate_limit_time = 0
        
        # Per-endpoint tracking
        self.endpoint_windows: Dict[str, RateLimitWindow] = {}
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'rate_limited_requests': 0,
            'throttled_requests': 0,
            'average_wait_time': 0.0,
            'total_wait_time': 0.0
        }
        
        logger.info(
            "Rate limiter initialized",
            max_calls_per_hour=max_calls_per_hour,
            max_calls_per_minute=max_calls_per_minute,
            burst_allowance=burst_allowance
        )
    
    async def can_make_request(
        self,
        endpoint: Optional[str] = None,
        repository: Optional[str] = None
    ) -> bool:
        """
        Check if we can make a request without exceeding rate limits.
        
        Args:
            endpoint: Specific API endpoint for per-endpoint tracking
            repository: Repository identifier for per-repo tracking
        """
        # Check all rate limiting windows
        windows_to_check = [
            self.hourly_window,
            self.minute_window,
            self.burst_window
        ]
        
        # Add endpoint-specific window if exists
        if endpoint and endpoint in self.endpoint_windows:
            windows_to_check.append(self.endpoint_windows[endpoint])
        
        # Check GitHub API rate limit if available
        if self.github_rate_limit:
            github_remaining = self.github_rate_limit.get('remaining', 1000)
            if github_remaining < 10:  # Conservative threshold
                logger.warning(
                    "GitHub API rate limit nearly exhausted",
                    remaining=github_remaining,
                    reset_time=self.github_rate_limit.get('reset_time')
                )
                return False
        
        # Apply adaptive throttling
        if self.throttle_factor > 1.0:
            # Reduce effective limits when throttling
            effective_limits = [
                w.max_requests / self.throttle_factor for w in windows_to_check
            ]
            
            for window, effective_limit in zip(windows_to_check, effective_limits):
                if window.current_count() >= effective_limit:
                    return False
        else:
            # Normal rate limit checking
            for window in windows_to_check:
                if not window.can_make_request():
                    return False
        
        return True
    
    async def wait_for_slot(
        self,
        endpoint: Optional[str] = None,
        repository: Optional[str] = None,
        max_wait_seconds: float = 300.0
    ) -> bool:
        """
        Wait for a rate limit slot to become available.
        
        Returns:
            True if slot became available, False if max wait time exceeded
        """
        start_wait = time.time()
        
        while not await self.can_make_request(endpoint, repository):
            # Calculate wait time
            wait_times = [
                self.hourly_window.time_until_slot_available(),
                self.minute_window.time_until_slot_available(),
                self.burst_window.time_until_slot_available()
            ]
            
            # Add GitHub API reset time if needed
            if self.github_rate_limit:
                github_remaining = self.github_rate_limit.get('remaining', 1000)
                if github_remaining < 10:
                    reset_time = self.github_rate_limit.get('reset_time', time.time() + 3600)
                    github_wait = max(0, reset_time - time.time())
                    wait_times.append(github_wait)
            
            wait_time = min(max(wait_times), 60.0)  # Cap individual waits at 60 seconds
            
            # Check if we would exceed max wait time
            if time.time() - start_wait + wait_time > max_wait_seconds:
                logger.warning(
                    "Rate limit wait time would exceed maximum",
                    total_wait_time=time.time() - start_wait,
                    max_wait_seconds=max_wait_seconds
                )
                return False
            
            if wait_time > 0:
                logger.info(f"Rate limited, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)
                
                # Update statistics
                self.stats['rate_limited_requests'] += 1
                self.stats['total_wait_time'] += wait_time
        
        total_wait = time.time() - start_wait
        if total_wait > 0:
            self.stats['average_wait_time'] = (
                (self.stats['average_wait_time'] * self.stats['rate_limited_requests'] + total_wait) /
                (self.stats['rate_limited_requests'] + 1)
            )
        
        return True
    
    async def record_request(
        self,
        endpoint: Optional[str] = None,
        repository: Optional[str] = None,
        success: bool = True
    ) -> None:
        """Record a request in all applicable windows."""
        current_time = time.time()
        
        # Record in main windows
        self.hourly_window.add_request(current_time)
        self.minute_window.add_request(current_time)
        self.burst_window.add_request(current_time)
        
        # Record in endpoint-specific window
        if endpoint:
            if endpoint not in self.endpoint_windows:
                # Create endpoint-specific window with conservative limits
                self.endpoint_windows[endpoint] = RateLimitWindow(
                    requests=deque(),
                    window_size_seconds=60,
                    max_requests=30  # Conservative per-endpoint limit
                )
            self.endpoint_windows[endpoint].add_request(current_time)
        
        # Update statistics
        self.stats['total_requests'] += 1
        
        # Update adaptive throttling based on success
        if not success and 'rate limit' in str(success).lower():
            self._handle_rate_limit_exceeded()
        else:
            self._handle_successful_request()
    
    def update_github_rate_limit(
        self,
        limit: int,
        remaining: int,
        reset_timestamp: int,
        used: int
    ) -> None:
        """Update GitHub API rate limit information."""
        self.github_rate_limit = {
            'limit': limit,
            'remaining': remaining,
            'reset_timestamp': reset_timestamp,
            'reset_time': reset_timestamp,
            'used': used,
            'updated_at': time.time()
        }
        
        # Adjust throttling based on rate limit status
        usage_percentage = used / limit if limit > 0 else 0
        
        if usage_percentage > 0.9:  # 90% used
            self.throttle_factor = max(self.throttle_factor, 2.0)
        elif usage_percentage > 0.8:  # 80% used
            self.throttle_factor = max(self.throttle_factor, 1.5)
        elif usage_percentage < 0.5:  # Less than 50% used
            self.throttle_factor = max(1.0, self.throttle_factor * 0.9)
        
        logger.debug(
            "GitHub rate limit updated",
            remaining=remaining,
            limit=limit,
            usage_percentage=usage_percentage,
            throttle_factor=self.throttle_factor
        )
    
    def _handle_rate_limit_exceeded(self) -> None:
        """Handle rate limit exceeded event."""
        self.consecutive_rate_limits += 1
        self.last_rate_limit_time = time.time()
        
        # Increase throttling exponentially
        self.throttle_factor = min(10.0, self.throttle_factor * 1.5)
        
        logger.warning(
            "Rate limit exceeded",
            consecutive_rate_limits=self.consecutive_rate_limits,
            throttle_factor=self.throttle_factor
        )
    
    def _handle_successful_request(self) -> None:
        """Handle successful request event."""
        # Gradually reduce throttling after successful requests
        if self.consecutive_rate_limits > 0:
            time_since_last_limit = time.time() - self.last_rate_limit_time
            
            # Reset consecutive count if enough time has passed
            if time_since_last_limit > 300:  # 5 minutes
                self.consecutive_rate_limits = 0
                self.throttle_factor = max(1.0, self.throttle_factor * 0.95)
    
    def get_status(self) -> Dict:
        """Get current rate limiter status."""
        current_time = time.time()
        
        status = {
            'current_usage': {
                'hourly': {
                    'current': self.hourly_window.current_count(),
                    'limit': self.hourly_window.max_requests,
                    'percentage': (self.hourly_window.current_count() / self.hourly_window.max_requests) * 100
                },
                'minute': {
                    'current': self.minute_window.current_count(),
                    'limit': self.minute_window.max_requests,
                    'percentage': (self.minute_window.current_count() / self.minute_window.max_requests) * 100
                },
                'burst': {
                    'current': self.burst_window.current_count(),
                    'limit': self.burst_window.max_requests,
                    'percentage': (self.burst_window.current_count() / self.burst_window.max_requests) * 100
                }
            },
            'github_api': self.github_rate_limit,
            'adaptive_throttling': {
                'throttle_factor': self.throttle_factor,
                'consecutive_rate_limits': self.consecutive_rate_limits,
                'last_rate_limit_time': self.last_rate_limit_time
            },
            'statistics': self.stats,
            'endpoint_windows': {
                endpoint: {
                    'current': window.current_count(),
                    'limit': window.max_requests
                }
                for endpoint, window in self.endpoint_windows.items()
            }
        }
        
        return status
    
    def reset_statistics(self) -> None:
        """Reset rate limiting statistics."""
        self.stats = {
            'total_requests': 0,
            'rate_limited_requests': 0,
            'throttled_requests': 0,
            'average_wait_time': 0.0,
            'total_wait_time': 0.0
        }
        logger.info("Rate limiting statistics reset")
    
    def set_conservative_mode(self, enabled: bool = True) -> None:
        """Enable or disable conservative rate limiting mode."""
        if enabled:
            self.throttle_factor = max(self.throttle_factor, 2.0)
            logger.info("Conservative rate limiting mode enabled")
        else:
            self.throttle_factor = 1.0
            self.consecutive_rate_limits = 0
            logger.info("Conservative rate limiting mode disabled")
    
    def get_predicted_wait_time(
        self,
        endpoint: Optional[str] = None
    ) -> float:
        """Predict wait time for next request based on current usage."""
        if await self.can_make_request(endpoint):
            return 0.0
        
        wait_times = [
            self.hourly_window.time_until_slot_available(),
            self.minute_window.time_until_slot_available(),
            self.burst_window.time_until_slot_available()
        ]
        
        if endpoint and endpoint in self.endpoint_windows:
            wait_times.append(
                self.endpoint_windows[endpoint].time_until_slot_available()
            )
        
        return max(wait_times)
    
    async def cleanup(self) -> None:
        """Cleanup resources and log final statistics."""
        logger.info(
            "Rate limiter cleanup",
            final_statistics=self.stats,
            throttle_factor=self.throttle_factor
        )