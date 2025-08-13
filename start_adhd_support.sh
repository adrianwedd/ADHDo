#!/bin/bash
# Start all ADHD support services

echo "=========================================="
echo "🧠 STARTING ADHD SUPPORT SYSTEM"
echo "=========================================="

# Check if server is already running
if pgrep -f "minimal_main" > /dev/null; then
    echo "✅ Server already running on port 23444"
else
    echo "Starting MCP server..."
    cd /home/pi/repos/ADHDo
    PYTHONPATH=/home/pi/repos/ADHDo/src PORT=23444 /home/pi/repos/ADHDo/venv_beta/bin/python -m mcp_server.minimal_main &
    sleep 5
    echo "✅ Server started"
fi

# Start music auto-play loop
if pgrep -f "music_autoplay_loop" > /dev/null; then
    echo "✅ Music auto-play already running"
else
    echo "Starting music auto-play (8am-10pm)..."
    /home/pi/repos/ADHDo/venv_beta/bin/python /home/pi/repos/ADHDo/music_autoplay_loop.py &
    echo "✅ Music scheduler started"
fi

# Start calendar nudge scheduler
if pgrep -f "calendar_nudge_scheduler" > /dev/null; then
    echo "✅ Calendar nudge scheduler already running"
else
    echo "Starting calendar nudge scheduler..."
    /home/pi/repos/ADHDo/venv_beta/bin/python /home/pi/repos/ADHDo/calendar_nudge_scheduler.py &
    echo "✅ Nudge scheduler started"
fi

echo ""
echo "=========================================="
echo "✅ ALL SERVICES RUNNING"
echo "=========================================="
echo ""
echo "📍 Dashboard: http://localhost:23444"
echo "📍 Health: http://localhost:23444/health"
echo ""
echo "🎵 Music: Auto-plays 8am-10pm"
echo "📅 Nudges: Context-aware reminders"
echo "🛏️ Bedtime: Set for 10pm with escalation"
echo ""
echo "To stop all services: pkill -f 'minimal_main|music_autoplay|calendar_nudge'"
echo ""