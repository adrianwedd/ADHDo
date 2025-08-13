---
description: Check current music status and what's playing
allowed-tools: Bash(curl:*)
---

Check the current music playback status.

Use curl to GET the status endpoint:
`curl -s "http://192.168.1.100:23443/music/status"`

Parse the JSON response and show:
- Current track name and artist
- Music mood (focus, energy, etc.)
- Volume level
- Queue position (current/total tracks)
- Device name (should be Shack Speakers)
- Whether music is currently playing

Format the output in a user-friendly way with emojis (🎵 for playing, 🔇 for stopped, etc.).