#!/usr/bin/env python3
"""
Add MCP integration endpoints to main.py
"""

import sys
from pathlib import Path

def add_mcp_endpoints():
    """Add MCP endpoints to main.py"""
    
    main_py = Path(__file__).parent.parent / "src" / "mcp_server" / "main.py"
    
    # Read current content
    with open(main_py, 'r') as f:
        content = f.read()
    
    # Check if MCP endpoints already exist
    if "mcp_integration" in content:
        print("✅ MCP endpoints already exist in main.py")
        return
    
    # Add import
    import_line = "from mcp_server.mcp_integration import mcp_router, initialize_mcp_system, shutdown_mcp_system"
    
    # Find the imports section
    lines = content.split('\n')
    
    # Find where to add the import (after other mcp_server imports)
    import_index = -1
    for i, line in enumerate(lines):
        if line.startswith("from mcp_server.onboarding"):
            import_index = i + 1
            break
    
    if import_index != -1:
        lines.insert(import_index, import_line)
    
    # Add MCP initialization to lifespan function
    lifespan_start = None
    lifespan_end = None
    
    for i, line in enumerate(lines):
        if "# Initialize database connection" in line:
            lifespan_start = i
        elif "# TODO: Initialize Telegram bot" in line:
            lifespan_end = i
            break
    
    if lifespan_start and lifespan_end:
        mcp_init = """
    # Initialize MCP system
    try:
        await initialize_mcp_system()
        logger.info("✅ MCP system initialized successfully")
    except Exception as e:
        logger.warning("⚠️ MCP system initialization failed", error=str(e))"""
        
        lines.insert(lifespan_end, mcp_init)
    
    # Add MCP cleanup to shutdown
    shutdown_index = None
    for i, line in enumerate(lines):
        if "await close_database()" in line:
            shutdown_index = i + 1
            break
    
    if shutdown_index:
        mcp_cleanup = """        await shutdown_mcp_system()"""
        lines.insert(shutdown_index, mcp_cleanup)
    
    # Add router
    router_add = """
# Include MCP integration router
app.include_router(mcp_router)
"""
    
    # Find where to add router (after other routers)
    router_index = None
    for i, line in enumerate(lines):
        if "# Mount static files" in line:
            router_index = i
            break
    
    if router_index:
        lines.insert(router_index, router_add)
    
    # Write back to file
    content = '\n'.join(lines)
    with open(main_py, 'w') as f:
        f.write(content)
    
    print("✅ Added MCP endpoints to main.py")

if __name__ == "__main__":
    add_mcp_endpoints()