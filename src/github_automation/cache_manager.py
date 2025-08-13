"""
Redis Cache Manager for GitHub Automation System

High-performance caching layer with intelligent cache strategies,
automatic invalidation, and monitoring for optimal performance.
"""

import json
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict

import redis.asyncio as redis
import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    data: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: datetime = None
    cache_key: str = ""
    size_bytes: int = 0


class CacheConfig(BaseModel):
    """Cache configuration settings."""
    redis_url: str = "redis://localhost:6379/0"
    default_ttl_seconds: int = 3600  # 1 hour
    max_memory_mb: int = 512
    key_prefix: str = "github_automation"
    compression_enabled: bool = True
    compression_threshold_bytes: int = 1024
    stats_enabled: bool = True


class CacheManager:
    """
    Enterprise-grade Redis cache manager for GitHub automation.
    
    Features:
    - Intelligent cache invalidation strategies
    - Compression for large objects
    - Cache warming and preloading
    - Performance monitoring and statistics
    - Automatic cleanup and memory management
    """
    
    def __init__(self, config: CacheConfig):
        """Initialize cache manager with configuration."""
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        
        # Cache statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0,
            'total_size_bytes': 0,
            'average_access_time_ms': 0.0,
            'cache_efficiency': 0.0
        }
        
        # Key patterns for different data types
        self.key_patterns = {
            'issue': f"{config.key_prefix}:issue:{{owner}}:{{repo}}:{{number}}",
            'repository_issues': f"{config.key_prefix}:repo_issues:{{owner}}:{{repo}}:{{state}}",
            'feature_detection': f"{config.key_prefix}:feature:{{issue_id}}",
            'automation_action': f"{config.key_prefix}:action:{{action_id}}",
            'webhook_event': f"{config.key_prefix}:webhook:{{delivery_id}}",
            'rate_limit': f"{config.key_prefix}:rate_limit:{{endpoint}}",
            'user_session': f"{config.key_prefix}:session:{{user_id}}",
            'metrics': f"{config.key_prefix}:metrics:{{metric_name}}:{{timestamp}}"
        }
        
        logger.info(
            "Cache manager initialized",
            redis_url=config.redis_url,
            default_ttl=config.default_ttl_seconds,
            key_prefix=config.key_prefix
        )
    
    async def connect(self):
        """Connect to Redis server."""
        try:
            self.redis_client = redis.from_url(
                self.config.redis_url,
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            # Test connection
            await self.redis_client.ping()
            
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis server."""
        if self.redis_client:
            await self.redis_client.aclose()
            logger.info("Redis connection closed")
    
    async def get(
        self,
        key: str,
        default: Any = None,
        record_stats: bool = True
    ) -> Any:
        """Get value from cache with statistics tracking."""
        if not self.redis_client:
            await self.connect()
        
        start_time = time.time()
        
        try:
            # Get value from Redis
            cached_data = await self.redis_client.get(key)
            
            if cached_data is None:
                if record_stats:
                    self.stats['misses'] += 1
                    self._update_cache_efficiency()
                return default
            
            # Deserialize data
            try:
                if self.config.compression_enabled and cached_data.startswith('COMPRESSED:'):
                    cached_data = self._decompress_data(cached_data[11:])  # Remove 'COMPRESSED:' prefix
                
                data = json.loads(cached_data)
                
                # Update access statistics
                if record_stats:
                    self.stats['hits'] += 1
                    access_time = (time.time() - start_time) * 1000
                    self._update_average_access_time(access_time)
                    self._update_cache_efficiency()
                
                return data
                
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Failed to deserialize cached data for key {key}: {str(e)}")
                if record_stats:
                    self.stats['misses'] += 1
                return default
                
        except Exception as e:
            logger.error(f"Cache get operation failed for key {key}: {str(e)}")
            if record_stats:
                self.stats['misses'] += 1
            return default
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        record_stats: bool = True
    ) -> bool:
        """Set value in cache with optional TTL."""
        if not self.redis_client:
            await self.connect()
        
        if ttl_seconds is None:
            ttl_seconds = self.config.default_ttl_seconds
        
        try:
            # Serialize data
            serialized_data = json.dumps(value, default=str)
            
            # Apply compression if configured and data is large enough
            if (self.config.compression_enabled and 
                len(serialized_data.encode()) > self.config.compression_threshold_bytes):
                serialized_data = 'COMPRESSED:' + self._compress_data(serialized_data)
            
            # Set in Redis with TTL
            result = await self.redis_client.setex(
                key, ttl_seconds, serialized_data
            )
            
            if record_stats:
                self.stats['sets'] += 1
                self.stats['total_size_bytes'] += len(serialized_data.encode())
            
            return result
            
        except Exception as e:
            logger.error(f"Cache set operation failed for key {key}: {str(e)}")
            return False
    
    async def delete(self, key: str, record_stats: bool = True) -> bool:
        """Delete key from cache."""
        if not self.redis_client:
            await self.connect()
        
        try:
            result = await self.redis_client.delete(key)
            
            if record_stats and result > 0:
                self.stats['deletes'] += 1
            
            return result > 0
            
        except Exception as e:
            logger.error(f"Cache delete operation failed for key {key}: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.redis_client:
            await self.connect()
        
        try:
            result = await self.redis_client.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache exists check failed for key {key}: {str(e)}")
            return False
    
    async def expire(self, key: str, ttl_seconds: int) -> bool:
        """Set expiration time for existing key."""
        if not self.redis_client:
            await self.connect()
        
        try:
            result = await self.redis_client.expire(key, ttl_seconds)
            return result
        except Exception as e:
            logger.error(f"Cache expire operation failed for key {key}: {str(e)}")
            return False
    
    async def get_ttl(self, key: str) -> int:
        """Get remaining TTL for key."""
        if not self.redis_client:
            await self.connect()
        
        try:
            return await self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Cache TTL check failed for key {key}: {str(e)}")
            return -1
    
    # High-level caching methods for specific data types
    
    async def cache_github_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        issue_data: Dict,
        ttl_seconds: int = 3600
    ) -> bool:
        """Cache GitHub issue data."""
        key = self.key_patterns['issue'].format(
            owner=owner, repo=repo, number=issue_number
        )
        
        # Add caching metadata
        cached_issue = {
            'data': issue_data,
            'cached_at': datetime.utcnow().isoformat(),
            'owner': owner,
            'repo': repo,
            'issue_number': issue_number
        }
        
        return await self.set(key, cached_issue, ttl_seconds)
    
    async def get_cached_github_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int
    ) -> Optional[Dict]:
        """Get cached GitHub issue data."""
        key = self.key_patterns['issue'].format(
            owner=owner, repo=repo, number=issue_number
        )
        
        cached_data = await self.get(key)
        if cached_data:
            return cached_data.get('data')
        return None
    
    async def cache_repository_issues(
        self,
        owner: str,
        repo: str,
        state: str,
        issues: List[Dict],
        ttl_seconds: int = 1800  # 30 minutes
    ) -> bool:
        """Cache repository issues list."""
        key = self.key_patterns['repository_issues'].format(
            owner=owner, repo=repo, state=state
        )
        
        cached_data = {
            'issues': issues,
            'cached_at': datetime.utcnow().isoformat(),
            'count': len(issues),
            'owner': owner,
            'repo': repo,
            'state': state
        }
        
        return await self.set(key, cached_data, ttl_seconds)
    
    async def get_cached_repository_issues(
        self,
        owner: str,
        repo: str,
        state: str
    ) -> Optional[List[Dict]]:
        """Get cached repository issues list."""
        key = self.key_patterns['repository_issues'].format(
            owner=owner, repo=repo, state=state
        )
        
        cached_data = await self.get(key)
        if cached_data:
            return cached_data.get('issues')
        return None
    
    async def cache_feature_detection(
        self,
        issue_id: str,
        detection_result: Dict,
        ttl_seconds: int = 7200  # 2 hours
    ) -> bool:
        """Cache feature detection results."""
        key = self.key_patterns['feature_detection'].format(issue_id=issue_id)
        
        cached_data = {
            'result': detection_result,
            'cached_at': datetime.utcnow().isoformat(),
            'issue_id': issue_id
        }
        
        return await self.set(key, cached_data, ttl_seconds)
    
    async def get_cached_feature_detection(self, issue_id: str) -> Optional[Dict]:
        """Get cached feature detection results."""
        key = self.key_patterns['feature_detection'].format(issue_id=issue_id)
        
        cached_data = await self.get(key)
        if cached_data:
            return cached_data.get('result')
        return None
    
    async def cache_rate_limit_status(
        self,
        endpoint: str,
        rate_limit_info: Dict,
        ttl_seconds: int = 300  # 5 minutes
    ) -> bool:
        """Cache GitHub API rate limit status."""
        key = self.key_patterns['rate_limit'].format(endpoint=endpoint)
        
        cached_data = {
            'rate_limit': rate_limit_info,
            'cached_at': datetime.utcnow().isoformat(),
            'endpoint': endpoint
        }
        
        return await self.set(key, cached_data, ttl_seconds)
    
    async def get_cached_rate_limit_status(self, endpoint: str) -> Optional[Dict]:
        """Get cached GitHub API rate limit status."""
        key = self.key_patterns['rate_limit'].format(endpoint=endpoint)
        
        cached_data = await self.get(key)
        if cached_data:
            return cached_data.get('rate_limit')
        return None
    
    async def invalidate_repository_cache(self, owner: str, repo: str):
        """Invalidate all cache entries for a repository."""
        patterns_to_invalidate = [
            f"{self.config.key_prefix}:repo_issues:{owner}:{repo}:*",
            f"{self.config.key_prefix}:issue:{owner}:{repo}:*"
        ]
        
        for pattern in patterns_to_invalidate:
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache keys for pattern {pattern}")
    
    async def warm_cache(
        self,
        owner: str,
        repo: str,
        github_client
    ):
        """Warm cache with frequently accessed data."""
        logger.info(f"Warming cache for repository {owner}/{repo}")
        
        try:
            # Warm cache with open issues
            open_issues = await github_client.get_repository_issues(
                owner, repo, state="open", per_page=100
            )
            
            if open_issues:
                await self.cache_repository_issues(
                    owner, repo, "open", open_issues, ttl_seconds=1800
                )
                
                # Cache individual issues
                for issue in open_issues[:20]:  # Cache top 20 issues
                    await self.cache_github_issue(
                        owner, repo, issue['number'], issue, ttl_seconds=3600
                    )
            
            logger.info(f"Cache warming completed for {owner}/{repo}, cached {len(open_issues)} issues")
            
        except Exception as e:
            logger.error(f"Cache warming failed for {owner}/{repo}: {str(e)}")
    
    async def cleanup_expired_keys(self):
        """Clean up expired keys and update statistics."""
        try:
            # Get all keys with TTL information
            all_keys = await self.redis_client.keys(f"{self.config.key_prefix}:*")
            expired_keys = []
            
            for key in all_keys:
                ttl = await self.redis_client.ttl(key)
                if ttl == -2:  # Key expired
                    expired_keys.append(key)
            
            if expired_keys:
                self.stats['evictions'] += len(expired_keys)
                logger.info(f"Cleaned up {len(expired_keys)} expired cache keys")
            
        except Exception as e:
            logger.error(f"Cache cleanup failed: {str(e)}")
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """Get comprehensive cache information."""
        if not self.redis_client:
            await self.connect()
        
        try:
            info = await self.redis_client.info()
            
            # Get key count by pattern
            key_counts = {}
            for data_type, pattern in self.key_patterns.items():
                pattern_key = pattern.replace('{owner}', '*').replace('{repo}', '*').replace('{number}', '*').replace('{issue_id}', '*').replace('{action_id}', '*').replace('{delivery_id}', '*').replace('{endpoint}', '*').replace('{user_id}', '*').replace('{metric_name}', '*').replace('{timestamp}', '*')
                keys = await self.redis_client.keys(pattern_key)
                key_counts[data_type] = len(keys)
            
            return {
                'connection_info': {
                    'connected': True,
                    'redis_version': info.get('redis_version'),
                    'used_memory_human': info.get('used_memory_human'),
                    'connected_clients': info.get('connected_clients')
                },
                'cache_stats': self.stats,
                'key_counts': key_counts,
                'configuration': {
                    'default_ttl_seconds': self.config.default_ttl_seconds,
                    'compression_enabled': self.config.compression_enabled,
                    'key_prefix': self.config.key_prefix
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache info: {str(e)}")
            return {
                'connection_info': {'connected': False, 'error': str(e)},
                'cache_stats': self.stats,
                'key_counts': {},
                'configuration': asdict(self.config)
            }
    
    def _update_cache_efficiency(self):
        """Update cache efficiency calculation."""
        total_requests = self.stats['hits'] + self.stats['misses']
        if total_requests > 0:
            self.stats['cache_efficiency'] = self.stats['hits'] / total_requests
    
    def _update_average_access_time(self, access_time_ms: float):
        """Update average access time calculation."""
        current_avg = self.stats['average_access_time_ms']
        total_hits = self.stats['hits']
        
        if total_hits > 1:
            self.stats['average_access_time_ms'] = (
                (current_avg * (total_hits - 1) + access_time_ms) / total_hits
            )
        else:
            self.stats['average_access_time_ms'] = access_time_ms
    
    def _compress_data(self, data: str) -> str:
        """Compress data using gzip (if available)."""
        try:
            import gzip
            import base64
            
            compressed = gzip.compress(data.encode('utf-8'))
            return base64.b64encode(compressed).decode('ascii')
        except ImportError:
            logger.warning("Compression requested but gzip not available")
            return data
    
    def _decompress_data(self, compressed_data: str) -> str:
        """Decompress data using gzip."""
        try:
            import gzip
            import base64
            
            compressed_bytes = base64.b64decode(compressed_data.encode('ascii'))
            decompressed = gzip.decompress(compressed_bytes)
            return decompressed.decode('utf-8')
        except Exception as e:
            logger.error(f"Decompression failed: {str(e)}")
            raise
    
    async def health_check(self) -> bool:
        """Perform cache health check."""
        try:
            if not self.redis_client:
                await self.connect()
            
            # Test basic operations
            test_key = f"{self.config.key_prefix}:health_check"
            test_value = {"timestamp": datetime.utcnow().isoformat()}
            
            # Test set
            await self.set(test_key, test_value, ttl_seconds=10, record_stats=False)
            
            # Test get
            retrieved = await self.get(test_key, record_stats=False)
            
            # Test delete
            await self.delete(test_key, record_stats=False)
            
            return retrieved is not None
            
        except Exception as e:
            logger.error(f"Cache health check failed: {str(e)}")
            return False