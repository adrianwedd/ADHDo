---
description: Set music volume (0.0 to 1.0)
argument-hint: [volume]
allowed-tools: Bash(curl:*)
---

Set the music volume level.

The volume level is: $ARGUMENTS (use 0.7 if no arguments provided)

Validate that the volume is between 0.0 and 1.0, then use curl to POST:
`curl -s -X POST "http://192.168.1.100:23443/music/volume/{volume}"`

Replace {volume} with the specified volume level.

Show a confirmation message with the volume percentage (multiply by 100 for display).