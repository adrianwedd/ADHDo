"""
MCP Client Package for ADHD Server

Model Context Protocol client implementation for universal tool integration.
"""

from .client import MCPClient
from .models import (
    Tool, ToolConfig, ToolResult, ToolError,
    Resource, ResourceConfig, ResourceResult,
    ContextFrame, Integration, WorkflowStep
)
from .registry import ToolRegistry
from .auth import AuthManager
from .workflow import WorkflowEngine

__all__ = [
    "MCPClient",
    "Tool", "ToolConfig", "ToolResult", "ToolError",
    "Resource", "ResourceConfig", "ResourceResult", 
    "ContextFrame", "Integration", "WorkflowStep",
    "ToolRegistry",
    "AuthManager",
    "WorkflowEngine"
]