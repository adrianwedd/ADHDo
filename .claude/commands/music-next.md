---
description: Skip to the next track in the music queue
allowed-tools: Bash(curl:*)
---

Skip to the next track in the current music queue.

Use curl to POST to the next track endpoint:
`curl -s -X POST "http://192.168.1.100:23443/music/next"`

Show a confirmation message that we've skipped to the next track.