"""
GitHub API Client with intelligent rate limiting and error handling.

Enterprise-grade GitHub API integration with comprehensive error handling,
rate limiting, pagination, and caching for optimal performance.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import aiohttp
import structlog
from aiohttp import ClientTimeout, ClientError

logger = structlog.get_logger()


@dataclass
class RateLimitInfo:
    """GitHub API rate limit information."""
    limit: int
    remaining: int
    reset_timestamp: int
    used: int
    rate_limit_type: str = "core"
    
    @property
    def reset_datetime(self) -> datetime:
        """Get reset time as datetime."""
        return datetime.fromtimestamp(self.reset_timestamp)
    
    @property
    def seconds_until_reset(self) -> int:
        """Get seconds until rate limit resets."""
        return max(0, self.reset_timestamp - int(time.time()))


class GitHubAPIError(Exception):
    """GitHub API specific errors."""
    
    def __init__(self, message: str, status_code: int = None, rate_limit_info: RateLimitInfo = None):
        super().__init__(message)
        self.status_code = status_code
        self.rate_limit_info = rate_limit_info


class GitHubAPIClient:
    """
    Production-ready GitHub API client with enterprise features.
    
    Features:
    - Automatic rate limit handling and retry logic
    - Comprehensive pagination support
    - Request/response caching for performance
    - Detailed logging and metrics
    - Connection pooling and timeout handling
    """
    
    def __init__(
        self,
        token: str,
        base_url: str = "https://api.github.com",
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """Initialize GitHub API client."""
        self.token = token
        self.base_url = base_url.rstrip('/')
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # HTTP client configuration
        self.timeout = ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Rate limiting
        self.rate_limit_info: Optional[RateLimitInfo] = None
        self.last_rate_limit_check = 0
        
        # Metrics
        self.metrics = {
            'requests_made': 0,
            'rate_limit_hits': 0,
            'retries_made': 0,
            'cache_hits': 0,
            'errors': 0,
            'total_response_time': 0.0
        }
        
        # Simple in-memory cache (in production, use Redis)
        self._cache: Dict[str, Dict] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._cache_ttl = 300  # 5 minutes
        
        logger.info("GitHub API client initialized", base_url=base_url, timeout=timeout)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is available."""
        if self.session is None or self.session.closed:
            headers = {
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'ADHDo-GitHub-Automation/1.0.0',
                'X-GitHub-Api-Version': '2022-11-28'
            }
            
            connector = aiohttp.TCPConnector(
                limit=100,  # Connection pool size
                limit_per_host=20,
                keepalive_timeout=60,
                enable_cleanup_closed=True
            )
            
            self.session = aiohttp.ClientSession(
                headers=headers,
                timeout=self.timeout,
                connector=connector
            )
    
    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with rate limiting and error handling."""
        await self._ensure_session()
        
        url = urljoin(self.base_url + '/', endpoint.lstrip('/'))
        
        # Check cache first
        if cache_key and method.upper() == 'GET':
            cached_response = self._get_cached_response(cache_key)
            if cached_response:
                self.metrics['cache_hits'] += 1
                return cached_response
        
        # Check rate limits before making request
        await self._check_rate_limits()
        
        start_time = time.time()
        retry_count = 0
        
        while retry_count <= self.max_retries:
            try:
                self.metrics['requests_made'] += 1
                
                async with self.session.request(
                    method.upper(),
                    url,
                    params=params,
                    json=json_data
                ) as response:
                    
                    # Update rate limit info from headers
                    self._update_rate_limit_info(response.headers)
                    
                    response_time = time.time() - start_time
                    self.metrics['total_response_time'] += response_time
                    
                    # Handle different response codes
                    if response.status == 200:
                        response_data = await response.json()
                        
                        # Cache GET responses
                        if cache_key and method.upper() == 'GET':
                            self._cache_response(cache_key, response_data)
                        
                        logger.debug(
                            "GitHub API request successful",
                            method=method.upper(),
                            url=url,
                            status=response.status,
                            response_time_ms=response_time * 1000
                        )
                        
                        return {
                            'success': True,
                            'data': response_data,
                            'headers': dict(response.headers),
                            'status_code': response.status,
                            'response_time_ms': response_time * 1000
                        }
                    
                    elif response.status == 404:
                        logger.warning("GitHub API resource not found", url=url, status=response.status)
                        return {
                            'success': False,
                            'error': 'Resource not found',
                            'status_code': response.status,
                            'data': None
                        }
                    
                    elif response.status == 403:
                        # Rate limit or permissions issue
                        error_data = await response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                        
                        if 'rate limit' in error_data.get('message', '').lower():
                            self.metrics['rate_limit_hits'] += 1
                            logger.warning(
                                "GitHub API rate limit exceeded",
                                reset_time=self.rate_limit_info.reset_datetime if self.rate_limit_info else 'unknown'
                            )
                            
                            # Wait for rate limit reset if we have time info
                            if self.rate_limit_info and retry_count < self.max_retries:
                                sleep_time = min(self.rate_limit_info.seconds_until_reset + 10, 3600)  # Max 1 hour
                                logger.info(f"Waiting {sleep_time} seconds for rate limit reset")
                                await asyncio.sleep(sleep_time)
                                retry_count += 1
                                continue
                        
                        return {
                            'success': False,
                            'error': f"Forbidden: {error_data.get('message', 'Permission denied')}",
                            'status_code': response.status,
                            'data': error_data
                        }
                    
                    elif response.status >= 500:
                        # Server error - retry
                        logger.warning(
                            "GitHub API server error",
                            status=response.status,
                            retry_count=retry_count
                        )
                        
                        if retry_count < self.max_retries:
                            retry_count += 1
                            self.metrics['retries_made'] += 1
                            await asyncio.sleep(self.retry_delay * (2 ** retry_count))  # Exponential backoff
                            continue
                        
                        error_text = await response.text()
                        return {
                            'success': False,
                            'error': f"Server error: {error_text}",
                            'status_code': response.status,
                            'data': None
                        }
                    
                    else:
                        # Other client errors
                        error_data = await response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                        logger.error(
                            "GitHub API client error",
                            status=response.status,
                            error_data=error_data
                        )
                        return {
                            'success': False,
                            'error': f"Client error: {error_data.get('message', 'Unknown error')}",
                            'status_code': response.status,
                            'data': error_data
                        }
            
            except ClientError as e:
                logger.error(f"GitHub API connection error", error=str(e), retry_count=retry_count)
                
                if retry_count < self.max_retries:
                    retry_count += 1
                    self.metrics['retries_made'] += 1
                    await asyncio.sleep(self.retry_delay * (2 ** retry_count))
                    continue
                
                self.metrics['errors'] += 1
                return {
                    'success': False,
                    'error': f"Connection error: {str(e)}",
                    'status_code': None,
                    'data': None
                }
        
        # If we get here, all retries failed
        self.metrics['errors'] += 1
        return {
            'success': False,
            'error': f"Request failed after {self.max_retries} retries",
            'status_code': None,
            'data': None
        }
    
    async def _check_rate_limits(self):
        """Check and wait for rate limits if necessary."""
        if not self.rate_limit_info:
            return
        
        # If we're close to the rate limit, wait
        if self.rate_limit_info.remaining < 10:
            wait_time = self.rate_limit_info.seconds_until_reset + 5
            if wait_time > 0 and wait_time < 3600:  # Max 1 hour wait
                logger.warning(f"Rate limit low, waiting {wait_time} seconds")
                await asyncio.sleep(wait_time)
    
    def _update_rate_limit_info(self, headers: Dict[str, str]):
        """Update rate limit information from response headers."""
        try:
            if 'X-RateLimit-Limit' in headers:
                self.rate_limit_info = RateLimitInfo(
                    limit=int(headers.get('X-RateLimit-Limit', 5000)),
                    remaining=int(headers.get('X-RateLimit-Remaining', 5000)),
                    reset_timestamp=int(headers.get('X-RateLimit-Reset', time.time() + 3600)),
                    used=int(headers.get('X-RateLimit-Used', 0)),
                    rate_limit_type=headers.get('X-RateLimit-Resource', 'core')
                )
                self.last_rate_limit_check = time.time()
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse rate limit headers: {e}")
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """Get cached response if still valid."""
        if cache_key in self._cache:
            timestamp = self._cache_timestamps.get(cache_key, 0)
            if time.time() - timestamp < self._cache_ttl:
                return self._cache[cache_key]
            else:
                # Cleanup expired cache entry
                del self._cache[cache_key]
                del self._cache_timestamps[cache_key]
        return None
    
    def _cache_response(self, cache_key: str, data: Dict):
        """Cache response data."""
        self._cache[cache_key] = data
        self._cache_timestamps[cache_key] = time.time()
        
        # Simple cache cleanup (keep last 1000 entries)
        if len(self._cache) > 1000:
            oldest_key = min(self._cache_timestamps.keys(), key=self._cache_timestamps.get)
            del self._cache[oldest_key]
            del self._cache_timestamps[oldest_key]
    
    # GitHub API Methods
    
    async def get_repository_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        since: Optional[datetime] = None,
        per_page: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all issues for a repository with automatic pagination."""
        issues = []
        page = 1
        
        params = {
            'state': state,
            'per_page': min(per_page, 100),
            'sort': 'updated',
            'direction': 'desc'
        }
        
        if since:
            params['since'] = since.isoformat()
        
        while True:
            params['page'] = page
            cache_key = f"issues_{owner}_{repo}_{state}_{page}_{since}"
            
            result = await self._make_request(
                'GET',
                f'/repos/{owner}/{repo}/issues',
                params=params,
                cache_key=cache_key
            )
            
            if not result['success']:
                logger.error(f"Failed to fetch issues page {page}", error=result['error'])
                break
            
            page_issues = result['data']
            
            # Filter out pull requests (GitHub API returns them as issues)
            page_issues = [issue for issue in page_issues if 'pull_request' not in issue]
            
            issues.extend(page_issues)
            
            # Check if we have more pages
            if len(page_issues) < per_page:
                break
            
            page += 1
            
            # Safety check to prevent infinite loops
            if page > 100:
                logger.warning(f"Stopped pagination at page {page} for safety")
                break
        
        logger.info(f"Retrieved {len(issues)} issues from {owner}/{repo}")
        return issues
    
    async def get_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int
    ) -> Dict[str, Any]:
        """Get a specific issue."""
        cache_key = f"issue_{owner}_{repo}_{issue_number}"
        
        result = await self._make_request(
            'GET',
            f'/repos/{owner}/{repo}/issues/{issue_number}',
            cache_key=cache_key
        )
        
        return result
    
    async def close_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Close an issue with optional comment."""
        # Add comment first if provided
        if comment:
            comment_result = await self.create_issue_comment(
                owner, repo, issue_number, comment
            )
            if not comment_result['success']:
                logger.warning(f"Failed to add closing comment to issue {issue_number}")
        
        # Close the issue
        result = await self._make_request(
            'PATCH',
            f'/repos/{owner}/{repo}/issues/{issue_number}',
            json_data={'state': 'closed'}
        )
        
        return result
    
    async def create_issue_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str
    ) -> Dict[str, Any]:
        """Create a comment on an issue."""
        result = await self._make_request(
            'POST',
            f'/repos/{owner}/{repo}/issues/{issue_number}/comments',
            json_data={'body': body}
        )
        
        return result
    
    async def update_issue_labels(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        labels: List[str]
    ) -> Dict[str, Any]:
        """Update labels on an issue."""
        result = await self._make_request(
            'PUT',
            f'/repos/{owner}/{repo}/issues/{issue_number}/labels',
            json_data={'labels': labels}
        )
        
        return result
    
    async def get_repository_commits(
        self,
        owner: str,
        repo: str,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        per_page: int = 100
    ) -> List[Dict[str, Any]]:
        """Get repository commits with pagination."""
        commits = []
        page = 1
        
        params = {
            'per_page': min(per_page, 100)
        }
        
        if since:
            params['since'] = since.isoformat()
        if until:
            params['until'] = until.isoformat()
        
        while True:
            params['page'] = page
            cache_key = f"commits_{owner}_{repo}_{page}_{since}_{until}"
            
            result = await self._make_request(
                'GET',
                f'/repos/{owner}/{repo}/commits',
                params=params,
                cache_key=cache_key
            )
            
            if not result['success']:
                logger.error(f"Failed to fetch commits page {page}", error=result['error'])
                break
            
            page_commits = result['data']
            commits.extend(page_commits)
            
            if len(page_commits) < per_page:
                break
            
            page += 1
            
            # Safety check
            if page > 50:
                logger.warning(f"Stopped commit pagination at page {page} for safety")
                break
        
        logger.info(f"Retrieved {len(commits)} commits from {owner}/{repo}")
        return commits
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get client performance metrics."""
        total_requests = self.metrics['requests_made']
        avg_response_time = (
            self.metrics['total_response_time'] / total_requests 
            if total_requests > 0 else 0.0
        )
        
        return {
            'requests_made': total_requests,
            'rate_limit_hits': self.metrics['rate_limit_hits'],
            'retries_made': self.metrics['retries_made'],
            'cache_hits': self.metrics['cache_hits'],
            'errors': self.metrics['errors'],
            'average_response_time_ms': avg_response_time * 1000,
            'cache_size': len(self._cache),
            'current_rate_limit': {
                'remaining': self.rate_limit_info.remaining if self.rate_limit_info else None,
                'reset_time': self.rate_limit_info.reset_datetime.isoformat() if self.rate_limit_info else None
            }
        }