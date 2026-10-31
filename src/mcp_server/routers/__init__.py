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
from .docs_routes import docs_router
from .calendar_routes import router as calendar_router
from .onboarding_routes import onboarding_router
from .adhd_routes import router as adhd_router

__all__ = [
    "auth_router",
    "health_router", 
    "chat_router",
    "user_router",
    "webhook_router",
    "beta_router",
    "evolution_router",
    "docs_router",
    "calendar_router",
    "onboarding_router",
    "adhd_router"
]

# Evolution is optional and the application already loads its router lazily.
# Do not import the experimental engine while importing core routes.
def __getattr__(name):
    if name == "evolution_router":
        from .evolution_routes import evolution_router
        return evolution_router
    raise AttributeError(name)
