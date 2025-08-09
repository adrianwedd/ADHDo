"""
MCP Server Routers - Modular FastAPI route organization.

This module provides a clean separation of concerns for different
API endpoints, breaking down the monolithic main.py structure.
"""

from .auth_routes import auth_router
from .health_routes import health_router  
from .chat_routes import chat_router
from .user_routes import user_router
from .webhook_routes import webhook_router
from .beta_routes import beta_router
from .evolution_routes import evolution_router
from .docs_routes import docs_router
from .calendar_routes import router as calendar_router

__all__ = [
    "auth_router",
    "health_router", 
    "chat_router",
    "user_router",
    "webhook_router",
    "beta_router",
    "evolution_router",
    "docs_router",
    "calendar_router"
]