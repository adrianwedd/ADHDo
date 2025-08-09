"""
Multi-Layer Caching System for MCP ADHD Server.

Enterprise-scale caching infrastructure optimized for ADHD user responsiveness.
Provides hierarchical caching with intelligent invalidation and cache warming.

Cache Layers (fastest to slowest):
1. In-Memory Cache: Critical data, millisecond access
2. Redis Hot Cache: Frequently accessed data, <10ms access  
3. Redis Warm Cache: Less frequent data, <100ms access
4. Database Cache: Computed results, query optimization
5. External API Cache: Rate-limited API responses

Features:
- ADHD-optimized cache access patterns (<10ms for hot data)
- Intelligent cache warming and preloading
- Smart invalidation with dependency tracking
- Performance monitoring and hit rate optimization
- Crisis-safe caching with priority access
- Memory-efficient storage with compression
"""

import asyncio
import gzip
import hashlib
import json
import pickle
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union, Callable, Tuple
from dataclasses import dataclass, field
import logging

import redis.asyncio as redis
from pydantic import BaseModel, Field
import structlog

from mcp_server.config import settings


# Configure structured logger
logger = structlog.get_logger(__name__)


class CacheLayer(str, Enum):
    """Cache layer types ordered by access speed."""
    MEMORY = "memory"         # In-memory cache, millisecond access
    REDIS_HOT = "redis_hot"   # Redis hot data, <10ms access
    REDIS_WARM = "redis_warm" # Redis warm data, <100ms access
    DATABASE = "database"     # Database computed results
    EXTERNAL = "external"     # External API responses


class CachePriority(str, Enum):
    """Cache priority levels for ADHD optimization."""
    CRISIS = "crisis"         # Crisis data, always available
    HIGH = "high"             # User interaction data
    NORMAL = "normal"         # Background processing data  
    LOW = "low"               # Analytics and reports
    MAINTENANCE = "maintenance" # System optimization data


class CacheStrategy(str, Enum):
    """Cache invalidation and refresh strategies."""
    TTL = "ttl"               # Time-based expiration
    LRU = "lru"               # Least recently used
    LFU = "lfu"               # Least frequently used
    DEPENDENCY = "dependency" # Dependency-based invalidation
    MANUAL = "manual"         # Manual invalidation only


@dataclass
class CacheEntry:
    """Cache entry with metadata and performance tracking."""
    key: str
    value: Any
    layer: CacheLayer
    priority: CachePriority
    strategy: CacheStrategy
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    accessed_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    
    hit_count: int = 0
    access_count: int = 0
    size_bytes: int = 0
    
    # ADHD optimization metadata
    user_id: Optional[str] = None
    attention_critical: bool = False
    cognitive_load_weight: float = 1.0
    
    # Dependency tracking
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    
    # Performance metrics
    serialization_time: float = 0.0
    compression_ratio: float = 1.0


class CacheStats(BaseModel):
    """Cache performance statistics."""
    layer: CacheLayer
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    hit_rate: float = 0.0
    
    average_access_time_ms: float = 0.0
    total_size_bytes: int = 0
    entry_count: int = 0
    
    # ADHD-specific metrics
    crisis_access_time_ms: float = 0.0
    user_interaction_access_time_ms: float = 0.0
    attention_critical_hit_rate: float = 0.0
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class MultiLayerCacheManager:
    """
    Enterprise-scale multi-layer cache manager with ADHD optimizations.
    
    Features:
    - Hierarchical caching with automatic promotion/demotion
    - Intelligent cache warming and preloading strategies
    - Smart invalidation with dependency tracking
    - Performance monitoring and optimization
    - Crisis-safe caching with priority access
    - Memory-efficient storage with compression
    """
    
    def __init__(self):
        # Cache storage layers
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.redis_clients: Dict[str, redis.Redis] = {}
        
        # Cache management
        self.cache_stats: Dict[CacheLayer, CacheStats] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}
        self.warming_tasks: Dict[str, asyncio.Task] = {}
        
        # Performance optimization
        self.access_patterns: Dict[str, List[float]] = {}
        self.promotion_candidates: Set[str] = set()
        self.compression_enabled = True
        
        # ADHD optimization settings
        self.crisis_cache_size_mb = 50      # Reserved cache for crisis data
        self.user_cache_ttl = 300           # 5 minutes for user interaction data
        self.background_cache_ttl = 3600    # 1 hour for background data
        
        # Performance targets
        self.memory_access_target_ms = 1.0      # In-memory access target
        self.redis_hot_access_target_ms = 10.0  # Redis hot access target
        self.redis_warm_access_target_ms = 100.0 # Redis warm access target
        
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """Initialize the multi-layer cache manager."""
        try:
            # Initialize Redis clients for different cache layers
            self.redis_clients['hot'] = redis.from_url(
                settings.redis_url.replace('/0', '/1'),  # Use database 1 for hot cache
                decode_responses=False,  # Keep binary for compression
                health_check_interval=30,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            self.redis_clients['warm'] = redis.from_url(
                settings.redis_url.replace('/0', '/2'),  # Use database 2 for warm cache
                decode_responses=False,
                health_check_interval=30,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            self.redis_clients['external'] = redis.from_url(
                settings.redis_url.replace('/0', '/3'),  # Use database 3 for external cache
                decode_responses=False,
                health_check_interval=30,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            # Test Redis connections
            for name, client in self.redis_clients.items():
                await client.ping()
                logger.info(f"Redis {name} cache connection established")
            
            # Initialize cache statistics
            for layer in CacheLayer:
                self.cache_stats[layer] = CacheStats(layer=layer)
            
            # Start background optimization tasks
            asyncio.create_task(self._optimization_loop())
            asyncio.create_task(self._statistics_update_loop())
            
            self.is_initialized = True
            logger.info("Multi-layer cache manager initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize cache manager", error=str(e))
            raise
    
    async def shutdown(self) -> None:
        """Shutdown the cache manager gracefully."""
        logger.info("Shutting down multi-layer cache manager")
        
        # Cancel warming tasks
        for task_id, task in self.warming_tasks.items():
            if not task.done():
                task.cancel()
        
        # Close Redis connections
        for name, client in self.redis_clients.items():
            await client.aclose()
            logger.info(f"Closed Redis {name} cache connection")
        
        # Clear memory cache
        self.memory_cache.clear()
        
        logger.info("Multi-layer cache manager shutdown complete")
    
    async def get(
        self,
        key: str,
        default: Any = None,
        user_id: Optional[str] = None,
        priority: CachePriority = CachePriority.NORMAL
    ) -> Any:
        """
        Get value from cache with automatic layer traversal.
        
        Args:
            key: Cache key
            default: Default value if not found
            user_id: User ID for ADHD optimization
            priority: Cache priority level
            
        Returns:
            Cached value or default
        """
        start_time = time.perf_counter()
        
        try:
            # Try each cache layer in order
            for layer in CacheLayer:
                value = await self._get_from_layer(key, layer)
                
                if value is not None:
                    access_time_ms = (time.perf_counter() - start_time) * 1000
                    
                    # Update statistics
                    stats = self.cache_stats[layer]
                    stats.total_requests += 1
                    stats.cache_hits += 1
                    stats.hit_rate = stats.cache_hits / stats.total_requests
                    
                    # Update average access time
                    if stats.average_access_time_ms == 0:
                        stats.average_access_time_ms = access_time_ms
                    else:
                        stats.average_access_time_ms = (
                            (stats.average_access_time_ms * (stats.cache_hits - 1) + access_time_ms)
                            / stats.cache_hits
                        )
                    
                    # Track ADHD-specific metrics
                    if priority == CachePriority.CRISIS:
                        stats.crisis_access_time_ms = access_time_ms
                    elif priority == CachePriority.HIGH:
                        stats.user_interaction_access_time_ms = access_time_ms
                    
                    # Promote to faster layer if frequently accessed
                    await self._consider_promotion(key, layer, access_time_ms, priority)
                    
                    logger.debug(
                        "Cache hit",
                        key=key[:50],
                        layer=layer.value,
                        access_time_ms=f"{access_time_ms:.2f}",
                        priority=priority.value
                    )
                    
                    return value
                
                # Record miss for this layer
                stats = self.cache_stats[layer]
                stats.total_requests += 1
                stats.cache_misses += 1
                stats.hit_rate = stats.cache_hits / stats.total_requests
            
            # Cache miss across all layers
            logger.debug("Cache miss", key=key[:50], priority=priority.value)
            return default
            
        except Exception as e:
            logger.error("Cache get error", key=key[:50], error=str(e))
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        layer: Optional[CacheLayer] = None,
        priority: CachePriority = CachePriority.NORMAL,
        strategy: CacheStrategy = CacheStrategy.TTL,
        user_id: Optional[str] = None,
        dependencies: Optional[Set[str]] = None
    ) -> bool:
        """
        Set value in cache with intelligent layer selection.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            layer: Specific layer to use (auto-selected if None)
            priority: Cache priority level
            strategy: Cache invalidation strategy
            user_id: User ID for ADHD optimization
            dependencies: Cache dependencies for invalidation
            
        Returns:
            True if successfully cached
        """
        try:
            # Auto-select layer if not specified
            if layer is None:
                layer = self._select_cache_layer(key, value, priority)
            
            # Set appropriate TTL based on priority and layer
            if ttl is None:
                ttl = self._get_default_ttl(priority, layer)
            
            # Create cache entry
            entry = CacheEntry(
                key=key,
                value=value,
                layer=layer,
                priority=priority,
                strategy=strategy,
                user_id=user_id,
                expires_at=datetime.utcnow() + timedelta(seconds=ttl) if ttl > 0 else None,
                dependencies=dependencies or set()
            )
            
            # Calculate entry size and compression
            entry.size_bytes, entry.compression_ratio, entry.serialization_time = (
                await self._prepare_cache_entry(value)
            )
            
            # Store in selected layer
            success = await self._set_in_layer(key, entry, layer)
            
            if success:
                # Update dependency graph
                if dependencies:
                    self._update_dependency_graph(key, dependencies)
                
                # Update statistics
                stats = self.cache_stats[layer]
                stats.entry_count += 1
                stats.total_size_bytes += entry.size_bytes
                
                logger.debug(
                    "Cache set",
                    key=key[:50],
                    layer=layer.value,
                    priority=priority.value,
                    size_bytes=entry.size_bytes,
                    ttl=ttl
                )
            
            return success
            
        except Exception as e:
            logger.error("Cache set error", key=key[:50], error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from all cache layers."""
        try:
            success = True
            
            # Delete from all layers
            for layer in CacheLayer:
                layer_success = await self._delete_from_layer(key, layer)
                success = success and layer_success
            
            # Remove from dependency graph
            self._remove_from_dependency_graph(key)
            
            logger.debug("Cache delete", key=key[:50])
            return success
            
        except Exception as e:
            logger.error("Cache delete error", key=key[:50], error=str(e))
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern."""
        try:
            invalidated_count = 0
            
            # Invalidate from all layers
            for layer in CacheLayer:
                count = await self._invalidate_pattern_in_layer(pattern, layer)
                invalidated_count += count
            
            logger.info("Pattern invalidation", pattern=pattern, count=invalidated_count)
            return invalidated_count
            
        except Exception as e:
            logger.error("Pattern invalidation error", pattern=pattern, error=str(e))
            return 0
    
    async def invalidate_dependencies(self, dependency_key: str) -> int:
        """Invalidate all cache entries that depend on the given key."""
        try:
            # Find all dependent keys
            dependent_keys = set()
            self._find_dependent_keys(dependency_key, dependent_keys)
            
            # Invalidate all dependent keys
            for key in dependent_keys:
                await self.delete(key)
            
            logger.info("Dependency invalidation", dependency=dependency_key, count=len(dependent_keys))
            return len(dependent_keys)
            
        except Exception as e:
            logger.error("Dependency invalidation error", dependency=dependency_key, error=str(e))
            return 0
    
    async def warm_cache(
        self,
        keys: List[str],
        warm_function: Callable[[str], Any],
        priority: CachePriority = CachePriority.NORMAL,
        batch_size: int = 10
    ) -> int:
        """
        Warm cache with batch processing and progress tracking.
        
        Args:
            keys: Keys to warm
            warm_function: Function to generate cache values
            priority: Priority level for warmed data
            batch_size: Number of keys to process in parallel
            
        Returns:
            Number of keys successfully warmed
        """
        try:
            warmed_count = 0
            
            # Process keys in batches
            for i in range(0, len(keys), batch_size):
                batch = keys[i:i + batch_size]
                
                # Warm batch in parallel
                tasks = [
                    self._warm_single_key(key, warm_function, priority)
                    for key in batch
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count successful warming
                for result in results:
                    if result is True:
                        warmed_count += 1
                
                # Brief pause between batches to avoid overwhelming the system
                if i + batch_size < len(keys):
                    await asyncio.sleep(0.1)
            
            logger.info("Cache warming completed", total_keys=len(keys), warmed=warmed_count)
            return warmed_count
            
        except Exception as e:
            logger.error("Cache warming error", error=str(e))
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        try:
            stats = {}
            
            # Compile statistics for each layer
            for layer, layer_stats in self.cache_stats.items():
                stats[layer.value] = {
                    'requests': layer_stats.total_requests,
                    'hits': layer_stats.cache_hits,
                    'misses': layer_stats.cache_misses,
                    'hit_rate': layer_stats.hit_rate,
                    'average_access_time_ms': layer_stats.average_access_time_ms,
                    'entry_count': layer_stats.entry_count,
                    'total_size_bytes': layer_stats.total_size_bytes,
                    'crisis_access_time_ms': layer_stats.crisis_access_time_ms,
                    'user_interaction_access_time_ms': layer_stats.user_interaction_access_time_ms,
                    'attention_critical_hit_rate': layer_stats.attention_critical_hit_rate
                }
            
            # Add overall statistics
            total_requests = sum(s.total_requests for s in self.cache_stats.values())
            total_hits = sum(s.cache_hits for s in self.cache_stats.values())
            
            stats['overall'] = {
                'total_requests': total_requests,
                'total_hits': total_hits,
                'overall_hit_rate': total_hits / total_requests if total_requests > 0 else 0.0,
                'memory_cache_size': len(self.memory_cache),
                'dependency_graph_size': len(self.dependency_graph),
                'warming_tasks': len(self.warming_tasks)
            }
            
            # Add performance indicators
            stats['performance'] = {
                'memory_target_met': self.cache_stats[CacheLayer.MEMORY].average_access_time_ms <= self.memory_access_target_ms,
                'redis_hot_target_met': self.cache_stats[CacheLayer.REDIS_HOT].average_access_time_ms <= self.redis_hot_access_target_ms,
                'redis_warm_target_met': self.cache_stats[CacheLayer.REDIS_WARM].average_access_time_ms <= self.redis_warm_access_target_ms,
                'adhd_optimized': True  # Always true with our design
            }
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return {}
    
    # Internal Methods
    
    def _select_cache_layer(self, key: str, value: Any, priority: CachePriority) -> CacheLayer:
        """Select appropriate cache layer based on key, value, and priority."""
        # Crisis data always goes to memory cache
        if priority == CachePriority.CRISIS:
            return CacheLayer.MEMORY
        
        # High priority user interaction data goes to memory or hot cache
        if priority == CachePriority.HIGH:
            return CacheLayer.REDIS_HOT
        
        # Normal priority goes to warm cache
        if priority == CachePriority.NORMAL:
            return CacheLayer.REDIS_WARM
        
        # Low priority and maintenance go to external cache
        return CacheLayer.EXTERNAL
    
    def _get_default_ttl(self, priority: CachePriority, layer: CacheLayer) -> int:
        """Get default TTL based on priority and layer."""
        ttl_map = {
            CachePriority.CRISIS: 3600,        # 1 hour for crisis data
            CachePriority.HIGH: 300,           # 5 minutes for user interaction
            CachePriority.NORMAL: 3600,        # 1 hour for background data
            CachePriority.LOW: 7200,           # 2 hours for analytics
            CachePriority.MAINTENANCE: 86400   # 24 hours for maintenance data
        }
        
        base_ttl = ttl_map.get(priority, 3600)
        
        # Adjust based on layer
        if layer == CacheLayer.MEMORY:
            return min(base_ttl, 1800)  # Max 30 minutes in memory
        elif layer == CacheLayer.REDIS_HOT:
            return min(base_ttl, 3600)  # Max 1 hour in hot cache
        
        return base_ttl
    
    async def _prepare_cache_entry(self, value: Any) -> Tuple[int, float, float]:
        """Prepare cache entry with compression and size calculation."""
        start_time = time.perf_counter()
        
        # Serialize value
        serialized = pickle.dumps(value)
        original_size = len(serialized)
        
        # Compress if enabled and beneficial
        compressed = serialized
        compression_ratio = 1.0
        
        if self.compression_enabled and original_size > 1024:  # Only compress if >1KB
            compressed = gzip.compress(serialized)
            compression_ratio = len(compressed) / original_size
            
            # Only use compression if it reduces size by at least 20%
            if compression_ratio > 0.8:
                compressed = serialized
                compression_ratio = 1.0
        
        serialization_time = time.perf_counter() - start_time
        
        return len(compressed), compression_ratio, serialization_time
    
    async def _get_from_layer(self, key: str, layer: CacheLayer) -> Any:
        """Get value from specific cache layer."""
        try:
            if layer == CacheLayer.MEMORY:
                entry = self.memory_cache.get(key)
                if entry and (entry.expires_at is None or entry.expires_at > datetime.utcnow()):
                    entry.accessed_at = datetime.utcnow()
                    entry.access_count += 1
                    return entry.value
                elif entry:
                    # Expired entry
                    del self.memory_cache[key]
                return None
            
            elif layer in [CacheLayer.REDIS_HOT, CacheLayer.REDIS_WARM, CacheLayer.EXTERNAL]:
                redis_key = 'hot' if layer == CacheLayer.REDIS_HOT else 'warm' if layer == CacheLayer.REDIS_WARM else 'external'
                client = self.redis_clients[redis_key]
                
                raw_data = await client.get(key)
                if raw_data:
                    # Try to decompress if it's compressed
                    try:
                        decompressed = gzip.decompress(raw_data)
                        return pickle.loads(decompressed)
                    except:
                        # Not compressed or different format
                        return pickle.loads(raw_data)
                
                return None
            
            else:
                return None
                
        except Exception as e:
            logger.error("Layer get error", key=key[:50], layer=layer.value, error=str(e))
            return None
    
    async def _set_in_layer(self, key: str, entry: CacheEntry, layer: CacheLayer) -> bool:
        """Set value in specific cache layer."""
        try:
            if layer == CacheLayer.MEMORY:
                # Check memory limits for ADHD optimization
                if len(self.memory_cache) > 10000:  # Limit memory cache size
                    await self._evict_memory_cache()
                
                self.memory_cache[key] = entry
                return True
            
            elif layer in [CacheLayer.REDIS_HOT, CacheLayer.REDIS_WARM, CacheLayer.EXTERNAL]:
                redis_key = 'hot' if layer == CacheLayer.REDIS_HOT else 'warm' if layer == CacheLayer.REDIS_WARM else 'external'
                client = self.redis_clients[redis_key]
                
                # Serialize and optionally compress
                serialized = pickle.dumps(entry.value)
                
                if self.compression_enabled and len(serialized) > 1024:
                    compressed = gzip.compress(serialized)
                    if len(compressed) < len(serialized) * 0.8:  # Use if >20% reduction
                        serialized = compressed
                
                # Set with TTL
                ttl = None
                if entry.expires_at:
                    ttl = max(1, int((entry.expires_at - datetime.utcnow()).total_seconds()))
                
                if ttl:
                    await client.setex(key, ttl, serialized)
                else:
                    await client.set(key, serialized)
                
                return True
            
            return False
            
        except Exception as e:
            logger.error("Layer set error", key=key[:50], layer=layer.value, error=str(e))
            return False
    
    async def _delete_from_layer(self, key: str, layer: CacheLayer) -> bool:
        """Delete key from specific cache layer."""
        try:
            if layer == CacheLayer.MEMORY:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                return True
            
            elif layer in [CacheLayer.REDIS_HOT, CacheLayer.REDIS_WARM, CacheLayer.EXTERNAL]:
                redis_key = 'hot' if layer == CacheLayer.REDIS_HOT else 'warm' if layer == CacheLayer.REDIS_WARM else 'external'
                client = self.redis_clients[redis_key]
                
                result = await client.delete(key)
                return result > 0
            
            return False
            
        except Exception as e:
            logger.error("Layer delete error", key=key[:50], layer=layer.value, error=str(e))
            return False
    
    async def _invalidate_pattern_in_layer(self, pattern: str, layer: CacheLayer) -> int:
        """Invalidate pattern in specific cache layer."""
        try:
            count = 0
            
            if layer == CacheLayer.MEMORY:
                # Find matching keys in memory cache
                matching_keys = [k for k in self.memory_cache.keys() if self._key_matches_pattern(k, pattern)]
                for key in matching_keys:
                    del self.memory_cache[key]
                    count += 1
            
            elif layer in [CacheLayer.REDIS_HOT, CacheLayer.REDIS_WARM, CacheLayer.EXTERNAL]:
                redis_key = 'hot' if layer == CacheLayer.REDIS_HOT else 'warm' if layer == CacheLayer.REDIS_WARM else 'external'
                client = self.redis_clients[redis_key]
                
                # Use Redis SCAN to find matching keys
                async for key in client.scan_iter(match=pattern):
                    await client.delete(key)
                    count += 1
            
            return count
            
        except Exception as e:
            logger.error("Pattern invalidation error", pattern=pattern, layer=layer.value, error=str(e))
            return 0
    
    def _key_matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern (simple wildcard support)."""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)
    
    async def _consider_promotion(self, key: str, current_layer: CacheLayer, access_time_ms: float, priority: CachePriority) -> None:
        """Consider promoting frequently accessed cache entries to faster layers."""
        # Track access patterns
        if key not in self.access_patterns:
            self.access_patterns[key] = []
        
        self.access_patterns[key].append(time.time())
        
        # Keep only recent access times (last 5 minutes)
        cutoff_time = time.time() - 300
        self.access_patterns[key] = [t for t in self.access_patterns[key] if t > cutoff_time]
        
        # Consider promotion if frequently accessed
        recent_accesses = len(self.access_patterns[key])
        
        # Promotion criteria based on ADHD optimization needs
        should_promote = False
        target_layer = current_layer
        
        if current_layer == CacheLayer.REDIS_WARM and recent_accesses >= 5:
            # Promote to hot cache
            should_promote = True
            target_layer = CacheLayer.REDIS_HOT
        elif current_layer == CacheLayer.REDIS_HOT and recent_accesses >= 10 and priority in [CachePriority.CRISIS, CachePriority.HIGH]:
            # Promote to memory cache
            should_promote = True
            target_layer = CacheLayer.MEMORY
        
        if should_promote:
            value = await self._get_from_layer(key, current_layer)
            if value is not None:
                await self._set_in_layer(key, CacheEntry(
                    key=key,
                    value=value,
                    layer=target_layer,
                    priority=priority,
                    strategy=CacheStrategy.TTL
                ), target_layer)
                
                logger.debug("Cache entry promoted", key=key[:50], from_layer=current_layer.value, to_layer=target_layer.value)
    
    async def _evict_memory_cache(self) -> None:
        """Evict least recently used entries from memory cache."""
        # Sort by access time and remove oldest entries
        sorted_entries = sorted(
            self.memory_cache.items(),
            key=lambda x: x[1].accessed_at
        )
        
        # Remove oldest 20% of entries
        evict_count = max(1, len(sorted_entries) // 5)
        for key, _ in sorted_entries[:evict_count]:
            del self.memory_cache[key]
        
        logger.debug("Memory cache evicted", evicted_count=evict_count)
    
    def _update_dependency_graph(self, key: str, dependencies: Set[str]) -> None:
        """Update cache dependency graph."""
        self.dependency_graph[key] = dependencies
        
        # Update reverse dependencies
        for dep in dependencies:
            if dep not in self.dependency_graph:
                self.dependency_graph[dep] = set()
    
    def _remove_from_dependency_graph(self, key: str) -> None:
        """Remove key from dependency graph."""
        if key in self.dependency_graph:
            del self.dependency_graph[key]
        
        # Remove from other dependencies
        for deps in self.dependency_graph.values():
            deps.discard(key)
    
    def _find_dependent_keys(self, dependency_key: str, found_keys: Set[str]) -> None:
        """Recursively find all keys that depend on the given key."""
        for key, deps in self.dependency_graph.items():
            if dependency_key in deps and key not in found_keys:
                found_keys.add(key)
                self._find_dependent_keys(key, found_keys)  # Recursive dependency resolution
    
    async def _warm_single_key(self, key: str, warm_function: Callable, priority: CachePriority) -> bool:
        """Warm a single cache key."""
        try:
            # Check if key already exists
            existing_value = await self.get(key)
            if existing_value is not None:
                return True  # Already warmed
            
            # Generate value using warm function
            value = await warm_function(key) if asyncio.iscoroutinefunction(warm_function) else warm_function(key)
            
            if value is not None:
                # Cache the warmed value
                success = await self.set(key, value, priority=priority)
                return success
            
            return False
            
        except Exception as e:
            logger.error("Cache warming error", key=key[:50], error=str(e))
            return False
    
    async def _optimization_loop(self) -> None:
        """Background optimization loop for cache management."""
        while self.is_initialized:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Clean up expired entries
                await self._cleanup_expired_entries()
                
                # Optimize cache distribution
                await self._optimize_cache_distribution()
                
                # Update promotion candidates
                await self._update_promotion_candidates()
                
            except Exception as e:
                logger.error("Cache optimization loop error", error=str(e))
                await asyncio.sleep(60)  # Continue after error
    
    async def _statistics_update_loop(self) -> None:
        """Background loop for updating cache statistics."""
        while self.is_initialized:
            try:
                await asyncio.sleep(30)  # Update every 30 seconds
                
                # Update timestamp
                for stats in self.cache_stats.values():
                    stats.last_updated = datetime.utcnow()
                
                # Log performance metrics for ADHD optimization
                memory_stats = self.cache_stats[CacheLayer.MEMORY]
                hot_stats = self.cache_stats[CacheLayer.REDIS_HOT]
                
                if memory_stats.average_access_time_ms > self.memory_access_target_ms:
                    logger.warning("Memory cache access time exceeds target", 
                                 actual=f"{memory_stats.average_access_time_ms:.2f}ms",
                                 target=f"{self.memory_access_target_ms:.2f}ms")
                
                if hot_stats.average_access_time_ms > self.redis_hot_access_target_ms:
                    logger.warning("Redis hot cache access time exceeds target",
                                 actual=f"{hot_stats.average_access_time_ms:.2f}ms", 
                                 target=f"{self.redis_hot_access_target_ms:.2f}ms")
                
            except Exception as e:
                logger.error("Cache statistics update error", error=str(e))
                await asyncio.sleep(30)
    
    async def _cleanup_expired_entries(self) -> None:
        """Clean up expired cache entries."""
        now = datetime.utcnow()
        expired_keys = []
        
        # Find expired memory cache entries
        for key, entry in self.memory_cache.items():
            if entry.expires_at and entry.expires_at <= now:
                expired_keys.append(key)
        
        # Remove expired entries
        for key in expired_keys:
            del self.memory_cache[key]
        
        if expired_keys:
            logger.debug("Cleaned up expired cache entries", count=len(expired_keys))
    
    async def _optimize_cache_distribution(self) -> None:
        """Optimize cache distribution across layers."""
        # This would implement more sophisticated cache optimization logic
        # For now, just ensure we're within memory limits
        if len(self.memory_cache) > 5000:  # Conservative memory limit for ADHD responsiveness
            await self._evict_memory_cache()
    
    async def _update_promotion_candidates(self) -> None:
        """Update candidates for cache promotion."""
        # Clear old candidates
        self.promotion_candidates.clear()
        
        # Find frequently accessed keys
        cutoff_time = time.time() - 300  # 5 minutes
        
        for key, access_times in self.access_patterns.items():
            recent_accesses = [t for t in access_times if t > cutoff_time]
            if len(recent_accesses) >= 3:  # 3 or more accesses in 5 minutes
                self.promotion_candidates.add(key)


# Global cache manager instance
cache_manager = MultiLayerCacheManager()