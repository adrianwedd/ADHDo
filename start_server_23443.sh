#!/bin/bash
# Start script for ADHDo server

# Load environment variables
source /home/pi/repos/ADHDo/.env 2>/dev/null || true

# Set Jellyfin and Chromecast configuration
export JELLYFIN_URL="${JELLYFIN_URL:-http://localhost:8096}"
export JELLYFIN_TOKEN="${JELLYFIN_TOKEN:-abf44b9de48c46dab56d4ace26b24f9a}"
export CHROMECAST_NAME="${CHROMECAST_NAME:-Shack Speakers}"

# Start the server
exec /home/pi/repos/ADHDo/venv_beta/bin/python -m mcp_server.minimal_main