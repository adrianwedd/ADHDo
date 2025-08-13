---
description: Stop music playback on Shack Speakers
allowed-tools: Bash(curl:*)
---

Stop the current music playback.

Use curl to POST to the stop endpoint:
`curl -s -X POST "http://192.168.1.100:23443/music/stop"`

After stopping, show a confirmation message that music has been stopped.