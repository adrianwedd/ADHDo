#!/bin/bash
# Simple startup script for ADHDo with minimal configuration

echo "🚀 Starting ADHDo ADHD Assistant..."

# Check if .env exists, if not copy from minimal template
if [ ! -f .env ]; then
    echo "📝 Creating .env from minimal template..."
    cp .env.minimal .env
    echo "⚠️  Please edit .env with your Claude session keys!"
    echo "   Get them from browser DevTools after logging into claude.ai"
    exit 1
fi

# Source environment variables
source .env

# Check for required Claude session key
if [ -z "$CLAUDE_SESSION_KEY" ] || [ "$CLAUDE_SESSION_KEY" = "your_session_key_here" ]; then
    echo "❌ Error: CLAUDE_SESSION_KEY not configured in .env"
    echo "   Please add your Claude session key from browser DevTools"
    exit 1
fi

# Check if Redis is running (optional but recommended)
if command -v redis-cli &> /dev/null; then
    redis-cli ping > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ Redis is running"
    else
        echo "⚠️  Redis not running - using in-memory storage (data won't persist)"
        echo "   Start Redis with: sudo systemctl start redis-server"
    fi
else
    echo "⚠️  Redis not installed - using in-memory storage"
fi

# Check if Jellyfin is running (optional for music)
if curl -s http://192.168.1.100:8096/System/Info > /dev/null 2>&1; then
    echo "✅ Jellyfin is running - music features available"
else
    echo "⚠️  Jellyfin not accessible - music features disabled"
    echo "   Start Jellyfin with: sudo systemctl start jellyfin"
fi

# Set Python path
export PYTHONPATH=/home/pi/repos/ADHDo/src

# Start the server
echo ""
echo "🧠 Starting MCP ADHD Server on port ${PORT:-23444}..."
echo "📱 Open http://localhost:${PORT:-23444} in your browser"
echo ""

# Use the virtual environment if it exists
if [ -d "venv_beta" ]; then
    PYTHON_CMD="/home/pi/repos/ADHDo/venv_beta/bin/python"
elif [ -d "venv" ]; then
    PYTHON_CMD="/home/pi/repos/ADHDo/venv/bin/python"
else
    PYTHON_CMD="python3"
fi

# Start the server
$PYTHON_CMD -m mcp_server.minimal_main