"""
Documentation portal routes - Enhanced API documentation and developer resources.

Provides ADHD-friendly documentation portal with interactive examples,
code generators, and comprehensive developer guides.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any, Optional, List
import json

from ..health_monitor import health_monitor
from ..__about__ import __version__

docs_router = APIRouter(tags=["Documentation"])

# Initialize templates (will create template files next)
templates = Jinja2Templates(directory="templates")


@docs_router.get("/docs-portal", response_class=HTMLResponse,
                 summary="Enhanced Documentation Portal",
                 description="ADHD-friendly API documentation portal with interactive examples")
async def docs_portal(request: Request):
    """
    Serve the enhanced documentation portal.
    
    Features:
    - ADHD-optimized design with clear visual hierarchy
    - Interactive API testing capabilities
    - Code examples in multiple languages
    - Progressive disclosure of complex features
    - Quick reference sections for common tasks
    """
    try:
        # Get OpenAPI schema for dynamic documentation
        openapi_schema = request.app.openapi()
        
        # Extract key information for the portal
        portal_data = {
            "title": openapi_schema.get("info", {}).get("title", "MCP ADHD Server"),
            "version": __version__,
            "description": openapi_schema.get("info", {}).get("description", ""),
            "servers": openapi_schema.get("servers", []),
            "tags": openapi_schema.get("tags", []),
            "paths": openapi_schema.get("paths", {}),
            "components": openapi_schema.get("components", {})
        }
        
        return templates.TemplateResponse("docs_portal.html", {
            "request": request,
            "portal_data": portal_data,
            "version": __version__
        })
        
    except Exception as e:
        health_monitor.record_error("docs_portal", str(e))
        raise HTTPException(status_code=500, detail="Documentation portal unavailable")


@docs_router.get("/docs-portal/api/endpoints",
                 summary="Get API Endpoints List", 
                 description="Returns organized list of all API endpoints with ADHD-friendly categorization")
async def get_api_endpoints(request: Request) -> Dict[str, Any]:
    """
    Get organized API endpoints for the documentation portal.
    
    Returns endpoints grouped by category with ADHD-friendly descriptions,
    difficulty levels, and usage frequency indicators.
    """
    try:
        openapi_schema = request.app.openapi()
        paths = openapi_schema.get("paths", {})
        tags = {tag["name"]: tag for tag in openapi_schema.get("tags", [])}
        
        # Organize endpoints by category with ADHD-friendly metadata
        categorized_endpoints = {}
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    endpoint_tags = details.get("tags", ["Uncategorized"])
                    primary_tag = endpoint_tags[0] if endpoint_tags else "Uncategorized"
                    
                    if primary_tag not in categorized_endpoints:
                        tag_info = tags.get(primary_tag, {})
                        categorized_endpoints[primary_tag] = {
                            "name": primary_tag,
                            "description": tag_info.get("description", ""),
                            "icon": _get_category_icon(primary_tag),
                            "difficulty": _get_category_difficulty(primary_tag),
                            "endpoints": []
                        }
                    
                    # Add ADHD-friendly metadata
                    endpoint_info = {
                        "path": path,
                        "method": method.upper(),
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                        "difficulty": _get_endpoint_difficulty(path, method),
                        "frequency": _get_endpoint_frequency(path, method),
                        "response_time": _get_estimated_response_time(path, method),
                        "examples": _get_endpoint_examples(path, method, details)
                    }
                    
                    categorized_endpoints[primary_tag]["endpoints"].append(endpoint_info)
        
        return {
            "categories": categorized_endpoints,
            "total_endpoints": sum(len(cat["endpoints"]) for cat in categorized_endpoints.values()),
            "quick_start_endpoints": _get_quick_start_endpoints(categorized_endpoints)
        }
        
    except Exception as e:
        health_monitor.record_error("get_api_endpoints", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve endpoints")


@docs_router.get("/docs-portal/api/examples/{category}",
                 summary="Get Code Examples by Category",
                 description="Returns code examples in multiple languages for a specific API category")
async def get_code_examples(category: str, language: str = "python") -> Dict[str, Any]:
    """
    Get code examples for a specific API category.
    
    Supports multiple programming languages with ADHD-friendly
    explanations and step-by-step breakdowns.
    """
    try:
        # Define code examples for different categories and languages
        examples = _generate_code_examples(category, language)
        
        return {
            "category": category,
            "language": language,
            "examples": examples,
            "prerequisites": _get_prerequisites(category, language),
            "common_pitfalls": _get_common_pitfalls(category),
            "adhd_tips": _get_adhd_coding_tips(category)
        }
        
    except Exception as e:
        health_monitor.record_error("get_code_examples", str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve code examples")


@docs_router.get("/docs-portal/quick-reference",
                 summary="Quick Reference Guide", 
                 description="ADHD-optimized quick reference for common API operations")
async def quick_reference() -> Dict[str, Any]:
    """
    Get quick reference guide for common operations.
    
    Optimized for ADHD users with:
    - Most common tasks first
    - Single-screen reference
    - Copy-paste ready examples
    - Minimal cognitive load
    """
    try:
        return {
            "common_tasks": [
                {
                    "task": "Start a conversation",
                    "endpoint": "POST /chat",
                    "example": {
                        "message": "I need help staying focused",
                        "context": {"task": "work project", "energy": "low"}
                    },
                    "difficulty": "beginner",
                    "estimated_time": "< 5 minutes"
                },
                {
                    "task": "Create a task",
                    "endpoint": "POST /tasks", 
                    "example": {
                        "title": "Complete quarterly report",
                        "priority": "high",
                        "estimated_duration": 120
                    },
                    "difficulty": "beginner",
                    "estimated_time": "< 3 minutes"
                },
                {
                    "task": "Check system health",
                    "endpoint": "GET /health",
                    "example": {},
                    "difficulty": "beginner", 
                    "estimated_time": "< 1 minute"
                },
                {
                    "task": "Register new user",
                    "endpoint": "POST /api/auth/register",
                    "example": {
                        "email": "user@example.com",
                        "password": "secure_password"
                    },
                    "difficulty": "intermediate",
                    "estimated_time": "< 10 minutes"
                }
            ],
            "authentication_flow": {
                "step1": "Register: POST /api/auth/register",
                "step2": "Login: POST /api/auth/login",
                "step3": "Use token in Authorization header: Bearer <token>"
            },
            "response_patterns": {
                "success": {"status": "success", "data": "..."},
                "error": {"error": "error_message", "details": "..."},
                "adhd_optimized": {"response": "clear_message", "processing_time": "< 3s"}
            }
        }
        
    except Exception as e:
        health_monitor.record_error("quick_reference", str(e))
        raise HTTPException(status_code=500, detail="Failed to generate quick reference")


def _get_category_icon(category: str) -> str:
    """Get icon for API category."""
    icons = {
        "Authentication": "🔐",
        "Chat": "💬", 
        "Health": "🏥",
        "Users": "👥",
        "Tasks": "✅",
        "Webhooks": "🔗",
        "Beta": "🧪",
        "Evolution": "🧬",
        "GitHub Automation": "🐙"
    }
    return icons.get(category, "📄")


def _get_category_difficulty(category: str) -> str:
    """Get difficulty level for API category."""
    difficulties = {
        "Health": "beginner",
        "Chat": "beginner", 
        "Authentication": "intermediate",
        "Tasks": "beginner",
        "Users": "intermediate",
        "Webhooks": "advanced",
        "Beta": "intermediate",
        "Evolution": "advanced",
        "GitHub Automation": "advanced"
    }
    return difficulties.get(category, "intermediate")


def _get_endpoint_difficulty(path: str, method: str) -> str:
    """Determine endpoint difficulty level."""
    if method == "GET" and "health" in path:
        return "beginner"
    elif method == "POST" and "chat" in path:
        return "beginner"
    elif "auth" in path:
        return "intermediate"
    elif "webhook" in path or "evolution" in path:
        return "advanced"
    else:
        return "intermediate"


def _get_endpoint_frequency(path: str, method: str) -> str:
    """Estimate usage frequency."""
    high_frequency = ["/chat", "/health", "/api/auth"]
    medium_frequency = ["/tasks", "/users", "/context"]
    
    for freq_path in high_frequency:
        if freq_path in path:
            return "high"
    
    for freq_path in medium_frequency:
        if freq_path in path:
            return "medium"
    
    return "low"


def _get_estimated_response_time(path: str, method: str) -> str:
    """Estimate response time for ADHD users."""
    if "chat" in path:
        return "< 3s (ADHD optimized)"
    elif "health" in path:
        return "< 100ms"
    elif "auth" in path:
        return "< 500ms"
    else:
        return "< 1s"


def _get_endpoint_examples(path: str, method: str, details: Dict) -> Dict[str, Any]:
    """Generate examples for endpoint."""
    # This would generate relevant examples based on the endpoint
    # For now, return basic structure
    return {
        "curl": f"curl -X {method.upper()} {path}",
        "python": f"requests.{method.lower()}('{path}')",
        "javascript": f"fetch('{path}', {{ method: '{method.upper()}' }})"
    }


def _generate_code_examples(category: str, language: str) -> Dict[str, Any]:
    """Generate comprehensive code examples."""
    if category.lower() == "chat" and language == "python":
        return {
            "basic_chat": {
                "title": "Basic Chat Request",
                "code": '''
import requests

# Basic chat with the MCP system
response = requests.post("http://localhost:8000/chat", json={
    "message": "I'm feeling overwhelmed and need help organizing my day",
    "context": {
        "energy_level": "low",
        "available_time": "2 hours",
        "priority_task": "work presentation"
    }
})

print(response.json()["response"])
                ''',
                "explanation": "This example shows how to send a basic message to the MCP system with context about your current state."
            },
            "emergency_chat": {
                "title": "Emergency/Crisis Chat",
                "code": '''
import requests

# Emergency chat for crisis situations
response = requests.post("http://localhost:8000/chat", json={
    "message": "I'm having a difficult time and need immediate support",
    "emergency": True
})

# Emergency responses are handled with highest priority
print("Crisis support:", response.json()["response"])
                ''',
                "explanation": "Use the emergency flag for crisis situations. The system provides immediate, hardcoded safety responses."
            }
        }
    
    # Return basic examples for other categories
    return {
        "basic_example": {
            "title": f"Basic {category} Example",
            "code": f"# {language} example for {category} endpoints",
            "explanation": f"Example code for {category} operations"
        }
    }


def _get_prerequisites(category: str, language: str) -> List[str]:
    """Get prerequisites for using category."""
    base_prereqs = [f"{language} installed", "API server running"]
    
    if category.lower() == "authentication":
        base_prereqs.append("Valid email address")
    elif category.lower() == "chat":
        base_prereqs.append("Basic understanding of ADHD support concepts")
    
    return base_prereqs


def _get_common_pitfalls(category: str) -> List[str]:
    """Get common pitfalls for category."""
    general_pitfalls = [
        "Not handling network timeouts",
        "Forgetting to include authentication headers"
    ]
    
    category_pitfalls = {
        "chat": [
            "Not providing enough context for ADHD-optimized responses",
            "Forgetting to set emergency flag for crisis situations"
        ],
        "authentication": [
            "Storing tokens insecurely", 
            "Not refreshing expired tokens"
        ]
    }
    
    return general_pitfalls + category_pitfalls.get(category.lower(), [])


def _get_adhd_coding_tips(category: str) -> List[str]:
    """Get ADHD-specific coding tips."""
    return [
        "Break large requests into smaller chunks",
        "Use clear, descriptive variable names",
        "Add comments explaining business logic",
        "Implement proper error handling for user feedback",
        "Keep response processing simple and fast",
        "Use timeouts to prevent hanging requests"
    ]


def _get_quick_start_endpoints(categorized_endpoints: Dict) -> List[Dict]:
    """Get quick start endpoints for new developers."""
    quick_start = []
    
    # Prioritize beginner-friendly, high-frequency endpoints
    for category, data in categorized_endpoints.items():
        for endpoint in data["endpoints"]:
            if (endpoint["difficulty"] == "beginner" and 
                endpoint["frequency"] in ["high", "medium"]):
                quick_start.append({
                    "category": category,
                    "path": endpoint["path"],
                    "method": endpoint["method"],
                    "summary": endpoint["summary"]
                })
    
    return sorted(quick_start[:6], key=lambda x: x["category"])