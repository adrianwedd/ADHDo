"""
Performance-optimized database configuration for MCP ADHD Server.

Features:
- Connection pooling optimized for ADHD response times (<3 seconds)
- Memory-efficient session management
- Performance monitoring and metrics
- Connection pool health monitoring
"""
import asyncio
import time
from typing import AsyncGenerator, Optional
import structlog

from sqlalchemy import MetaData, event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import QueuePool

from mcp_server.config import settings
from mcp_server.performance_config import perf_config

# Database metadata with naming convention for constraints
metadata = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s", 
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
})

class Base(DeclarativeBase):
    """Base class for all database models."""
    metadata = metadata

# Global engine and session factory
engine = None
SessionLocal = None

# Performance monitoring
_connection_metrics = {
    'connections_created': 0,
    'connections_closed': 0,
    'query_times': [],
    'pool_size': 0,
    'checked_out_connections': 0
}

logger = structlog.get_logger(__name__)

async def init_database() -> None:
    """Initialize high-performance database engine with ADHD-optimized settings."""
    global engine, SessionLocal
    
    if engine is None:
        logger.info("Initializing performance-optimized database engine")
        
        # Performance-optimized connection arguments
        connect_args = {
            "server_settings": {
                "jit": "off",  # Disable JIT for consistent performance
                "shared_preload_libraries": "",  # Reduce startup overhead
                "max_connections": "100",  # Reasonable limit
                "work_mem": "4MB",  # Memory for sorts/hashes
                "maintenance_work_mem": "64MB",
                "effective_cache_size": "256MB",
                "checkpoint_completion_target": "0.9",
                "wal_buffers": "16MB",
                "default_statistics_target": "100"
            },
            "command_timeout": 30,  # 30 second query timeout for ADHD users
        }
        
        # Create engine with performance optimizations
        engine = create_async_engine(
            settings.database_url,
            echo=settings.DEBUG and False,  # Disable echo in production for performance
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,  # Recycle connections every hour
            pool_size=perf_config.db_pool_size,  # Configurable pool size
            max_overflow=perf_config.db_pool_max_overflow,  # Overflow connections
            pool_timeout=5,  # Fast timeout for ADHD response times
            poolclass=QueuePool,  # Use queue pool for better performance
            connect_args=connect_args,
            # Performance options
            isolation_level="READ_COMMITTED",  # Faster than SERIALIZABLE
            logging_name="mcp_adhd_db"
        )
        
        # Set up connection event listeners for monitoring
        @event.listens_for(engine.sync_engine, "connect")
        def receive_connect(dbapi_connection, connection_record):
            """Track connection creation."""
            _connection_metrics['connections_created'] += 1
            
        @event.listens_for(engine.sync_engine, "close") 
        def receive_close(dbapi_connection, connection_record):
            """Track connection closure."""
            _connection_metrics['connections_closed'] += 1
        
        # Create optimized session factory
        SessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Better performance, handle manually
            autoflush=True,  # Auto-flush for data consistency
            autocommit=False
        )
        
        # Test connection and log performance info
        try:
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                await result.fetchone()
                
            pool_status = engine.pool.status()
            logger.info("Database engine initialized successfully",
                       pool_size=engine.pool.size(),
                       checked_out=engine.pool.checkedout(),
                       overflow=engine.pool.overflow(),
                       performance_mode=True)
                       
        except Exception as e:
            logger.error("Database initialization failed", error=str(e))
            raise

async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """Performance-optimized database session dependency."""
    if SessionLocal is None:
        await init_database()
    
    session_start_time = time.perf_counter()
    session = None
    
    try:
        session = SessionLocal()
        yield session
        
        # Commit with performance tracking
        commit_start = time.perf_counter()
        await session.commit()
        commit_time = time.perf_counter() - commit_start
        
        # Track slow commits (>100ms indicates potential ADHD impact)
        if commit_time > 0.1:
            logger.warning("Slow database commit detected",
                          commit_time=f"{commit_time:.3f}s",
                          adhd_impact="May affect response time")
            
    except Exception as e:
        if session:
            rollback_start = time.perf_counter()
            await session.rollback()
            rollback_time = time.perf_counter() - rollback_start
            
            logger.error("Database transaction rolled back",
                        error=str(e)[:100],
                        rollback_time=f"{rollback_time:.3f}s")
        raise
        
    finally:
        if session:
            try:
                await session.close()
                
                # Track total session time
                total_session_time = time.perf_counter() - session_start_time
                _connection_metrics['query_times'].append(total_session_time)
                
                # Keep only recent query times (last 100)
                if len(_connection_metrics['query_times']) > 100:
                    _connection_metrics['query_times'] = _connection_metrics['query_times'][-100:]
                    
            except Exception as close_error:
                logger.error("Error closing database session", error=str(close_error))


async def get_db_performance_metrics() -> dict:
    """Get database performance metrics."""
    if engine is None:
        return {"error": "Database not initialized"}
    
    pool = engine.pool
    
    # Calculate query time statistics
    query_times = _connection_metrics['query_times']
    avg_query_time = sum(query_times) / len(query_times) if query_times else 0
    max_query_time = max(query_times) if query_times else 0
    
    return {
        "pool_metrics": {
            "pool_size": pool.size(),
            "checked_out": pool.checkedout(), 
            "overflow": pool.overflow(),
            "checked_in": pool.checkedin()
        },
        "connection_metrics": {
            "connections_created": _connection_metrics['connections_created'],
            "connections_closed": _connection_metrics['connections_closed'],
            "active_connections": _connection_metrics['connections_created'] - _connection_metrics['connections_closed']
        },
        "performance_metrics": {
            "avg_query_time_ms": round(avg_query_time * 1000, 2),
            "max_query_time_ms": round(max_query_time * 1000, 2),
            "total_queries": len(query_times),
            "slow_queries": len([t for t in query_times if t > 0.1])  # >100ms
        },
        "health": {
            "adhd_compliant": avg_query_time < 0.1,  # <100ms average
            "pool_healthy": pool.checkedout() < pool.size() * 0.8  # <80% utilization
        }
    }


async def close_database() -> None:
    """Performance-optimized database shutdown."""
    global engine
    
    if engine:
        logger.info("Closing database connections")
        
        try:
            # Get final metrics before shutdown
            metrics = await get_db_performance_metrics()
            logger.info("Database performance summary", **metrics)
            
            # Graceful connection disposal
            await engine.dispose()
            
            # Reset globals
            engine = None
            SessionLocal = None
            
            logger.info("Database connections closed successfully")
            
        except Exception as e:
            logger.error("Error during database shutdown", error=str(e))
            # Force cleanup
            engine = None