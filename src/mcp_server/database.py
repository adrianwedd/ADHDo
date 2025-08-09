"""Database configuration and session management for MCP ADHD Server."""
import asyncio
from typing import AsyncGenerator

from sqlalchemy import MetaData, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from mcp_server.config import settings

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

async def init_database() -> None:
    """Initialize database engine and session factory."""
    global engine, SessionLocal
    
    if engine is None:
        engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=20,  # Increased pool size for better integration
            max_overflow=30,  # Allow overflow connections during peak
            pool_timeout=10,  # Connection acquisition timeout
            connect_args={
                "server_settings": {
                    "jit": "off"  # Disable JIT for consistent performance
                }
            }
        )
        
        SessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    if SessionLocal is None:
        await init_database()
    
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def close_database() -> None:
    """Close database connections."""
    global engine
    if engine:
        await engine.dispose()
        engine = None