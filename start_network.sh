#!/bin/bash
# Start MCP ADHD Server for local network access

# Get the Pi's local IP address
LOCAL_IP=$(hostname -I | cut -d' ' -f1)

echo "🧠 Starting MCP ADHD Server for Local Network Access"
echo "=================================="
echo "📡 Network URL: http://$LOCAL_IP:23443"
echo "📍 Localhost:  http://localhost:23443"
echo "📖 Docs:       http://$LOCAL_IP:23443/docs"
echo "🛑 Press Ctrl+C to stop"
echo ""

# Set environment and start server
export PYTHONPATH=src
export PORT=23443

# Start the server
/home/pi/repos/ADHDo/venv_beta/bin/python src/mcp_server/minimal_main.py