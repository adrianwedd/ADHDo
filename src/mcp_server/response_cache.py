"""
High-performance response caching for MCP ADHD Server.

Optimized for ADHD users requiring sub-3 second response times.
Features memory-efficient caching with TTL and size limits.
"""

import time
import hashlib
import json
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass
from collections import OrderedDict
import asyncio
from datetime import datetime, timedelta

import structlog
from mcp_server.performance_config import perf_config


@dataclass
class CacheEntry:
    """Cache entry with TTL and metadata."""
    data: Any
    created_at: float
    ttl: int
    access_count: int = 0
    last_accessed: float = 0
    size_bytes: int = 0


class ADHDResponseCache:
    """
    Memory-efficient response cache optimized for ADHD users.
    
    Features:
    - LRU eviction with TTL
    - Size-aware caching (prevents memory bloat)
    - Fast cache key generation
    - ADHD-optimized cache warming
    - Performance metrics tracking
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'memory_bytes': 0,
            'avg_response_time_ms': 0
        }
        self._lock = asyncio.Lock()
        self.logger = structlog.get_logger(__name__)
    
    def _generate_cache_key(self, endpoint: str, params: Dict = None, user_id: str = None) -> str:
        """Generate fast cache key using hash."""
        key_data = {
            'endpoint': endpoint,
            'params': params or {},
            'user_id': user_id
        }
        
        # Fast JSON serialization for cache key
        key_str = json.dumps(key_data, sort_keys=True, separators=(',', ':'))
        return hashlib.blake2b(key_str.encode(), digest_size=16).hexdigest()
    
    def _estimate_size(self, data: Any) -> int:
        """Estimate memory size of cached data."""
        try:
            if isinstance(data, (str, bytes)):
                return len(data)
            elif isinstance(data, dict):
                return len(json.dumps(data, separators=(',', ':')))
            elif hasattr(data, '__sizeof__'):
                return data.__sizeof__()
            else:
                return len(str(data))
        except Exception:
            return 1024  # Default estimate
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries (non-blocking)."""
        current_time = time.perf_counter()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if current_time - entry.created_at > entry.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._evict_entry(key)
    
    def _evict_entry(self, key: str) -> None:
        """Evict a cache entry."""
        if key in self.cache:
            entry = self.cache.pop(key)
            self.stats['evictions'] += 1
            self.stats['memory_bytes'] -= entry.size_bytes
    
    def _evict_lru(self) -> None:
        """Evict least recently used entries until under max_size."""
        while len(self.cache) >= self.max_size:
            # Pop oldest (LRU) entry
            key, _ = self.cache.popitem(last=False)
            self.stats['evictions'] += 1
    
    async def get(self, cache_key: str) -> Optional[Any]:
        """Get cached response with performance tracking."""
        async with self._lock:
            # Fast cleanup of a few expired entries
            if len(self.cache) > 10:
                self._cleanup_expired()
            
            if cache_key not in self.cache:
                self.stats['misses'] += 1
                return None
            
            entry = self.cache[cache_key]
            current_time = time.perf_counter()
            
            # Check if expired
            if current_time - entry.created_at > entry.ttl:
                self._evict_entry(cache_key)
                self.stats['misses'] += 1
                return None
            
            # Update access tracking
            entry.access_count += 1
            entry.last_accessed = current_time
            
            # Move to end (most recently used)
            self.cache.move_to_end(cache_key)
            
            self.stats['hits'] += 1
            return entry.data
    
    async def set(self, cache_key: str, data: Any, ttl: Optional[int] = None) -> None:
        """Cache response data with memory management."""
        if ttl is None:
            ttl = self.default_ttl
        
        size_bytes = self._estimate_size(data)
        
        # Skip caching if data is too large (>1MB)
        if size_bytes > 1024 * 1024:
            self.logger.warning("Skipping cache for large response", size_mb=size_bytes / (1024*1024))
            return
        
        async with self._lock:
            current_time = time.perf_counter()
            
            # Evict LRU entries if needed
            self._evict_lru()
            
            # Create cache entry
            entry = CacheEntry(
                data=data,
                created_at=current_time,
                ttl=ttl,
                size_bytes=size_bytes
            )
            
            # Remove existing entry if present
            if cache_key in self.cache:
                old_entry = self.cache[cache_key]
                self.stats['memory_bytes'] -= old_entry.size_bytes
            
            # Add new entry
            self.cache[cache_key] = entry
            self.stats['memory_bytes'] += size_bytes
    
    async def invalidate(self, pattern: str = None, user_id: str = None) -> int:
        """Invalidate cache entries by pattern or user."""
        async with self._lock:
            keys_to_remove = []
            
            for key in self.cache:
                should_remove = False
                
                if pattern and pattern in key:
                    should_remove = True
                elif user_id:
                    # Check if this cache entry is for the specific user
                    # This is a simple approach - in production you might want more sophisticated matching
                    if user_id in key:
                        should_remove = True
                
                if should_remove:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self._evict_entry(key)
            
            return len(keys_to_remove)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'hit_rate_percent': round(hit_rate, 2),
            'total_entries': len(self.cache),
            'memory_usage_mb': round(self.stats['memory_bytes'] / (1024*1024), 2),
            'hits': self.stats['hits'],
            'misses': self.stats['misses'], 
            'evictions': self.stats['evictions'],
            'adhd_optimized': hit_rate > 70,  # Good hit rate for ADHD users
            'memory_efficient': self.stats['memory_bytes'] < 50 * 1024 * 1024  # <50MB
        }


# Global cache instance
response_cache = ADHDResponseCache(
    max_size=perf_config.evolution_cache_size,
    default_ttl=perf_config.health_cache_ttl
)


def cache_key_for_endpoint(endpoint: str, **kwargs) -> str:
    """Helper to generate cache keys for endpoints."""
    return response_cache._generate_cache_key(endpoint, kwargs)


async def cached_response(cache_key: str, ttl: int = None):
    """Decorator for caching endpoint responses."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Try to get from cache first
            cached_data = await response_cache.get(cache_key)
            if cached_data is not None:
                return cached_data
            
            # Execute function and cache result
            start_time = time.perf_counter()
            result = await func(*args, **kwargs)
            execution_time = time.perf_counter() - start_time
            
            # Cache the result
            await response_cache.set(cache_key, result, ttl)
            
            # Log slow responses that might affect ADHD users
            if execution_time > 1.0:
                response_cache.logger.warning(
                    "Slow response cached",
                    endpoint=cache_key[:50],
                    execution_time=f"{execution_time:.3f}s",
                    adhd_impact="May need optimization"
                )
            
            return result
        return wrapper
    return decorator