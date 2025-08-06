"""
MCP Tool Registry

Manages registration, discovery, and lifecycle of MCP tools.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

import structlog
from pydantic import ValidationError

from .models import Tool, ToolConfig, ToolType, ToolStatus

logger = structlog.get_logger()


class ToolRegistry:
    """Registry for managing MCP tools and their configurations."""
    
    def __init__(self, registry_path: Optional[Path] = None):
        """Initialize the tool registry."""
        self.registry_path = registry_path or Path("data/mcp_tools.json")
        self.tools: Dict[str, Tool] = {}
        self.tool_types: Set[str] = set()
        self.tags: Set[str] = set()
        
        # Ensure registry directory exists
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing tools
        asyncio.create_task(self._load_from_disk())
    
    async def register_tool(self, tool: Tool) -> bool:
        """Register a tool in the registry."""
        try:
            tool_id = tool.config.tool_id
            
            # Validate tool configuration
            self._validate_tool_config(tool.config)
            
            # Store in memory
            self.tools[tool_id] = tool
            
            # Update indexes
            self.tool_types.add(tool.config.tool_type.value)
            self.tags.update(tool.config.tags)
            
            # Persist to disk
            await self._save_to_disk()
            
            logger.info("Tool registered in registry", 
                       tool_id=tool_id, 
                       name=tool.config.name,
                       tool_type=tool.config.tool_type)
            
            return True
            
        except ValidationError as e:
            logger.error("Tool validation failed", tool_id=tool.config.tool_id, errors=e.errors())
            return False
        except Exception as e:
            logger.error("Tool registration failed", tool_id=tool.config.tool_id, error=str(e))
            return False
    
    async def unregister_tool(self, tool_id: str) -> bool:
        """Unregister a tool from the registry."""
        try:
            if tool_id in self.tools:
                tool = self.tools[tool_id]
                
                # Remove from memory
                del self.tools[tool_id]
                
                # Rebuild indexes
                self._rebuild_indexes()
                
                # Persist to disk
                await self._save_to_disk()
                
                logger.info("Tool unregistered", tool_id=tool_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Tool unregistration failed", tool_id=tool_id, error=str(e))
            return False
    
    async def update_tool(self, tool: Tool) -> bool:
        """Update an existing tool in the registry."""
        try:
            tool_id = tool.config.tool_id
            
            if tool_id not in self.tools:
                logger.warning("Attempted to update non-existent tool", tool_id=tool_id)
                return False
            
            # Update in memory
            self.tools[tool_id] = tool
            
            # Update indexes
            self._rebuild_indexes()
            
            # Persist to disk
            await self._save_to_disk()
            
            logger.debug("Tool updated in registry", tool_id=tool_id)
            return True
            
        except Exception as e:
            logger.error("Tool update failed", tool_id=tool.config.tool_id, error=str(e))
            return False
    
    async def get_tool(self, tool_id: str) -> Optional[Tool]:
        """Get a tool by ID."""
        return self.tools.get(tool_id)
    
    async def list_tools(self, status: Optional[ToolStatus] = None) -> List[Tool]:
        """List all tools, optionally filtered by status."""
        tools = list(self.tools.values())
        
        if status:
            tools = [tool for tool in tools if tool.status == status]
        
        # Sort by priority and name
        tools.sort(key=lambda t: (-t.config.priority, t.config.name))
        
        return tools
    
    async def discover_tools(
        self, 
        tool_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        adhd_friendly_only: bool = True
    ) -> List[Tool]:
        """Discover tools by type, tags, and ADHD-friendliness."""
        tools = list(self.tools.values())
        
        # Filter by type
        if tool_type:
            tools = [tool for tool in tools if tool.config.tool_type.value == tool_type]
        
        # Filter by tags
        if tags:
            tools = [
                tool for tool in tools 
                if any(tag in tool.config.tags for tag in tags)
            ]
        
        # Filter by ADHD-friendliness
        if adhd_friendly_only:
            tools = [tool for tool in tools if tool.config.adhd_friendly]
        
        # Filter enabled only
        tools = [tool for tool in tools if tool.config.enabled]
        
        # Sort by priority and ADHD-specific scores
        tools.sort(key=lambda t: (
            -t.config.priority,
            -t.focus_friendly_score if t.focus_friendly_score else 0,
            t.config.cognitive_load,  # Lower cognitive load is better
            t.config.name
        ))
        
        return tools
    
    async def search_tools(self, query: str) -> List[Tool]:
        """Search tools by name, description, or tags."""
        query = query.lower()
        matching_tools = []
        
        for tool in self.tools.values():
            # Check name
            if query in tool.config.name.lower():
                matching_tools.append((tool, 3))  # High relevance
                continue
            
            # Check description
            if query in tool.config.description.lower():
                matching_tools.append((tool, 2))  # Medium relevance
                continue
            
            # Check tags
            if any(query in tag.lower() for tag in tool.config.tags):
                matching_tools.append((tool, 1))  # Low relevance
        
        # Sort by relevance then priority
        matching_tools.sort(key=lambda x: (-x[1], -x[0].config.priority))
        
        return [tool for tool, _ in matching_tools]
    
    async def get_tools_by_type(self, tool_type: ToolType) -> List[Tool]:
        """Get all tools of a specific type."""
        return [
            tool for tool in self.tools.values() 
            if tool.config.tool_type == tool_type and tool.config.enabled
        ]
    
    async def get_focus_safe_tools(self) -> List[Tool]:
        """Get tools that are safe to use during focus time."""
        return [
            tool for tool in self.tools.values()
            if tool.config.focus_safe and tool.config.enabled
        ]
    
    async def get_low_cognitive_load_tools(self, max_load: float = 0.3) -> List[Tool]:
        """Get tools with low cognitive load."""
        return [
            tool for tool in self.tools.values()
            if tool.config.cognitive_load <= max_load and tool.config.enabled
        ]
    
    def get_registry_stats(self) -> Dict[str, any]:
        """Get statistics about the tool registry."""
        total_tools = len(self.tools)
        enabled_tools = len([t for t in self.tools.values() if t.config.enabled])
        connected_tools = len([t for t in self.tools.values() if t.status == ToolStatus.CONNECTED])
        
        type_counts = {}
        for tool_type in self.tool_types:
            type_counts[tool_type] = len([
                t for t in self.tools.values() 
                if t.config.tool_type.value == tool_type
            ])
        
        return {
            'total_tools': total_tools,
            'enabled_tools': enabled_tools,
            'connected_tools': connected_tools,
            'tool_types': list(self.tool_types),
            'type_counts': type_counts,
            'total_tags': len(self.tags),
            'registry_path': str(self.registry_path)
        }
    
    # Private Methods
    
    def _validate_tool_config(self, config: ToolConfig):
        """Validate tool configuration."""
        # Check required fields
        if not config.tool_id or not config.name:
            raise ValidationError("Tool ID and name are required")
        
        # Check tool ID format
        if not config.tool_id.replace('_', '').replace('-', '').isalnum():
            raise ValidationError("Tool ID must be alphanumeric with underscores/hyphens")
        
        # Check cognitive load range
        if not 0 <= config.cognitive_load <= 1:
            raise ValidationError("Cognitive load must be between 0 and 1")
        
        # Check priority range
        if not 1 <= config.priority <= 10:
            raise ValidationError("Priority must be between 1 and 10")
    
    def _rebuild_indexes(self):
        """Rebuild tool type and tag indexes."""
        self.tool_types.clear()
        self.tags.clear()
        
        for tool in self.tools.values():
            self.tool_types.add(tool.config.tool_type.value)
            self.tags.update(tool.config.tags)
    
    async def _load_from_disk(self):
        """Load tools from disk storage."""
        try:
            if not self.registry_path.exists():
                logger.info("No existing tool registry found, starting fresh")
                return
            
            with open(self.registry_path, 'r') as f:
                data = json.load(f)
            
            # Load tools
            for tool_data in data.get('tools', []):
                try:
                    tool = Tool.parse_obj(tool_data)
                    self.tools[tool.config.tool_id] = tool
                except ValidationError as e:
                    logger.warning("Invalid tool data in registry", 
                                  tool_id=tool_data.get('config', {}).get('tool_id'),
                                  errors=e.errors())
            
            # Rebuild indexes
            self._rebuild_indexes()
            
            logger.info("Tool registry loaded from disk", 
                       tool_count=len(self.tools),
                       path=str(self.registry_path))
            
        except Exception as e:
            logger.error("Failed to load tool registry from disk", 
                        path=str(self.registry_path), 
                        error=str(e))
    
    async def _save_to_disk(self):
        """Save tools to disk storage."""
        try:
            # Prepare data
            data = {
                'version': '1.0',
                'last_updated': datetime.utcnow().isoformat(),
                'tools': [tool.dict() for tool in self.tools.values()]
            }
            
            # Write to temporary file first
            temp_path = self.registry_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Atomic move
            temp_path.replace(self.registry_path)
            
            logger.debug("Tool registry saved to disk", 
                        tool_count=len(self.tools),
                        path=str(self.registry_path))
            
        except Exception as e:
            logger.error("Failed to save tool registry to disk", 
                        path=str(self.registry_path), 
                        error=str(e))


# Import asyncio at module level to avoid issues
import asyncio