---
description: Play music with specified mood for ADHD focus support
argument-hint: [mood]
allowed-tools: Bash(curl:*)
---

Play music with the specified mood (or "focus" by default). 

Available moods: focus, energy, calm, ambient, nature, study

Use curl to POST to the music API:
- focus: `curl -s -X POST "http://192.168.1.100:23443/music/focus"`  
- energy: `curl -s -X POST "http://192.168.1.100:23443/music/energy"`
- calm: `curl -s -X POST "http://192.168.1.100:23443/music/calm"`
- ambient: `curl -s -X POST "http://192.168.1.100:23443/music/ambient"`
- nature: `curl -s -X POST "http://192.168.1.100:23443/music/nature"`
- study: `curl -s -X POST "http://192.168.1.100:23443/music/study"`

The mood is: $ARGUMENTS (use "focus" if no arguments provided)

After making the API call, show a friendly confirmation message about the music starting.