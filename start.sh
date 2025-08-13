#!/bin/bash
# ADHD Server - Smart Starter
# Always uses port 23443, checks if running

PORT=23443
echo "🧠 ADHD Server (Port $PORT)"

# Check if already running
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    if curl -s http://localhost:$PORT/health > /dev/null 2>&1; then
        echo "✅ Already running!"
        echo "📍 http://localhost:$PORT"
        [ "$1" = "-r" ] && { echo "Reloading..."; lsof -ti:$PORT | xargs kill -9; sleep 1; } || exit 0
    else
        echo "Restarting broken server..."
        lsof -ti:$PORT | xargs kill -9 2>/dev/null
        sleep 1
    fi
fi

# Start server
echo "Starting..."
cd /home/pi/repos/ADHDo
PYTHONPATH=. ./venv_beta/bin/python simple_working_server.py
