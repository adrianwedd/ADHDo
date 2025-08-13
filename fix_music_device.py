#!/usr/bin/env python3
"""
Fix music playback device - play on a Nest device you can actually hear
"""

import os

# Update the environment to use a different Chromecast device
print("Fixing music playback device...")
print("\nAvailable devices:")
print("1. Nest Mini")
print("2. Nest Hub Max")
print("3. Living Room speaker")
print("\nThe system is currently trying to play on 'Shack Speakers' which you can't hear.")
print("\nTo fix this, restart the server with a different device:")
print("\n# For Nest Mini:")
print("CHROMECAST_NAME='Nest Mini' PYTHONPATH=/home/pi/repos/ADHDo/src PORT=23443 python -m mcp_server.minimal_main")
print("\n# For Living Room speaker:")
print("CHROMECAST_NAME='Living Room speaker' PYTHONPATH=/home/pi/repos/ADHDo/src PORT=23443 python -m mcp_server.minimal_main")
print("\n# For Nest Hub Max (might conflict with nudges):")
print("CHROMECAST_NAME='Nest Hub Max' PYTHONPATH=/home/pi/repos/ADHDo/src PORT=23443 python -m mcp_server.minimal_main")
print("\nRecommendation: Use 'Nest Mini' or 'Living Room speaker' for music to avoid nudge conflicts.")