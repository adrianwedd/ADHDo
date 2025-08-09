"""
Performance optimization configuration for MCP ADHD Server.
Controls lazy loading, caching, and other performance features.
"""

from typing import Dict, Any, Set
from dataclasses import dataclass, field


@dataclass
class PerformanceConfig:
    """Configuration for performance optimizations."""
    
    # Import optimization
    lazy_import_enabled: bool = True
    deferred_imports: Set[str] = field(default_factory=lambda: {
        'mcp_integration',
        'telegram_bot', 
        'evolution_router',
        'emergent_evolution',
        'optimization_engine',
        'github_automation_endpoints'
    })
    
    # Startup optimization
    parallel_startup_enabled: bool = True
    skip_optional_services: bool = False
    startup_timeout_seconds: int = 30
    
    # Memory optimization  
    enable_memory_profiling: bool = True
    memory_threshold_mb: int = 200
    gc_aggressive_mode: bool = False
    
    # Caching optimization
    response_cache_enabled: bool = True
    static_cache_ttl: int = 3600  # 1 hour
    health_cache_ttl: int = 5     # 5 seconds
    
    # Connection pooling
    redis_pool_size: int = 10
    db_pool_size: int = 20
    db_pool_max_overflow: int = 10
    
    # Request optimization
    compression_enabled: bool = True
    request_timeout: int = 30
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    
    # Background task optimization
    background_task_concurrency: int = 5
    health_check_interval: int = 30
    metrics_collection_interval: int = 60
    
    # Evolution engine optimization (heavy component)
    evolution_lazy_load: bool = True
    evolution_cache_size: int = 1000
    evolution_batch_size: int = 50


# Global performance configuration
perf_config = PerformanceConfig()


class LazyImporter:
    """Lazy importer for deferring heavy module imports until needed."""
    
    def __init__(self):
        self._imported_modules: Dict[str, Any] = {}
        self._import_times: Dict[str, float] = {}
    
    def get_module(self, module_name: str, import_path: str):
        """Get module with lazy import."""
        if module_name in self._imported_modules:
            return self._imported_modules[module_name]
            
        import time
        start_time = time.perf_counter()
        
        try:
            # Dynamic import
            parts = import_path.split('.')
            module = __import__(import_path)
            for part in parts[1:]:
                module = getattr(module, part)
                
            self._imported_modules[module_name] = module
            self._import_times[module_name] = time.perf_counter() - start_time
            
            return module
            
        except ImportError as e:
            # Log and return None for optional modules
            import structlog
            logger = structlog.get_logger(__name__)
            logger.warning(f"Optional module {module_name} not available", error=str(e))
            return None
    
    def get_import_stats(self) -> Dict[str, float]:
        """Get import timing statistics."""
        return self._import_times.copy()


# Global lazy importer
lazy_importer = LazyImporter()


def get_telegram_bot():
    """Lazy import telegram bot."""
    if not perf_config.lazy_import_enabled:
        from mcp_server.telegram_bot import telegram_bot
        return telegram_bot
    
    return lazy_importer.get_module('telegram_bot', 'mcp_server.telegram_bot')


def get_mcp_integration():
    """Lazy import MCP integration system.""" 
    if not perf_config.lazy_import_enabled:
        from mcp_server import mcp_integration
        return mcp_integration
    
    return lazy_importer.get_module('mcp_integration', 'mcp_server.mcp_integration')


def get_evolution_router():
    """Lazy import evolution router."""
    if not perf_config.lazy_import_enabled:
        from mcp_server.routers.evolution_routes import evolution_router
        return evolution_router
    
    return lazy_importer.get_module('evolution_router', 'mcp_server.routers.evolution_routes')


def get_github_automation():
    """Lazy import GitHub automation endpoints."""
    if not perf_config.lazy_import_enabled:
        from mcp_server.github_automation_endpoints import github_router
        return github_router
    
    return lazy_importer.get_module('github_router', 'mcp_server.github_automation_endpoints')


def should_enable_service(service_name: str) -> bool:
    """Check if a service should be enabled based on performance config."""
    if perf_config.skip_optional_services:
        optional_services = {
            'telegram_bot', 'evolution_engine', 'github_automation',
            'nest_integration', 'gmail_integration'
        }
        return service_name not in optional_services
    
    return True